import React, { useState, useRef, useEffect } from 'react';
import { Send, Mic, Sparkles, Brain, Paperclip, Image as ImageIcon, Radio, X, Terminal, ChevronRight, Power } from 'lucide-react';
import { Message } from '../../types';
import { sendMessageToGemini, getGeminiClient } from '../../services/geminiService';
import { Modality, LiveServerMessage } from '@google/genai';
import { useAgentWatch } from '../../context/AgentWatchContext';
import { useAgents } from '../../context/AgentContext';
import { Button } from '../../components/UIComponents';

export const ConversationBridge: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: 'Hydra systems online. Command bridge active. Awaiting instructions.',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [overrideCmd, setOverrideCmd] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [attachedImage, setAttachedImage] = useState<{data: string, mimeType: string} | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  const { watchedAgentId, streamLogs, stopWatching, injectCommand } = useAgentWatch();
  const { getAgent } = useAgents();
  const watchedAgent = watchedAgentId ? getAgent(watchedAgentId) : null;
  
  // Live API Refs
  const audioContextRef = useRef<AudioContext | null>(null);
  const inputAudioContextRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sessionPromiseRef = useRef<Promise<any> | null>(null);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, attachedImage, isLive]);

  // Auto-scroll logs
  useEffect(() => {
    if (watchedAgentId) {
       logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [streamLogs, watchedAgentId]);

  // --- Image Handling ---

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = (reader.result as string).split(',')[1];
        setAttachedImage({
          data: base64String,
          mimeType: file.type
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const removeImage = () => setAttachedImage(null);

  // --- Text/Image Generation ---

  const handleSend = async () => {
    if ((!inputValue.trim() && !attachedImage) || isProcessing) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date(),
      attachment: attachedImage ? { type: 'image', ...attachedImage } : undefined
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    const currentImage = attachedImage;
    setAttachedImage(null); // Clear immediately
    setIsProcessing(true);

    try {
      const response = await sendMessageToGemini(userMsg.content, undefined, currentImage || undefined);

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.text,
        timestamp: new Date()
      };
      
      // Handle response image attachment if exists
      if (response.images && response.images.length > 0) {
        aiMsg.attachment = {
           type: 'image',
           data: response.images[0].data,
           mimeType: response.images[0].mimeType
        };
      }

      setMessages(prev => [...prev, aiMsg]);
    } catch (e) {
      // Error handling
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOverride = (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideCmd.trim()) return;
    injectCommand(overrideCmd);
    setOverrideCmd('');
  };

  // --- Live API Handling ---

  const stopLiveSession = () => {
    setIsLive(false);
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (inputAudioContextRef.current) {
      inputAudioContextRef.current.close();
      inputAudioContextRef.current = null;
    }
    sourcesRef.current.forEach(source => source.stop());
    sourcesRef.current.clear();
    sessionPromiseRef.current = null;
  };

  const startLiveSession = async () => {
    const ai = getGeminiClient();
    if (!ai || !process.env.API_KEY) {
      alert("API Key required for Live Mode");
      return;
    }

    setIsLive(true);
    nextStartTimeRef.current = 0;

    inputAudioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-09-2025',
        callbacks: {
          onopen: () => {
            if (!inputAudioContextRef.current) return;
            const source = inputAudioContextRef.current.createMediaStreamSource(stream);
            const scriptProcessor = inputAudioContextRef.current.createScriptProcessor(4096, 1, 1);
            scriptProcessor.onaudioprocess = (audioProcessingEvent) => {
              const inputData = audioProcessingEvent.inputBuffer.getChannelData(0);
              const pcmBlob = createBlob(inputData);
              sessionPromise.then(session => {
                session.sendRealtimeInput({ media: pcmBlob });
              });
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputAudioContextRef.current.destination);
          },
          onmessage: async (message: LiveServerMessage) => {
            const base64Audio = message.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64Audio && audioContextRef.current) {
              const audioCtx = audioContextRef.current;
              nextStartTimeRef.current = Math.max(nextStartTimeRef.current, audioCtx.currentTime);
              const audioBuffer = await decodeAudioData(decode(base64Audio), audioCtx, 24000, 1);
              const source = audioCtx.createBufferSource();
              source.buffer = audioBuffer;
              const gainNode = audioCtx.createGain();
              source.connect(gainNode);
              gainNode.connect(audioCtx.destination); 
              if (canvasRef.current) animateVisualizer();
              source.start(nextStartTimeRef.current);
              nextStartTimeRef.current += audioBuffer.duration;
              sourcesRef.current.add(source);
              source.onended = () => sourcesRef.current.delete(source);
            }
          },
          onclose: () => setIsLive(false),
          onerror: (err) => setIsLive(false)
        },
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: "You are HYDRA, a high-tech command center AI. Be concise, efficient, and speak with a slight sci-fi edge.",
        }
      });
      sessionPromiseRef.current = sessionPromise;
    } catch (err) {
      console.error("Failed to start live session", err);
      setIsLive(false);
    }
  };

  function createBlob(data: Float32Array) {
    const l = data.length;
    const int16 = new Int16Array(l);
    for (let i = 0; i < l; i++) {
      int16[i] = data[i] * 32768;
    }
    const bytes = new Uint8Array(int16.buffer);
    let binary = '';
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const b64 = btoa(binary);
    return { data: b64, mimeType: 'audio/pcm;rate=16000' };
  }

  function decode(base64: string) {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
  }

  async function decodeAudioData(data: Uint8Array, ctx: AudioContext, sampleRate: number, numChannels: number) {
    const dataInt16 = new Int16Array(data.buffer);
    const frameCount = dataInt16.length / numChannels;
    const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);
    for (let channel = 0; channel < numChannels; channel++) {
      const channelData = buffer.getChannelData(channel);
      for (let i = 0; i < frameCount; i++) {
        channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
      }
    }
    return buffer;
  }
  
  const animateVisualizer = () => {
     const canvas = canvasRef.current;
     if (!canvas) return;
     const ctx = canvas.getContext('2d');
     if (!ctx) return;
     ctx.clearRect(0, 0, canvas.width, canvas.height);
     ctx.fillStyle = '#10b981'; 
     const bars = 20;
     const width = canvas.width / bars;
     for (let i = 0; i < bars; i++) {
        const height = Math.random() * canvas.height;
        ctx.fillRect(i * width, (canvas.height - height) / 2, width - 2, height);
     }
  };
  
  useEffect(() => {
    if (!isLive && canvasRef.current) {
       const ctx = canvasRef.current.getContext('2d');
       ctx?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
  }, [isLive]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-dim border-l border-neutral-800 w-[400px]">
      <input type="file" ref={fileInputRef} onChange={handleImageSelect} accept="image/*" className="hidden" />

      {/* Header */}
      <div className="h-16 border-b border-neutral-800 flex items-center px-4 justify-between bg-surface-default shrink-0">
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${
            watchedAgentId ? 'bg-cyan-500 animate-pulse shadow-glow-cyan' :
            isLive ? 'bg-red-500 animate-pulse shadow-glow-red' : 
            'bg-emerald-500 shadow-glow-emerald'
          }`} />
          <span className={`font-mono text-sm font-semibold tracking-wide ${
             watchedAgentId ? 'text-cyan-400' :
             isLive ? 'text-red-400' : 
             'text-emerald-400'
          }`}>
            {watchedAgentId ? `MONITOR_${watchedAgent?.name.toUpperCase()}` : isLive ? 'LIVE_UPLINK' : 'BRIDGE_UPLINK'}
          </span>
        </div>
        <div className="flex items-center gap-2">
           {!watchedAgentId && (
             <button 
               onClick={isLive ? stopLiveSession : startLiveSession}
               className={`p-2 rounded-full transition-all border ${
                 isLive 
                   ? 'bg-red-500/20 border-red-500 text-red-400 hover:bg-red-500/30' 
                   : 'bg-neutral-800 border-neutral-700 text-neutral-400 hover:text-white'
               }`}
               title="Toggle Voice Uplink"
             >
               {isLive ? <Radio size={16} className="animate-pulse" /> : <Mic size={16} />}
             </button>
           )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden relative flex flex-col">
        {/* Live Audio Overlay */}
        {isLive && !watchedAgentId && (
          <div className="absolute inset-0 bg-surface-base/90 z-20 flex flex-col items-center justify-center backdrop-blur-sm">
             <div className="text-red-500 font-mono text-xs mb-4 animate-pulse">AUDIO STREAM ACTIVE</div>
             <canvas ref={canvasRef} width={300} height={100} className="mb-8" />
             <div className="text-neutral-500 text-sm font-mono max-w-[200px] text-center">
               Hydra is listening... Speak your command.
             </div>
             <button onClick={stopLiveSession} className="mt-8 px-6 py-2 bg-red-900/20 border border-red-500 text-red-400 rounded hover:bg-red-900/40 font-mono text-xs">
               TERMINATE UPLINK
             </button>
          </div>
        )}

        {/* Watch Mode Overlay */}
        {watchedAgentId && (
           <div className="absolute inset-0 bg-neutral-900/95 backdrop-blur-sm z-30 flex flex-col font-mono font-mono">
              <div className="px-4 py-2 bg-surface-raised border-b border-neutral-800 flex justify-between items-center text-xs text-neutral-400">
                 <div className="flex items-center gap-2">
                    <Terminal size={12} />
                    <span>SECURE_SHELL // {watchedAgentId}</span>
                 </div>
                 <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                    <span className="text-cyan-500">RECEIVING TELEMETRY</span>
                 </div>
              </div>
              
              {/* Terminal Output */}
              <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-xs bg-black/50">
                 {streamLogs.map((log) => (
                    <div key={log.id} className="flex gap-2 text-neutral-300 border-l-2 border-transparent hover:border-neutral-700 pl-2">
                       <span className="text-neutral-600 opacity-50 shrink-0">[{log.timestamp}]</span>
                       <span className={`shrink-0 w-16 font-bold ${
                          log.level === 'DEBUG' ? 'text-purple-400' : 
                          log.level === 'WARN' ? 'text-amber-400' :
                          'text-emerald-400'
                       }`}>{log.level}</span>
                       <span className={log.message.includes('[TOOL_CALL]') ? 'text-amber-300' : 'text-neutral-300'}>
                         {log.message}
                       </span>
                    </div>
                 ))}
                 <div ref={logsEndRef} />
              </div>

              {/* System Override Input */}
              <div className="p-4 bg-surface-dim border-t border-neutral-800">
                 <form onSubmit={handleOverride} className="mb-2">
                    <div className="flex items-center bg-black/40 border border-neutral-700 rounded px-3 py-2 focus-within:border-cyan-500 transition-colors">
                       <span className="text-cyan-500 mr-2 blink">_</span>
                       <input 
                          type="text" 
                          value={overrideCmd}
                          onChange={(e) => setOverrideCmd(e.target.value)}
                          className="bg-transparent border-none outline-none text-cyan-400 w-full font-mono text-sm placeholder-cyan-900"
                          placeholder="Inject System Command..."
                          autoFocus
                       />
                       <button type="submit" disabled={!overrideCmd} className="text-cyan-600 hover:text-cyan-400 disabled:opacity-50">
                          <ChevronRight size={16} />
                       </button>
                    </div>
                 </form>
                 <Button variant="danger" className="w-full justify-center text-xs py-2 bg-red-900/10 border-red-900/30 hover:bg-red-900/20" onClick={stopWatching}>
                    <Power size={12} className="mr-2" /> TERMINATE MONITORING
                 </Button>
              </div>
           </div>
        )}

        {/* Normal Chat */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-sm">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[85%] rounded-lg p-3 ${msg.role === 'user' ? 'bg-emerald-900/20 text-emerald-100 border border-emerald-500/20' : 'bg-neutral-800/50 text-neutral-300 border border-neutral-700'}`}>
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-1.5 mb-2 text-xs text-cyan-500 font-bold uppercase tracking-wider">
                    <Brain size={12} /><span>HYDRA</span>
                  </div>
                )}
                
                {msg.attachment && (
                  <div className="mb-2 rounded overflow-hidden border border-neutral-700/50">
                     <img src={`data:${msg.attachment.mimeType};base64,${msg.attachment.data}`} alt="attachment" className="max-w-full h-auto max-h-[200px] object-cover" />
                  </div>
                )}

                <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
              </div>
              <span className="text-[10px] text-neutral-600 mt-1 px-1">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          ))}
          {isProcessing && (
             <div className="flex flex-col items-start">
               <div className="bg-neutral-800/50 text-cyan-400 border border-cyan-500/20 max-w-[85%] rounded-lg p-3 flex items-center gap-2">
                 <Sparkles size={14} className="animate-spin" />
                 <span className="animate-pulse">Processing intent...</span>
               </div>
             </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="p-4 bg-surface-default border-t border-neutral-800 shrink-0">
        {attachedImage && (
           <div className="mb-3 flex items-center gap-3 bg-surface-dim p-2 rounded border border-neutral-700">
              <div className="h-10 w-10 rounded overflow-hidden relative">
                 <img src={`data:${attachedImage.mimeType};base64,${attachedImage.data}`} className="w-full h-full object-cover" />
              </div>
              <span className="text-xs text-neutral-400 flex-1 truncate">Image Attached</span>
              <button onClick={removeImage} className="text-neutral-500 hover:text-red-400"><X size={14} /></button>
           </div>
        )}

        <div className="relative">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!!watchedAgentId}
            placeholder={watchedAgentId ? "Monitoring Active - Input Disabled" : "Enter command or query..."}
            className="w-full bg-surface-dim text-neutral-200 text-sm rounded-lg pl-3 pr-20 py-3 border border-neutral-700 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none resize-none h-12 min-h-[48px] overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <div className="absolute right-2 top-1.5 flex gap-1">
             <button onClick={() => fileInputRef.current?.click()} disabled={!!watchedAgentId} className="p-1.5 text-neutral-400 hover:text-cyan-400 transition-colors disabled:opacity-30" title="Attach Image"><ImageIcon size={16} /></button>
             <button onClick={handleSend} disabled={(!inputValue.trim() && !attachedImage) || isProcessing || !!watchedAgentId} className="p-1.5 text-neutral-400 hover:text-emerald-400 disabled:opacity-30 disabled:hover:text-neutral-400 transition-colors"><Send size={16} /></button>
          </div>
        </div>
        <div className="flex justify-between mt-2 text-[10px] text-neutral-600 font-mono uppercase">
          <span>SECURE_CONN_ESTABLISHED</span>
          <div className="flex items-center gap-1"><div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />ONLINE</div>
        </div>
      </div>
    </div>
  );
};
