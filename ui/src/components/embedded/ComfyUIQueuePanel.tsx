'use client';

import { useState, useEffect, useCallback } from 'react';

const COMFYUI_URL = 'http://192.168.1.203:8188';

// Preset workflows for quick generation
const PRESETS = {
  portrait: {
    id: 'portrait',
    name: 'Portrait',
    icon: '👤',
    description: 'High-quality character portrait',
    steps: 30,
    cfg: 7,
  },
  landscape: {
    id: 'landscape',
    name: 'Landscape',
    icon: '🏔️',
    description: 'Scenic environment generation',
    steps: 25,
    cfg: 6,
  },
  concept: {
    id: 'concept',
    name: 'Concept Art',
    icon: '🎨',
    description: 'Detailed concept artwork',
    steps: 40,
    cfg: 8,
  },
  anime: {
    id: 'anime',
    name: 'Anime',
    icon: '✨',
    description: 'Anime/manga style',
    steps: 28,
    cfg: 7,
  },
  photo: {
    id: 'photo',
    name: 'Photorealistic',
    icon: '📷',
    description: 'Photorealistic generation',
    steps: 35,
    cfg: 5,
  },
};

type PresetKey = keyof typeof PRESETS;

interface QueueItem {
  id: string;
  prompt: string;
  preset: PresetKey;
  status: 'queued' | 'running' | 'completed' | 'error';
  progress?: number; // 0-100
  startedAt?: string;
  completedAt?: string;
  imageUrl?: string;
  error?: string;
}

interface SystemStatus {
  queueSize: number;
  currentItem?: string;
  gpuMemory: {
    used: number;
    total: number;
  };
  modelsLoaded: string[];
}

interface ComfyUIQueuePanelProps {
  // Show preset buttons
  showPresets?: boolean;
  // Show queue list
  showQueue?: boolean;
  // Show recent generations
  showRecent?: boolean;
  // Compact mode
  compact?: boolean;
  // Height
  height?: number;
  // Show header
  showHeader?: boolean;
  // Max items to show in queue
  maxQueueItems?: number;
}

export function ComfyUIQueuePanel({
  showPresets = true,
  showQueue = true,
  showRecent = true,
  compact = false,
  height = 400,
  showHeader = true,
  maxQueueItems = 5,
}: ComfyUIQueuePanelProps) {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [recentImages, setRecentImages] = useState<QueueItem[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [promptInput, setPromptInput] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<PresetKey>('portrait');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch queue and system status
  const fetchStatus = useCallback(async () => {
    try {
      // In production, this would call ComfyUI API
      // For now, simulate with mock data
      const mockQueue: QueueItem[] = [
        {
          id: 'q1',
          prompt: 'A warrior princess in golden armor, dramatic lighting',
          preset: 'portrait',
          status: 'running',
          progress: 65,
          startedAt: new Date(Date.now() - 30000).toISOString(),
        },
        {
          id: 'q2',
          prompt: 'Mystical forest with glowing mushrooms',
          preset: 'landscape',
          status: 'queued',
        },
      ];

      const mockRecent: QueueItem[] = [
        {
          id: 'r1',
          prompt: 'Cyberpunk city at night, neon lights',
          preset: 'concept',
          status: 'completed',
          completedAt: new Date(Date.now() - 300000).toISOString(),
          imageUrl: '/api/placeholder/256/256',
        },
        {
          id: 'r2',
          prompt: 'Portrait of an elf queen',
          preset: 'portrait',
          status: 'completed',
          completedAt: new Date(Date.now() - 600000).toISOString(),
          imageUrl: '/api/placeholder/256/256',
        },
        {
          id: 'r3',
          prompt: 'Dragon flying over mountains',
          preset: 'concept',
          status: 'error',
          completedAt: new Date(Date.now() - 900000).toISOString(),
          error: 'Out of VRAM',
        },
      ];

      const mockStatus: SystemStatus = {
        queueSize: mockQueue.length,
        currentItem: mockQueue.find((q) => q.status === 'running')?.id,
        gpuMemory: {
          used: 12.3,
          total: 16.0,
        },
        modelsLoaded: ['SDXL-Base', 'VAE-FT', 'ControlNet-Canny'],
      };

      setQueue(mockQueue);
      setRecentImages(mockRecent);
      setSystemStatus(mockStatus);
      setIsLoading(false);
      setError(null);
    } catch (err) {
      setError('Failed to connect to ComfyUI');
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Submit a new generation
  const submitGeneration = async (preset?: PresetKey) => {
    if (!promptInput.trim()) return;

    setIsSubmitting(true);
    try {
      // In production: POST to ComfyUI API
      await new Promise((resolve) => setTimeout(resolve, 500));

      const newItem: QueueItem = {
        id: `q${Date.now()}`,
        prompt: promptInput,
        preset: preset || selectedPreset,
        status: 'queued',
      };

      setQueue((prev) => [...prev, newItem]);
      setPromptInput('');
    } catch (err) {
      setError('Failed to submit generation');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Cancel a queued item
  const cancelItem = async (itemId: string) => {
    try {
      await new Promise((resolve) => setTimeout(resolve, 200));
      setQueue((prev) => prev.filter((q) => q.id !== itemId));
    } catch (err) {
      setError('Failed to cancel item');
    }
  };

  // Get status color
  const getStatusColor = (status: QueueItem['status']) => {
    switch (status) {
      case 'completed':
        return 'var(--hydra-green)';
      case 'error':
        return 'var(--hydra-red)';
      case 'running':
        return 'var(--hydra-cyan)';
      case 'queued':
        return 'var(--hydra-yellow)';
      default:
        return 'var(--hydra-text-muted)';
    }
  };

  // Format relative time
  const formatRelativeTime = (dateString: string) => {
    const diff = Date.now() - new Date(dateString).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  };

  if (compact) {
    return (
      <div className="comfyui-compact flex items-center gap-3">
        {/* Queue status */}
        <div
          className="flex items-center gap-1.5 px-2 py-1 rounded text-xs"
          style={{
            backgroundColor:
              queue.length > 0
                ? 'rgba(234, 179, 8, 0.1)'
                : 'rgba(107, 114, 128, 0.1)',
            border: '1px solid',
            borderColor: queue.length > 0 ? 'var(--hydra-yellow)' : 'var(--hydra-border)',
            color: queue.length > 0 ? 'var(--hydra-yellow)' : 'var(--hydra-text-muted)',
          }}
        >
          <span>🎨</span>
          <span>{queue.length} queued</span>
        </div>

        {/* Current progress */}
        {queue.find((q) => q.status === 'running') && (
          <div className="flex items-center gap-1.5">
            <div
              className="w-16 h-1.5 rounded-full overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-border)' }}
            >
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${queue.find((q) => q.status === 'running')?.progress || 0}%`,
                  backgroundColor: 'var(--hydra-cyan)',
                }}
              />
            </div>
            <span className="text-xs" style={{ color: 'var(--hydra-cyan)' }}>
              {queue.find((q) => q.status === 'running')?.progress || 0}%
            </span>
          </div>
        )}

        {/* VRAM usage */}
        {systemStatus && (
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            VRAM: {systemStatus.gpuMemory.used.toFixed(1)}/{systemStatus.gpuMemory.total}GB
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="comfyui-queue-panel flex flex-col" style={{ height }}>
      {showHeader && (
        <div
          className="flex items-center justify-between px-3 py-2 border-b"
          style={{ borderColor: 'var(--hydra-border)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
              Image Generation
            </span>
            {systemStatus && (
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor:
                    queue.length > 0
                      ? 'rgba(234, 179, 8, 0.1)'
                      : 'rgba(34, 197, 94, 0.1)',
                  color: queue.length > 0 ? 'var(--hydra-yellow)' : 'var(--hydra-green)',
                }}
              >
                {queue.length} in queue
              </span>
            )}
          </div>
          <a
            href={COMFYUI_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 rounded transition-colors hover:bg-white/10"
            style={{ color: 'var(--hydra-cyan)' }}
          >
            Open ComfyUI →
          </a>
        </div>
      )}

      <div className="flex-1 overflow-auto p-3 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div
              className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--hydra-cyan)', borderTopColor: 'transparent' }}
            />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <span style={{ color: 'var(--hydra-red)' }}>⚠️ {error}</span>
            <button
              onClick={fetchStatus}
              className="text-xs px-2 py-1 rounded"
              style={{ backgroundColor: 'var(--hydra-cyan)', color: 'var(--hydra-bg)' }}
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* Quick Prompt Input */}
            <div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={promptInput}
                  onChange={(e) => setPromptInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && submitGeneration()}
                  placeholder="Enter prompt..."
                  className="flex-1 px-2 py-1.5 rounded text-sm border"
                  style={{
                    backgroundColor: 'var(--hydra-bg)',
                    borderColor: 'var(--hydra-border)',
                    color: 'var(--hydra-text)',
                  }}
                />
                <button
                  onClick={() => submitGeneration()}
                  disabled={isSubmitting || !promptInput.trim()}
                  className="px-3 py-1.5 rounded text-sm font-medium transition-colors disabled:opacity-50"
                  style={{
                    backgroundColor: 'var(--hydra-cyan)',
                    color: 'var(--hydra-bg)',
                  }}
                >
                  {isSubmitting ? '...' : 'Generate'}
                </button>
              </div>
            </div>

            {/* Presets */}
            {showPresets && (
              <div>
                <div
                  className="text-xs font-medium mb-2"
                  style={{ color: 'var(--hydra-text-muted)' }}
                >
                  Quick Presets
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(PRESETS).map(([key, preset]) => (
                    <button
                      key={key}
                      onClick={() => setSelectedPreset(key as PresetKey)}
                      className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-all hover:scale-105"
                      style={{
                        backgroundColor:
                          selectedPreset === key
                            ? 'rgba(139, 92, 246, 0.2)'
                            : 'var(--hydra-bg)',
                        borderColor:
                          selectedPreset === key
                            ? 'var(--hydra-purple)'
                            : 'var(--hydra-border)',
                        border: '1px solid',
                        color:
                          selectedPreset === key
                            ? 'var(--hydra-purple)'
                            : 'var(--hydra-text)',
                      }}
                      title={preset.description}
                    >
                      <span>{preset.icon}</span>
                      <span>{preset.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Current Queue */}
            {showQueue && queue.length > 0 && (
              <div>
                <div
                  className="text-xs font-medium mb-2"
                  style={{ color: 'var(--hydra-text-muted)' }}
                >
                  Queue
                </div>
                <div className="space-y-2">
                  {queue.slice(0, maxQueueItems).map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center gap-2 p-2 rounded border"
                      style={{
                        backgroundColor: 'var(--hydra-bg)',
                        borderColor: 'var(--hydra-border)',
                      }}
                    >
                      <span className="text-lg">{PRESETS[item.preset]?.icon || '🎨'}</span>
                      <div className="flex-1 min-w-0">
                        <div
                          className="text-sm truncate"
                          style={{ color: 'var(--hydra-text)' }}
                        >
                          {item.prompt}
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className="text-xs"
                            style={{ color: getStatusColor(item.status) }}
                          >
                            {item.status === 'running'
                              ? `Running ${item.progress || 0}%`
                              : item.status}
                          </span>
                          {item.status === 'running' && (
                            <div
                              className="flex-1 h-1 rounded-full overflow-hidden max-w-[100px]"
                              style={{ backgroundColor: 'var(--hydra-border)' }}
                            >
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${item.progress || 0}%`,
                                  backgroundColor: 'var(--hydra-cyan)',
                                }}
                              />
                            </div>
                          )}
                        </div>
                      </div>
                      {item.status === 'queued' && (
                        <button
                          onClick={() => cancelItem(item.id)}
                          className="text-xs px-1.5 py-0.5 rounded transition-colors hover:bg-red-500/20"
                          style={{ color: 'var(--hydra-red)' }}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Generations */}
            {showRecent && recentImages.length > 0 && (
              <div>
                <div
                  className="text-xs font-medium mb-2"
                  style={{ color: 'var(--hydra-text-muted)' }}
                >
                  Recent
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {recentImages.slice(0, 6).map((item) => (
                    <div
                      key={item.id}
                      className="relative aspect-square rounded border overflow-hidden group"
                      style={{
                        backgroundColor: 'var(--hydra-bg)',
                        borderColor: 'var(--hydra-border)',
                      }}
                    >
                      {item.status === 'completed' && item.imageUrl ? (
                        <div
                          className="w-full h-full"
                          style={{
                            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
                          }}
                        >
                          <div className="absolute inset-0 flex items-center justify-center text-2xl opacity-30">
                            {PRESETS[item.preset]?.icon || '🎨'}
                          </div>
                        </div>
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <span style={{ color: getStatusColor(item.status) }}>
                            {item.status === 'error' ? '⚠️' : '⏳'}
                          </span>
                        </div>
                      )}
                      <div
                        className="absolute inset-0 bg-black/70 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 flex flex-col justify-end"
                      >
                        <div
                          className="text-xs line-clamp-2"
                          style={{ color: 'var(--hydra-text)' }}
                        >
                          {item.prompt}
                        </div>
                        <div
                          className="text-xs mt-0.5"
                          style={{ color: 'var(--hydra-text-muted)' }}
                        >
                          {item.completedAt && formatRelativeTime(item.completedAt)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* System Status Footer */}
      {systemStatus && (
        <div
          className="px-3 py-2 border-t flex items-center justify-between text-xs"
          style={{ borderColor: 'var(--hydra-border)', backgroundColor: 'rgba(0,0,0,0.2)' }}
        >
          <div className="flex items-center gap-3">
            <span style={{ color: 'var(--hydra-text-muted)' }}>
              VRAM: {systemStatus.gpuMemory.used.toFixed(1)}/{systemStatus.gpuMemory.total}GB
            </span>
            <div
              className="w-20 h-1.5 rounded-full overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-border)' }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(systemStatus.gpuMemory.used / systemStatus.gpuMemory.total) * 100}%`,
                  backgroundColor:
                    systemStatus.gpuMemory.used / systemStatus.gpuMemory.total > 0.9
                      ? 'var(--hydra-red)'
                      : systemStatus.gpuMemory.used / systemStatus.gpuMemory.total > 0.7
                      ? 'var(--hydra-yellow)'
                      : 'var(--hydra-green)',
                }}
              />
            </div>
          </div>
          <span style={{ color: 'var(--hydra-text-muted)' }}>
            {systemStatus.modelsLoaded.length} models loaded
          </span>
        </div>
      )}
    </div>
  );
}

// Standalone generate button with preset
interface QuickGenerateButtonProps {
  preset: PresetKey;
  prompt: string;
  showLabel?: boolean;
}

export function QuickGenerateButton({
  preset,
  prompt,
  showLabel = true,
}: QuickGenerateButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const config = PRESETS[preset];

  const generate = async () => {
    setIsGenerating(true);
    try {
      // In production: POST to ComfyUI
      await new Promise((resolve) => setTimeout(resolve, 1000));
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <button
      onClick={generate}
      disabled={isGenerating}
      className="flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all hover:scale-105 disabled:opacity-50"
      style={{
        backgroundColor: 'rgba(139, 92, 246, 0.1)',
        border: '1px solid var(--hydra-purple)',
        color: 'var(--hydra-purple)',
      }}
      title={prompt}
    >
      {isGenerating ? (
        <span
          className="w-3 h-3 border border-t-transparent rounded-full animate-spin"
          style={{ borderColor: 'currentColor', borderTopColor: 'transparent' }}
        />
      ) : (
        <span>{config.icon}</span>
      )}
      {showLabel && <span>{config.name}</span>}
    </button>
  );
}
