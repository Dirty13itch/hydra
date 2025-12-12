'use client';

import { useEffect, useState } from 'react';
import api, { OllamaModel, OllamaRunningModel, GpuInfo } from '@/lib/api';

interface AIModelsPanelProps {
  gpus: GpuInfo[];
}

function formatSize(bytes: number): string {
  const gb = bytes / (1024 * 1024 * 1024);
  if (gb >= 1) return `${gb.toFixed(1)} GB`;
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(0)} MB`;
}

export function AIModelsPanel({ gpus }: AIModelsPanelProps) {
  const [availableModels, setAvailableModels] = useState<OllamaModel[]>([]);
  const [runningModels, setRunningModels] = useState<OllamaRunningModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingModel, setLoadingModel] = useState<string | null>(null);
  const [unloadingModel, setUnloadingModel] = useState<string | null>(null);
  const [showAllModels, setShowAllModels] = useState(false);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const [modelsData, runningData] = await Promise.all([
          api.ollamaModels().catch(() => ({ models: [] })),
          api.ollamaRunning().catch(() => ({ models: [] })),
        ]);
        setAvailableModels(modelsData.models || []);
        setRunningModels(runningData.models || []);
        setError(null);
      } catch (err) {
        setError('Failed to fetch model data');
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
    const interval = setInterval(fetchModels, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleLoadModel = async (modelName: string) => {
    setLoadingModel(modelName);
    try {
      await api.ollamaLoadModel(modelName);
      // Refresh models after a delay
      setTimeout(async () => {
        const runningData = await api.ollamaRunning().catch(() => ({ models: [] }));
        setRunningModels(runningData.models || []);
        setLoadingModel(null);
      }, 2000);
    } catch (err) {
      console.error('Failed to load model:', err);
      setLoadingModel(null);
    }
  };

  const handleUnloadModel = async (modelName: string) => {
    setUnloadingModel(modelName);
    try {
      await api.ollamaUnloadModel(modelName);
      // Refresh models after a delay
      setTimeout(async () => {
        const runningData = await api.ollamaRunning().catch(() => ({ models: [] }));
        setRunningModels(runningData.models || []);
        setUnloadingModel(null);
      }, 1000);
    } catch (err) {
      console.error('Failed to unload model:', err);
      setUnloadingModel(null);
    }
  };

  // Get models not currently running
  const unloadedModels = availableModels.filter(
    m => !runningModels.some(r => r.name === m.name || r.name.startsWith(m.name.split(':')[0]))
  );

  const totalVram = gpus.reduce((sum, g) => sum + (g.memory_total_gb || 0), 0);
  const usedVram = gpus.reduce((sum, g) => sum + (g.memory_used_gb || 0), 0);
  const vramPct = totalVram > 0 ? (usedVram / totalVram) * 100 : 0;

  return (
    <div className="panel p-4" style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}>
      <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
        AI Models
      </h3>

      {/* VRAM Summary */}
      <div className="mb-4 p-3 rounded border" style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--hydra-text-muted)' }}>
            Total VRAM
          </span>
          <span className="text-sm font-medium" style={{ color: 'var(--hydra-cyan)' }}>
            {usedVram.toFixed(1)} / {totalVram.toFixed(1)} GB
          </span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--hydra-bg-secondary)' }}>
          <div
            className="h-full transition-all duration-300"
            style={{
              width: `${vramPct}%`,
              backgroundColor: vramPct > 90 ? 'var(--hydra-red)' : vramPct > 70 ? 'var(--hydra-yellow)' : 'var(--hydra-green)'
            }}
          />
        </div>
      </div>

      {/* Running Models */}
      <div className="mb-3">
        <div className="text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--hydra-text-muted)' }}>
          Running ({runningModels.length})
        </div>
        {loading ? (
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>Loading...</div>
        ) : error ? (
          <div className="text-xs" style={{ color: 'var(--hydra-red)' }}>{error}</div>
        ) : runningModels.length === 0 ? (
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>No models loaded</div>
        ) : (
          <div className="space-y-2">
            {runningModels.map((model, i) => (
              <div
                key={i}
                className="p-2 rounded border group"
                style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'rgba(0, 255, 136, 0.3)' }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium truncate" style={{ color: 'var(--hydra-green)' }}>
                    {model.name.split(':')[0]}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(0, 255, 136, 0.15)', color: 'var(--hydra-green)' }}>
                      LOADED
                    </span>
                    <button
                      onClick={() => handleUnloadModel(model.name)}
                      disabled={unloadingModel === model.name}
                      className="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-0.5 text-xs rounded"
                      style={{
                        backgroundColor: unloadingModel === model.name ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: unloadingModel === model.name ? 'var(--hydra-yellow)' : 'var(--hydra-red)',
                        cursor: unloadingModel === model.name ? 'wait' : 'pointer'
                      }}
                    >
                      {unloadingModel === model.name ? 'Unloading...' : 'Unload'}
                    </button>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                    VRAM: {formatSize(model.size_vram)}
                  </span>
                  <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                    {model.name.split(':')[1] || 'latest'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Available Models */}
      <div className="pt-2 border-t" style={{ borderColor: 'var(--hydra-border)' }}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs uppercase tracking-wider" style={{ color: 'var(--hydra-text-muted)' }}>
            Available ({unloadedModels.length})
          </span>
          {unloadedModels.length > 4 && (
            <button
              onClick={() => setShowAllModels(!showAllModels)}
              className="text-xs hover:underline"
              style={{ color: 'var(--hydra-cyan)' }}
            >
              {showAllModels ? 'Show less' : 'Show all'}
            </button>
          )}
        </div>
        {unloadedModels.length > 0 && (
          <div className="space-y-1.5">
            {(showAllModels ? unloadedModels : unloadedModels.slice(0, 4)).map((model, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-1.5 rounded group"
                style={{ backgroundColor: 'var(--hydra-bg)' }}
              >
                <div className="flex-1 min-w-0">
                  <span className="text-xs truncate block" style={{ color: 'var(--hydra-text-secondary)' }} title={model.name}>
                    {model.name.split(':')[0]}
                  </span>
                  <span className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>
                    {formatSize(model.size)} • {model.details?.parameter_size || ''}
                  </span>
                </div>
                <button
                  onClick={() => handleLoadModel(model.name)}
                  disabled={loadingModel === model.name}
                  className="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-0.5 text-xs rounded ml-2"
                  style={{
                    backgroundColor: loadingModel === model.name ? 'rgba(234, 179, 8, 0.2)' : 'rgba(0, 255, 136, 0.2)',
                    color: loadingModel === model.name ? 'var(--hydra-yellow)' : 'var(--hydra-green)',
                    cursor: loadingModel === model.name ? 'wait' : 'pointer'
                  }}
                >
                  {loadingModel === model.name ? 'Loading...' : 'Load'}
                </button>
              </div>
            ))}
            {!showAllModels && unloadedModels.length > 4 && (
              <div className="text-xs text-center py-1" style={{ color: 'var(--hydra-text-muted)' }}>
                +{unloadedModels.length - 4} more models
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
