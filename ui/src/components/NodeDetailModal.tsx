'use client';

import { useEffect } from 'react';
import { StatusIndicator } from './StatusIndicator';
import { GpuInfo } from '@/lib/api';

interface NodeDetailModalProps {
  name: string;
  role: string;
  cpu?: number;
  memory?: number;
  status: 'online' | 'offline' | 'unknown';
  gpus?: string[];
  gpuMetrics?: GpuInfo[];
  ip?: string;
  onClose: () => void;
}

export function NodeDetailModal({
  name,
  role,
  cpu,
  memory,
  status,
  gpus,
  gpuMetrics,
  ip,
  onClose
}: NodeDetailModalProps) {
  const toFahrenheit = (celsius: number) => Math.round((celsius * 9/5) + 32);

  const getTempColor = (tempC: number) => {
    if (tempC >= 80) return 'text-hydra-red';
    if (tempC >= 65) return 'text-hydra-yellow';
    return 'text-hydra-green';
  };

  const getUtilColor = (util: number) => {
    if (util >= 90) return 'text-hydra-red';
    if (util >= 50) return 'text-hydra-yellow';
    return 'text-hydra-green';
  };

  const getBarColor = (pct: number) => {
    if (pct >= 90) return 'bg-hydra-red';
    if (pct >= 70) return 'bg-hydra-yellow';
    return 'bg-hydra-cyan';
  };

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Calculate total VRAM if GPUs available
  const totalVram = gpuMetrics?.reduce((sum, g) => sum + (g.memory_total_gb || 0), 0) || 0;
  const usedVram = gpuMetrics?.reduce((sum, g) => sum + (g.memory_used_gb || 0), 0) || 0;
  const totalPower = gpuMetrics?.reduce((sum, g) => sum + (g.power_w || 0), 0) || 0;

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-hydra-darker border border-hydra-cyan/30 rounded-lg w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-hydra-gray/30">
          <div className="flex items-center gap-4">
            <StatusIndicator status={status} pulse={status === 'online'} />
            <div>
              <h2 className="text-xl font-bold text-hydra-cyan">{name}</h2>
              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span className="uppercase tracking-wider">{role}</span>
                {ip && <span className="text-gray-600">|</span>}
                {ip && <span className="font-mono">{ip}</span>}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-2xl leading-none p-1"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* System Resources */}
          <div className="grid grid-cols-2 gap-6">
            {/* CPU */}
            <div className="bg-hydra-dark/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-400 uppercase tracking-wider">CPU Usage</span>
                <span className={`text-2xl font-bold ${cpu && cpu > 80 ? 'text-hydra-red' : 'text-hydra-green'}`}>
                  {cpu !== undefined ? `${cpu.toFixed(1)}%` : '--'}
                </span>
              </div>
              <div className="h-3 bg-hydra-darker rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getBarColor(cpu || 0)}`}
                  style={{ width: `${cpu || 0}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-xs text-gray-500">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Memory */}
            <div className="bg-hydra-dark/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-400 uppercase tracking-wider">Memory</span>
                <span className={`text-2xl font-bold ${memory && memory > 80 ? 'text-hydra-red' : 'text-hydra-magenta'}`}>
                  {memory !== undefined ? `${memory.toFixed(1)}%` : '--'}
                </span>
              </div>
              <div className="h-3 bg-hydra-darker rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${memory && memory > 80 ? 'bg-hydra-red' : 'bg-hydra-magenta'}`}
                  style={{ width: `${memory || 0}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-xs text-gray-500">
                <span>0%</span>
                <span>50%</span>
                <span>100%</span>
              </div>
            </div>
          </div>

          {/* GPU Summary */}
          {gpuMetrics && gpuMetrics.length > 0 && (
            <div className="bg-hydra-dark/50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-gray-400 uppercase tracking-wider">GPU Summary</span>
                <span className="text-xs text-hydra-cyan">{gpuMetrics.length} GPU{gpuMetrics.length > 1 ? 's' : ''}</span>
              </div>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-xs text-gray-500 uppercase mb-1">Total VRAM</div>
                  <div className="text-lg font-bold text-hydra-magenta">
                    {usedVram.toFixed(1)} / {totalVram.toFixed(0)} GB
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase mb-1">Total Power</div>
                  <div className="text-lg font-bold text-hydra-yellow">
                    {totalPower.toFixed(0)} W
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 uppercase mb-1">Avg Temp</div>
                  <div className={`text-lg font-bold ${getTempColor(gpuMetrics.reduce((sum, g) => sum + g.temp_c, 0) / gpuMetrics.length)}`}>
                    {toFahrenheit(gpuMetrics.reduce((sum, g) => sum + g.temp_c, 0) / gpuMetrics.length)}°F
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Individual GPUs */}
          {gpuMetrics && gpuMetrics.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm text-gray-400 uppercase tracking-wider">GPU Details</h3>
              {gpuMetrics.map((gpu, i) => {
                const memPct = gpu.memory_used_gb !== undefined && gpu.memory_total_gb
                  ? (gpu.memory_used_gb / gpu.memory_total_gb) * 100
                  : 0;
                return (
                  <div key={i} className="bg-hydra-dark/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-hydra-cyan font-medium">{gpu.name}</span>
                      <span className={`text-sm ${getTempColor(gpu.temp_c)}`}>
                        {toFahrenheit(gpu.temp_c)}°F ({gpu.temp_c}°C)
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      {/* Utilization */}
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-500">Utilization</span>
                          <span className={getUtilColor(gpu.utilization)}>{gpu.utilization}%</span>
                        </div>
                        <div className="h-2 bg-hydra-darker rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${getBarColor(gpu.utilization)}`}
                            style={{ width: `${gpu.utilization}%` }}
                          />
                        </div>
                      </div>

                      {/* Power */}
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-500">Power Draw</span>
                          <span className="text-hydra-yellow">{gpu.power_w.toFixed(0)}W</span>
                        </div>
                        <div className="h-2 bg-hydra-darker rounded-full overflow-hidden">
                          <div
                            className="h-full transition-all duration-500 bg-hydra-yellow"
                            style={{ width: `${Math.min((gpu.power_w / 350) * 100, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* VRAM */}
                    {gpu.memory_used_gb !== undefined && gpu.memory_total_gb !== undefined && (
                      <div className="mt-3">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-500">VRAM</span>
                          <span className="text-hydra-magenta">
                            {gpu.memory_used_gb.toFixed(1)} / {gpu.memory_total_gb.toFixed(0)} GB ({memPct.toFixed(0)}%)
                          </span>
                        </div>
                        <div className="h-2 bg-hydra-darker rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-500 ${memPct > 90 ? 'bg-hydra-red' : memPct > 70 ? 'bg-hydra-yellow' : 'bg-hydra-magenta'}`}
                            style={{ width: `${memPct}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* No GPU fallback */}
          {(!gpuMetrics || gpuMetrics.length === 0) && gpus && gpus.length > 0 && (
            <div className="bg-hydra-dark/50 rounded-lg p-4">
              <span className="text-sm text-gray-400 uppercase tracking-wider">GPUs</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {gpus.map((gpu, i) => (
                  <span key={i} className="text-sm bg-hydra-gray/30 px-3 py-1 rounded text-hydra-cyan">
                    {gpu}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-hydra-gray/30 flex items-center justify-between text-xs text-gray-500">
          <span>Press ESC to close</span>
          <span>Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  );
}
