'use client';

import { useState, useEffect, useCallback } from 'react';
import { StatusIndicator } from '../StatusIndicator';

interface VoicePipelineStatus {
  wake_word: {
    enabled: boolean;
    model: string;
    sensitivity: number;
    last_activation: string | null;
  };
  stt: {
    engine: string;
    status: 'ready' | 'loading' | 'error' | 'offline';
    model: string;
    latency_ms: number | null;
  };
  llm: {
    router: string;
    status: 'ready' | 'loading' | 'error' | 'offline';
    active_model: string | null;
    latency_ms: number | null;
  };
  tts: {
    engine: string;
    status: 'ready' | 'loading' | 'error' | 'offline';
    voice: string;
    latency_ms: number | null;
  };
  overall_latency_ms: number | null;
  target_latency_ms: number;
}

const VOICE_API_URL = process.env.NEXT_PUBLIC_VOICE_URL || 'http://192.168.1.244:8850';
const WAKEWORD_API_URL = process.env.NEXT_PUBLIC_WAKEWORD_URL || 'http://192.168.1.244:8860';

export function VoiceView() {
  const [pipelineStatus, setPipelineStatus] = useState<VoicePipelineStatus | null>(null);
  const [wakewordStatus, setWakewordStatus] = useState<{ listening: boolean; total_detections: number } | null>(null);
  const [testText, setTestText] = useState('');
  const [testResponse, setTestResponse] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      // Fetch voice pipeline status
      const voiceResp = await fetch(`${VOICE_API_URL}/status`);
      if (voiceResp.ok) {
        const data = await voiceResp.json();
        setPipelineStatus(data);
      }

      // Fetch wakeword status
      try {
        const wakeResp = await fetch(`${WAKEWORD_API_URL}/status`);
        if (wakeResp.ok) {
          const data = await wakeResp.json();
          setWakewordStatus(data);
        }
      } catch {
        // Wakeword service may not be running
      }

      setError(null);
    } catch (e) {
      setError('Failed to connect to voice services');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleTestVoice = async () => {
    if (!testText.trim()) return;

    setIsLoading(true);
    setTestResponse(null);

    try {
      const resp = await fetch(`${VOICE_API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: testText,
          voice_response: false
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setTestResponse(data.text);
      } else {
        setTestResponse('Error: Failed to get response');
      }
    } catch (e) {
      setTestResponse('Error: Failed to connect to voice service');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleWakeWord = async () => {
    if (!pipelineStatus) return;

    const endpoint = pipelineStatus.wake_word.enabled
      ? '/wake-word/disable'
      : '/wake-word/enable';

    try {
      await fetch(`${VOICE_API_URL}${endpoint}`, { method: 'POST' });
      fetchStatus();
    } catch (e) {
      setError('Failed to toggle wake word');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'online';
      case 'loading': return 'warning';
      case 'error': return 'offline';
      case 'offline': return 'offline';
      default: return 'warning';
    }
  };

  const formatLatency = (ms: number | null) => {
    if (ms === null) return '-';
    return `${ms.toFixed(0)}ms`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-hydra-cyan flex items-center gap-2">
            <span className="text-2xl">🎤</span>
            Voice Interface
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Wake word detection, speech-to-text, and voice responses
          </p>
        </div>
        {pipelineStatus && (
          <div className="text-right">
            <div className="text-sm text-gray-400">Target Latency</div>
            <div className="text-lg font-mono text-hydra-cyan">
              &lt;{pipelineStatus.target_latency_ms}ms
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-300">
          {error}
        </div>
      )}

      {/* Pipeline Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Wake Word */}
        <div className="panel p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-200">Wake Word</h3>
            <StatusIndicator
              status={pipelineStatus?.wake_word.enabled ? 'online' : 'offline'}
              label={pipelineStatus?.wake_word.enabled ? 'Active' : 'Disabled'}
            />
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-400">
              <span>Model</span>
              <span className="text-gray-300">{pipelineStatus?.wake_word.model || '-'}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Detections</span>
              <span className="text-gray-300">{wakewordStatus?.total_detections ?? '-'}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Last Activation</span>
              <span className="text-gray-300">
                {pipelineStatus?.wake_word.last_activation
                  ? new Date(pipelineStatus.wake_word.last_activation).toLocaleTimeString()
                  : 'Never'}
              </span>
            </div>
          </div>
          <button
            onClick={handleToggleWakeWord}
            className={`mt-3 w-full py-2 rounded text-sm font-medium transition-colors ${
              pipelineStatus?.wake_word.enabled
                ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
                : 'bg-hydra-cyan/20 text-hydra-cyan hover:bg-hydra-cyan/30'
            }`}
          >
            {pipelineStatus?.wake_word.enabled ? 'Disable' : 'Enable'} Wake Word
          </button>
        </div>

        {/* STT */}
        <div className="panel p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-200">Speech-to-Text</h3>
            <StatusIndicator
              status={getStatusColor(pipelineStatus?.stt.status || 'offline')}
              label={pipelineStatus?.stt.status || 'Offline'}
            />
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-400">
              <span>Engine</span>
              <span className="text-gray-300">{pipelineStatus?.stt.engine || '-'}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Model</span>
              <span className="text-gray-300">{pipelineStatus?.stt.model || '-'}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Latency</span>
              <span className={`font-mono ${
                (pipelineStatus?.stt.latency_ms ?? 0) < 200 ? 'text-hydra-green' : 'text-hydra-yellow'
              }`}>
                {formatLatency(pipelineStatus?.stt.latency_ms ?? null)}
              </span>
            </div>
          </div>
        </div>

        {/* LLM */}
        <div className="panel p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-200">Language Model</h3>
            <StatusIndicator
              status={getStatusColor(pipelineStatus?.llm.status || 'offline')}
              label={pipelineStatus?.llm.status || 'Offline'}
            />
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-400">
              <span>Router</span>
              <span className="text-gray-300">{pipelineStatus?.llm.router || '-'}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Active Model</span>
              <span className="text-gray-300 truncate max-w-[120px]" title={pipelineStatus?.llm.active_model || '-'}>
                {pipelineStatus?.llm.active_model || '-'}
              </span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Latency</span>
              <span className={`font-mono ${
                (pipelineStatus?.llm.latency_ms ?? 0) < 250 ? 'text-hydra-green' : 'text-hydra-yellow'
              }`}>
                {formatLatency(pipelineStatus?.llm.latency_ms ?? null)}
              </span>
            </div>
          </div>
        </div>

        {/* TTS */}
        <div className="panel p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-200">Text-to-Speech</h3>
            <StatusIndicator
              status={getStatusColor(pipelineStatus?.tts.status || 'offline')}
              label={pipelineStatus?.tts.status || 'Offline'}
            />
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-400">
              <span>Engine</span>
              <span className="text-gray-300">{pipelineStatus?.tts.engine || '-'}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Voice</span>
              <span className="text-gray-300">{pipelineStatus?.tts.voice || '-'}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Latency</span>
              <span className={`font-mono ${
                (pipelineStatus?.tts.latency_ms ?? 0) < 100 ? 'text-hydra-green' : 'text-hydra-yellow'
              }`}>
                {formatLatency(pipelineStatus?.tts.latency_ms ?? null)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Overall Latency */}
      {pipelineStatus?.overall_latency_ms && (
        <div className="panel p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-200">Overall Pipeline Latency</h3>
              <p className="text-sm text-gray-400">End-to-end time from speech to response</p>
            </div>
            <div className="text-right">
              <div className={`text-3xl font-mono ${
                pipelineStatus.overall_latency_ms < pipelineStatus.target_latency_ms
                  ? 'text-hydra-green'
                  : pipelineStatus.overall_latency_ms < pipelineStatus.target_latency_ms * 1.5
                    ? 'text-hydra-yellow'
                    : 'text-red-400'
              }`}>
                {formatLatency(pipelineStatus.overall_latency_ms)}
              </div>
              <div className="text-sm text-gray-400">
                Target: {pipelineStatus.target_latency_ms}ms
              </div>
            </div>
          </div>
          {/* Latency bar */}
          <div className="mt-4 h-2 bg-hydra-gray/30 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all ${
                pipelineStatus.overall_latency_ms < pipelineStatus.target_latency_ms
                  ? 'bg-hydra-green'
                  : 'bg-hydra-yellow'
              }`}
              style={{
                width: `${Math.min(
                  (pipelineStatus.overall_latency_ms / pipelineStatus.target_latency_ms) * 100,
                  100
                )}%`
              }}
            />
          </div>
        </div>
      )}

      {/* Test Interface */}
      <div className="panel p-4">
        <h3 className="font-semibold text-gray-200 mb-3">Test Voice Chat</h3>
        <div className="flex gap-3">
          <input
            type="text"
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleTestVoice()}
            placeholder="Type a message to test voice response..."
            className="flex-1 bg-hydra-darker border border-hydra-gray/30 rounded px-4 py-2 text-gray-200 placeholder-gray-500 focus:border-hydra-cyan/50 focus:outline-none"
          />
          <button
            onClick={handleTestVoice}
            disabled={isLoading || !testText.trim()}
            className="px-6 py-2 bg-hydra-cyan/20 text-hydra-cyan rounded hover:bg-hydra-cyan/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Processing...' : 'Send'}
          </button>
        </div>
        {testResponse && (
          <div className="mt-4 p-4 bg-hydra-darker rounded border border-hydra-gray/30">
            <div className="text-sm text-gray-400 mb-1">Response:</div>
            <div className="text-gray-200">{testResponse}</div>
          </div>
        )}
      </div>

      {/* Voice Commands Reference */}
      <div className="panel p-4">
        <h3 className="font-semibold text-gray-200 mb-3">Supported Voice Commands</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
          <div className="space-y-2">
            <h4 className="text-hydra-cyan font-medium">Lighting</h4>
            <ul className="space-y-1 text-gray-400">
              <li>&quot;Turn on the lights&quot;</li>
              <li>&quot;Lights off in bedroom&quot;</li>
              <li>&quot;Dim the living room&quot;</li>
            </ul>
          </div>
          <div className="space-y-2">
            <h4 className="text-hydra-cyan font-medium">Climate</h4>
            <ul className="space-y-1 text-gray-400">
              <li>&quot;What&apos;s the temperature?&quot;</li>
              <li>&quot;Set thermostat to 72&quot;</li>
              <li>&quot;Is it cold outside?&quot;</li>
            </ul>
          </div>
          <div className="space-y-2">
            <h4 className="text-hydra-cyan font-medium">System</h4>
            <ul className="space-y-1 text-gray-400">
              <li>&quot;System status&quot;</li>
              <li>&quot;Switch model to Mistral&quot;</li>
              <li>&quot;How&apos;s the cluster?&quot;</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
