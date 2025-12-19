import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, Button, Badge } from '../components/UIComponents';
import { useNotifications } from '../context/NotificationContext';
import {
  MessageSquare, Send, Loader2, RefreshCw, Cpu, Zap, Sparkles,
  Code, Brain, Heart, ChevronDown, Settings, Trash2, Copy, Check,
  RotateCcw, Square, Sliders, FileText
} from 'lucide-react';

// API base URL
const API_BASE = 'http://192.168.1.244:8700';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  model?: string;
  tokens?: number;
}

interface ModelInfo {
  name: string;
  type: string;
  size_gb?: number;
  quantization?: string;
  vram_gb?: number;
  backend: string;
  categories: string[];
  is_nsfw?: boolean;
}

interface ModelRegistry {
  by_category: {
    creative_nsfw: ModelInfo[];
    coding: ModelInfo[];
    reasoning: ModelInfo[];
    general: ModelInfo[];
  };
  loaded: {
    tabbyapi?: { model_name?: string; status?: string };
  };
  quick_picks: {
    nsfw_creative: string;
    coding: string;
    reasoning: string;
    general: string;
    fast: string;
  };
}

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [registry, setRegistry] = useState<ModelRegistry | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('current');
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string>('creative_nsfw');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [systemPrompt, setSystemPrompt] = useState('You are a helpful, creative, and intelligent AI assistant.');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2048);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { addNotification } = useNotifications();

  // Copy message to clipboard
  const copyToClipboard = useCallback(async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      addNotification('error', 'Copy Failed', 'Could not copy to clipboard');
    }
  }, [addNotification]);

  // Regenerate last response
  const regenerateResponse = useCallback(async () => {
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
    if (!lastUserMessage) return;

    // Remove last assistant message
    setMessages(prev => {
      const lastIndex = prev.map(m => m.role).lastIndexOf('assistant');
      if (lastIndex > -1) {
        return prev.slice(0, lastIndex);
      }
      return prev;
    });

    // Trigger new generation with the last user input
    setInput(lastUserMessage.content);
    setTimeout(() => sendMessage(), 100);
  }, [messages]);

  // Stop generation
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
      addNotification('info', 'Stopped', 'Generation stopped');
    }
  }, [addNotification]);

  // Fetch model registry on mount
  useEffect(() => {
    fetchRegistry();
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchRegistry = async () => {
    try {
      const response = await fetch(`${API_BASE}/models/registry`);
      if (response.ok) {
        const data = await response.json();
        setRegistry(data);
        // Set default model based on what's loaded
        if (data.loaded?.tabbyapi?.model_name) {
          setSelectedModel('current');
        }
      }
    } catch (e) {
      console.error('Failed to fetch model registry:', e);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create abort controller for stop functionality
    abortControllerRef.current = new AbortController();

    try {
      // Build messages array with system prompt
      const chatMessages = [
        { role: 'system', content: systemPrompt },
        ...messages.map(m => ({ role: m.role, content: m.content })),
        { role: userMessage.role, content: userMessage.content },
      ];

      const response = await fetch(`${API_BASE}/models/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          messages: chatMessages,
          max_tokens: maxTokens,
          temperature: temperature,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        model: data.model,
        tokens: data.tokens_used,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (e: any) {
      addNotification('error', 'Chat Error', e.message || 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'creative_nsfw': return <Heart size={16} className="text-pink-500" />;
      case 'coding': return <Code size={16} className="text-cyan-500" />;
      case 'reasoning': return <Brain size={16} className="text-purple-500" />;
      default: return <Sparkles size={16} className="text-amber-500" />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'creative_nsfw': return 'Creative / NSFW';
      case 'coding': return 'Coding';
      case 'reasoning': return 'Reasoning';
      default: return 'General';
    }
  };

  const getLoadedModelName = () => {
    if (selectedModel === 'current' && registry?.loaded?.tabbyapi?.model_name) {
      return registry.loaded.tabbyapi.model_name;
    }
    return selectedModel;
  };

  return (
    <div className="flex flex-col h-full bg-surface-base">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-neutral-800 flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-pink-500">CHAT</span> // MODEL PLAYGROUND
          </h2>
          <p className="text-sm text-neutral-500 mt-1">
            Chat with any model - NSFW, coding, reasoning, or general
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
            icon={<Sliders size={14} />}
          >
            Settings
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchRegistry}
            icon={<RefreshCw size={14} />}
          >
            Refresh
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={clearChat}
            icon={<Trash2 size={14} />}
          >
            Clear
          </Button>
        </div>
      </div>

      {/* Model Selector Bar */}
      <div className="px-6 py-3 border-b border-neutral-800 bg-surface-dim">
        <div className="flex items-center gap-4">
          <span className="text-xs text-neutral-500 font-mono">MODEL:</span>
          <button
            onClick={() => setShowModelPicker(!showModelPicker)}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface-default border border-neutral-700 rounded-lg hover:border-pink-500/50 transition-colors"
          >
            <Cpu size={14} className="text-pink-500" />
            <span className="text-sm text-neutral-200 font-mono truncate max-w-[300px]">
              {getLoadedModelName()}
            </span>
            <ChevronDown size={14} className="text-neutral-500" />
          </button>

          {registry?.loaded?.tabbyapi?.status === 'loaded' && (
            <Badge variant="emerald">
              <Zap size={10} className="mr-1" />
              LOADED
            </Badge>
          )}
        </div>

        {/* Model Picker Dropdown */}
        {showModelPicker && registry && (
          <div className="absolute z-50 mt-2 w-[500px] bg-surface-raised border border-neutral-700 rounded-xl shadow-xl overflow-hidden">
            {/* Category Tabs */}
            <div className="flex border-b border-neutral-700">
              {Object.keys(registry.by_category).map(category => (
                <button
                  key={category}
                  onClick={() => setActiveCategory(category)}
                  className={`flex-1 px-4 py-3 text-xs font-mono flex items-center justify-center gap-2 transition-colors ${
                    activeCategory === category
                      ? 'bg-surface-default text-neutral-200 border-b-2 border-pink-500'
                      : 'text-neutral-500 hover:text-neutral-300'
                  }`}
                >
                  {getCategoryIcon(category)}
                  {getCategoryLabel(category)}
                </button>
              ))}
            </div>

            {/* Model List */}
            <div className="max-h-[300px] overflow-y-auto p-2">
              {/* Current Model Option */}
              <button
                onClick={() => {
                  setSelectedModel('current');
                  setShowModelPicker(false);
                }}
                className={`w-full p-3 rounded-lg text-left transition-colors mb-1 ${
                  selectedModel === 'current'
                    ? 'bg-pink-500/10 border border-pink-500/30'
                    : 'hover:bg-surface-default'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Zap size={14} className="text-emerald-500" />
                  <span className="text-sm font-medium text-neutral-200">Currently Loaded Model</span>
                </div>
                <p className="text-xs text-neutral-500 mt-1 ml-5">
                  {registry.loaded?.tabbyapi?.model_name || 'No model loaded'}
                </p>
              </button>

              {/* Category Models */}
              {registry.by_category[activeCategory as keyof typeof registry.by_category]?.map(model => (
                <button
                  key={model.name}
                  onClick={() => {
                    setSelectedModel(model.name);
                    setShowModelPicker(false);
                  }}
                  className={`w-full p-3 rounded-lg text-left transition-colors ${
                    selectedModel === model.name
                      ? 'bg-pink-500/10 border border-pink-500/30'
                      : 'hover:bg-surface-default'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-neutral-200">{model.name}</span>
                    <div className="flex items-center gap-2">
                      {model.quantization && (
                        <Badge variant="neutral">{model.quantization}</Badge>
                      )}
                      {model.vram_gb && (
                        <Badge variant="purple">{model.vram_gb}GB</Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-neutral-500">{model.backend}</span>
                    {model.is_nsfw && (
                      <Badge variant="red">NSFW</Badge>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="px-6 py-4 border-b border-neutral-800 bg-surface-raised">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* System Prompt */}
            <div className="md:col-span-2">
              <label className="block text-xs text-neutral-500 font-mono mb-2">
                <FileText size={12} className="inline mr-1" />
                SYSTEM PROMPT
              </label>
              <textarea
                value={systemPrompt}
                onChange={e => setSystemPrompt(e.target.value)}
                className="w-full bg-surface-default border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-200 placeholder-neutral-500 resize-none focus:outline-none focus:border-pink-500/50"
                rows={3}
                placeholder="Set the AI's behavior and personality..."
              />
            </div>

            {/* Parameters */}
            <div className="space-y-4">
              {/* Temperature */}
              <div>
                <label className="block text-xs text-neutral-500 font-mono mb-2">
                  TEMPERATURE: {temperature.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={e => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-pink-500"
                />
                <div className="flex justify-between text-xs text-neutral-600 mt-1">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>

              {/* Max Tokens */}
              <div>
                <label className="block text-xs text-neutral-500 font-mono mb-2">
                  MAX TOKENS: {maxTokens}
                </label>
                <input
                  type="range"
                  min="256"
                  max="8192"
                  step="256"
                  value={maxTokens}
                  onChange={e => setMaxTokens(parseInt(e.target.value))}
                  className="w-full accent-pink-500"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-neutral-500">
            <MessageSquare size={48} className="mb-4 opacity-50" />
            <p className="text-lg mb-2">Start a conversation</p>
            <p className="text-sm">Select a model and send a message</p>

            {/* Quick Start Cards */}
            {registry && (
              <div className="grid grid-cols-2 gap-4 mt-8 w-full max-w-2xl">
                <Card
                  className="hover:border-pink-500/30 cursor-pointer transition-colors"
                  onClick={() => {
                    setSelectedModel(registry.quick_picks.nsfw_creative);
                    setInput('Write a steamy scene between two characters meeting at a masquerade ball.');
                  }}
                >
                  <div className="flex items-center gap-3">
                    <Heart size={24} className="text-pink-500" />
                    <div>
                      <p className="font-medium text-neutral-200">Creative Writing</p>
                      <p className="text-xs text-neutral-500">NSFW-capable models</p>
                    </div>
                  </div>
                </Card>

                <Card
                  className="hover:border-cyan-500/30 cursor-pointer transition-colors"
                  onClick={() => {
                    setSelectedModel(registry.quick_picks.coding);
                    setInput('Write a Python function to parse JSON with error handling.');
                  }}
                >
                  <div className="flex items-center gap-3">
                    <Code size={24} className="text-cyan-500" />
                    <div>
                      <p className="font-medium text-neutral-200">Coding</p>
                      <p className="text-xs text-neutral-500">Code generation models</p>
                    </div>
                  </div>
                </Card>

                <Card
                  className="hover:border-purple-500/30 cursor-pointer transition-colors"
                  onClick={() => {
                    setSelectedModel(registry.quick_picks.reasoning);
                    setInput('Explain step by step how to solve: If 3x + 7 = 22, what is x?');
                  }}
                >
                  <div className="flex items-center gap-3">
                    <Brain size={24} className="text-purple-500" />
                    <div>
                      <p className="font-medium text-neutral-200">Reasoning</p>
                      <p className="text-xs text-neutral-500">Deep thinking models</p>
                    </div>
                  </div>
                </Card>

                <Card
                  className="hover:border-amber-500/30 cursor-pointer transition-colors"
                  onClick={() => {
                    setSelectedModel('current');
                    setInput('Hello! What can you help me with today?');
                  }}
                >
                  <div className="flex items-center gap-3">
                    <Sparkles size={24} className="text-amber-500" />
                    <div>
                      <p className="font-medium text-neutral-200">General</p>
                      <p className="text-xs text-neutral-500">Currently loaded model</p>
                    </div>
                  </div>
                </Card>
              </div>
            )}
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={message.id}
              className={`group flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 relative ${
                  message.role === 'user'
                    ? 'bg-pink-500/20 border border-pink-500/30 text-neutral-200'
                    : 'bg-surface-raised border border-neutral-700 text-neutral-300'
                }`}
              >
                {/* Message content with code block styling */}
                <div className="whitespace-pre-wrap prose prose-invert prose-sm max-w-none">
                  {message.content.split('```').map((part, i) => {
                    if (i % 2 === 1) {
                      // Code block
                      const [lang, ...code] = part.split('\n');
                      return (
                        <pre key={i} className="bg-neutral-900 rounded-lg p-3 overflow-x-auto my-2 text-sm">
                          <code className={`language-${lang || 'text'}`}>{code.join('\n')}</code>
                        </pre>
                      );
                    }
                    return <span key={i}>{part}</span>;
                  })}
                </div>

                {/* Action buttons - visible on hover */}
                <div className={`absolute -bottom-8 ${message.role === 'user' ? 'right-0' : 'left-0'} flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity`}>
                  <button
                    onClick={() => copyToClipboard(message.content, message.id)}
                    className="p-1.5 rounded-lg bg-surface-default border border-neutral-700 hover:border-pink-500/50 transition-colors"
                    title="Copy to clipboard"
                  >
                    {copiedId === message.id ? (
                      <Check size={12} className="text-emerald-500" />
                    ) : (
                      <Copy size={12} className="text-neutral-400" />
                    )}
                  </button>
                  {message.role === 'assistant' && index === messages.length - 1 && (
                    <button
                      onClick={regenerateResponse}
                      className="p-1.5 rounded-lg bg-surface-default border border-neutral-700 hover:border-pink-500/50 transition-colors"
                      title="Regenerate response"
                    >
                      <RotateCcw size={12} className="text-neutral-400" />
                    </button>
                  )}
                </div>

                {/* Model info */}
                {message.model && (
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-neutral-700/50">
                    <Cpu size={10} className="text-neutral-500" />
                    <span className="text-xs text-neutral-500">{message.model}</span>
                    {message.tokens && (
                      <span className="text-xs text-neutral-600">| {message.tokens} tokens</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-surface-raised border border-neutral-700 rounded-2xl px-4 py-3 flex items-center gap-3">
              <Loader2 size={16} className="animate-spin text-pink-500" />
              <span className="text-neutral-400">Generating...</span>
              <button
                onClick={stopGeneration}
                className="px-2 py-1 rounded-lg bg-red-500/10 border border-red-500/30 hover:bg-red-500/20 transition-colors flex items-center gap-1"
              >
                <Square size={10} className="text-red-400" />
                <span className="text-xs text-red-400">Stop</span>
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="px-6 pb-6 pt-4 border-t border-neutral-800">
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message... (Shift+Enter for new line)"
            className="flex-1 bg-surface-default border border-neutral-700 rounded-xl px-4 py-3 text-neutral-200 placeholder-neutral-500 resize-none focus:outline-none focus:border-pink-500/50 transition-colors"
            rows={2}
            disabled={isLoading}
          />
          <Button
            variant="primary"
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            icon={isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
            className="self-end"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
};
