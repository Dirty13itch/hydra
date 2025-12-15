'use client';

import { useState, useEffect, useCallback } from 'react';

interface VoicePipelineStatus {
  wakeWord: {
    enabled: boolean;
    model: string;
    lastActivation?: string;
  };
  stt: {
    engine: string;
    status: 'ready' | 'loading' | 'error' | 'offline';
    model: string;
    latency?: number;
  };
  llm: {
    router: string;
    status: 'ready' | 'loading' | 'error' | 'offline';
    activeModel?: string;
    latency?: number;
  };
  tts: {
    engine: string;
    status: 'ready' | 'loading' | 'error' | 'offline';
    voice: string;
    latency?: number;
  };
  overallLatency?: number;
  targetLatency: number;
}

interface VoiceInterfacePanelProps {
  compact?: boolean;
  showControls?: boolean;
}

const DEFAULT_STATUS: VoicePipelineStatus = {
  wakeWord: {
    enabled: false,
    model: 'porcupine-hydra',
  },
  stt: {
    engine: 'faster-whisper',
    status: 'offline',
    model: 'large-v3',
  },
  llm: {
    router: 'RouteLLM',
    status: 'ready',
    activeModel: 'Mistral-Nemo-12B',
  },
  tts: {
    engine: 'Kokoro',
    status: 'ready',
    voice: 'af_bella',
  },
  targetLatency: 500,
};

export function VoiceInterfacePanel({
  compact = false,
  showControls = true,
}: VoiceInterfacePanelProps) {
  const [status, setStatus] = useState<VoicePipelineStatus>(DEFAULT_STATUS);
  const [isListening, setIsListening] = useState(false);
  const [lastCommand, setLastCommand] = useState<string | null>(null);
  const [testMode, setTestMode] = useState(false);

  // Fetch voice pipeline status
  const fetchStatus = useCallback(async () => {
    try {
      // In production, this would fetch from voice API
      // For now, simulate with mock data
      const mockStatus: VoicePipelineStatus = {
        wakeWord: {
          enabled: false,
          model: 'porcupine-hydra',
          lastActivation: undefined,
        },
        stt: {
          engine: 'faster-whisper',
          status: 'offline',
          model: 'large-v3',
          latency: undefined,
        },
        llm: {
          router: 'RouteLLM',
          status: 'ready',
          activeModel: 'Mistral-Nemo-12B',
          latency: 180,
        },
        tts: {
          engine: 'Kokoro',
          status: 'ready',
          voice: 'af_bella',
          latency: 95,
        },
        overallLatency: undefined,
        targetLatency: 500,
      };
      setStatus(mockStatus);
    } catch (err) {
      console.error('Failed to fetch voice status:', err);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const getStatusColor = (s: 'ready' | 'loading' | 'error' | 'offline') => {
    switch (s) {
      case 'ready':
        return 'var(--hydra-green)';
      case 'loading':
        return 'var(--hydra-yellow)';
      case 'error':
        return 'var(--hydra-red)';
      case 'offline':
        return 'var(--hydra-text-muted)';
    }
  };

  const getStatusBg = (s: 'ready' | 'loading' | 'error' | 'offline') => {
    switch (s) {
      case 'ready':
        return 'rgba(0, 255, 136, 0.1)';
      case 'loading':
        return 'rgba(255, 204, 0, 0.1)';
      case 'error':
        return 'rgba(255, 51, 102, 0.1)';
      case 'offline':
        return 'rgba(136, 136, 136, 0.1)';
    }
  };

  const isPipelineReady =
    status.stt.status === 'ready' &&
    status.llm.status === 'ready' &&
    status.tts.status === 'ready';

  const isLatencyOk =
    status.overallLatency !== undefined &&
    status.overallLatency <= status.targetLatency;

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-2 px-2 py-1 rounded text-xs"
          style={{
            backgroundColor: isPipelineReady
              ? 'rgba(0, 255, 136, 0.1)'
              : 'rgba(136, 136, 136, 0.1)',
            border: '1px solid',
            borderColor: isPipelineReady
              ? 'var(--hydra-green)'
              : 'var(--hydra-border)',
          }}
        >
          <span>🎤</span>
          <span style={{ color: isPipelineReady ? 'var(--hydra-green)' : 'var(--hydra-text-muted)' }}>
            Voice {isPipelineReady ? 'Ready' : 'Offline'}
          </span>
        </div>
        {status.overallLatency && (
          <span
            className="text-xs"
            style={{
              color: isLatencyOk ? 'var(--hydra-green)' : 'var(--hydra-yellow)',
            }}
          >
            {status.overallLatency}ms
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: 'var(--hydra-bg)',
        borderColor: 'var(--hydra-border)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--hydra-border)' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">🎤</span>
          <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
            Voice Interface
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              backgroundColor: isPipelineReady
                ? 'rgba(0, 255, 136, 0.1)'
                : 'rgba(136, 136, 136, 0.1)',
              color: isPipelineReady ? 'var(--hydra-green)' : 'var(--hydra-text-muted)',
            }}
          >
            {isPipelineReady ? 'READY' : 'OFFLINE'}
          </span>
        </div>
        <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
          Target: &lt;{status.targetLatency}ms
        </div>
      </div>

      {/* Pipeline Stages */}
      <div className="p-4 space-y-3">
        {/* Wake Word */}
        <div
          className="flex items-center justify-between p-2 rounded"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
        >
          <div className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full"
              style={{
                backgroundColor: status.wakeWord.enabled
                  ? 'var(--hydra-green)'
                  : 'var(--hydra-text-muted)',
              }}
            />
            <span className="text-sm" style={{ color: 'var(--hydra-text)' }}>
              Wake Word
            </span>
            <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              "Hey Hydra"
            </span>
          </div>
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: status.wakeWord.enabled
                ? 'rgba(0, 255, 136, 0.1)'
                : 'rgba(136, 136, 136, 0.1)',
              color: status.wakeWord.enabled
                ? 'var(--hydra-green)'
                : 'var(--hydra-text-muted)',
            }}
          >
            {status.wakeWord.enabled ? 'LISTENING' : 'DISABLED'}
          </span>
        </div>

        {/* STT */}
        <div
          className="flex items-center justify-between p-2 rounded"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
        >
          <div className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: getStatusColor(status.stt.status) }}
            />
            <span className="text-sm" style={{ color: 'var(--hydra-text)' }}>
              STT
            </span>
            <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              {status.stt.engine} ({status.stt.model})
            </span>
          </div>
          <div className="flex items-center gap-2">
            {status.stt.latency && (
              <span className="text-xs" style={{ color: 'var(--hydra-cyan)' }}>
                {status.stt.latency}ms
              </span>
            )}
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: getStatusBg(status.stt.status),
                color: getStatusColor(status.stt.status),
              }}
            >
              {status.stt.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* LLM Router */}
        <div
          className="flex items-center justify-between p-2 rounded"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
        >
          <div className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: getStatusColor(status.llm.status) }}
            />
            <span className="text-sm" style={{ color: 'var(--hydra-text)' }}>
              LLM
            </span>
            <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              {status.llm.router} → {status.llm.activeModel || 'None'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {status.llm.latency && (
              <span className="text-xs" style={{ color: 'var(--hydra-cyan)' }}>
                {status.llm.latency}ms
              </span>
            )}
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: getStatusBg(status.llm.status),
                color: getStatusColor(status.llm.status),
              }}
            >
              {status.llm.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* TTS */}
        <div
          className="flex items-center justify-between p-2 rounded"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
        >
          <div className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: getStatusColor(status.tts.status) }}
            />
            <span className="text-sm" style={{ color: 'var(--hydra-text)' }}>
              TTS
            </span>
            <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              {status.tts.engine} ({status.tts.voice})
            </span>
          </div>
          <div className="flex items-center gap-2">
            {status.tts.latency && (
              <span className="text-xs" style={{ color: 'var(--hydra-cyan)' }}>
                {status.tts.latency}ms
              </span>
            )}
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: getStatusBg(status.tts.status),
                color: getStatusColor(status.tts.status),
              }}
            >
              {status.tts.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Overall Latency */}
        {status.overallLatency && (
          <div
            className="flex items-center justify-between p-2 rounded border"
            style={{
              backgroundColor: isLatencyOk
                ? 'rgba(0, 255, 136, 0.05)'
                : 'rgba(255, 204, 0, 0.05)',
              borderColor: isLatencyOk ? 'var(--hydra-green)' : 'var(--hydra-yellow)',
            }}
          >
            <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
              End-to-End Latency
            </span>
            <span
              className="text-lg font-bold"
              style={{
                color: isLatencyOk ? 'var(--hydra-green)' : 'var(--hydra-yellow)',
              }}
            >
              {status.overallLatency}ms
            </span>
          </div>
        )}
      </div>

      {/* Controls */}
      {showControls && (
        <div
          className="px-4 py-3 border-t flex items-center justify-between"
          style={{ borderColor: 'var(--hydra-border)', backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
        >
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTestMode(!testMode)}
              className="text-xs px-3 py-1.5 rounded transition-colors"
              style={{
                backgroundColor: testMode ? 'rgba(0, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.3)',
                color: testMode ? 'var(--hydra-cyan)' : 'var(--hydra-text-muted)',
                border: '1px solid',
                borderColor: testMode ? 'var(--hydra-cyan)' : 'var(--hydra-border)',
              }}
            >
              {testMode ? 'Exit Test' : 'Test Mode'}
            </button>
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            {lastCommand ? `Last: "${lastCommand}"` : 'No recent commands'}
          </div>
        </div>
      )}
    </div>
  );
}
