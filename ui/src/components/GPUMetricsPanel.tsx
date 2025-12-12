'use client';

import { useEffect, useState } from 'react';
import { GpuInfo } from '@/lib/api';
import { Sparkline } from './Sparkline';
import { useGpuMetricsHistory } from '@/hooks/useGpuMetricsHistory';

interface GPUMetricsPanelProps {
  gpus: GpuInfo[];
}

function formatTemp(celsius: number, toFahrenheit = true): string {
  if (toFahrenheit) {
    return `${Math.round(celsius * 9/5 + 32)}°F`;
  }
  return `${Math.round(celsius)}°C`;
}

function getUtilizationColor(pct: number): string {
  if (pct >= 90) return 'var(--hydra-red)';
  if (pct >= 70) return 'var(--hydra-yellow)';
  return 'var(--hydra-green)';
}

function getTempColor(celsius: number): string {
  if (celsius >= 80) return 'var(--hydra-red)';
  if (celsius >= 70) return 'var(--hydra-yellow)';
  return 'var(--hydra-green)';
}

function getMemoryColor(pct: number): string {
  if (pct >= 95) return 'var(--hydra-red)';
  if (pct >= 80) return 'var(--hydra-yellow)';
  return 'var(--hydra-cyan)';
}

export function GPUMetricsPanel({ gpus }: GPUMetricsPanelProps) {
  const [expandedGpu, setExpandedGpu] = useState<string | null>(null);
  const { history, updateHistory, getGpuHistory } = useGpuMetricsHistory();

  // Update history when gpus change
  useEffect(() => {
    if (gpus.length > 0) {
      updateHistory(gpus);
    }
  }, [gpus, updateHistory]);

  // Group GPUs by node
  const gpusByNode = gpus.reduce((acc, gpu) => {
    if (!acc[gpu.node]) acc[gpu.node] = [];
    acc[gpu.node].push(gpu);
    return acc;
  }, {} as Record<string, GpuInfo[]>);

  if (gpus.length === 0) {
    return (
      <div className="panel p-4" style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}>
        <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
          GPU Metrics
        </h3>
        <p className="text-sm" style={{ color: 'var(--hydra-text-muted)' }}>No GPUs detected</p>
      </div>
    );
  }

  return (
    <div className="panel p-4" style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}>
      <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
        GPU Metrics
      </h3>

      <div className="space-y-4">
        {Object.entries(gpusByNode).map(([node, nodeGpus]) => (
          <div key={node}>
            <div className="text-xs uppercase tracking-wider mb-2 flex items-center gap-2" style={{ color: 'var(--hydra-text-muted)' }}>
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: 'var(--hydra-cyan)' }} />
              {node}
            </div>

            <div className="space-y-2">
              {nodeGpus.map((gpu) => {
                const gpuKey = `${gpu.node}-${gpu.index}`;
                const isExpanded = expandedGpu === gpuKey;
                const gpuHistory = getGpuHistory(gpu.node, gpu.index);
                const memoryPct = gpu.memory_total_gb && gpu.memory_total_gb > 0
                  ? (gpu.memory_used_gb || 0) / gpu.memory_total_gb * 100
                  : 0;

                return (
                  <div
                    key={gpuKey}
                    className="rounded border cursor-pointer transition-all hover:border-opacity-70"
                    style={{
                      backgroundColor: 'var(--hydra-bg)',
                      borderColor: isExpanded ? 'var(--hydra-cyan)' : 'var(--hydra-border)'
                    }}
                    onClick={() => setExpandedGpu(isExpanded ? null : gpuKey)}
                  >
                    {/* Collapsed View */}
                    <div className="p-3">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                            {gpu.name}
                          </span>
                          <span className="text-xs px-1.5 py-0.5 rounded" style={{ backgroundColor: 'rgba(0, 212, 255, 0.1)', color: 'var(--hydra-cyan)' }}>
                            GPU {gpu.index}
                          </span>
                        </div>
                        <svg
                          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                          style={{ color: 'var(--hydra-text-muted)' }}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>

                      {/* Quick Stats Row */}
                      <div className="grid grid-cols-4 gap-2">
                        <div className="text-center">
                          <div className="text-xs" style={{ color: getUtilizationColor(gpu.utilization) }}>
                            {gpu.utilization}%
                          </div>
                          <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>Util</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs" style={{ color: getMemoryColor(memoryPct) }}>
                            {memoryPct.toFixed(0)}%
                          </div>
                          <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>VRAM</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs" style={{ color: getTempColor(gpu.temp_c) }}>
                            {formatTemp(gpu.temp_c)}
                          </div>
                          <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>Temp</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs" style={{ color: 'var(--hydra-text-secondary)' }}>
                            {gpu.power_w}W
                          </div>
                          <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>Power</div>
                        </div>
                      </div>
                    </div>

                    {/* Expanded View */}
                    {isExpanded && gpuHistory && (
                      <div className="px-3 pb-3 pt-2 border-t" style={{ borderColor: 'var(--hydra-border)' }}>
                        <div className="grid grid-cols-2 gap-4">
                          {/* Utilization Chart */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] uppercase" style={{ color: 'var(--hydra-text-muted)' }}>
                                Utilization
                              </span>
                              <span className="text-xs font-medium" style={{ color: getUtilizationColor(gpu.utilization) }}>
                                {gpu.utilization}%
                              </span>
                            </div>
                            <Sparkline
                              data={gpuHistory.utilization}
                              width={120}
                              height={32}
                              color={getUtilizationColor(gpu.utilization)}
                              fillColor={getUtilizationColor(gpu.utilization)}
                              showDots={false}
                            />
                          </div>

                          {/* VRAM Chart */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] uppercase" style={{ color: 'var(--hydra-text-muted)' }}>
                                VRAM
                              </span>
                              <span className="text-xs font-medium" style={{ color: getMemoryColor(memoryPct) }}>
                                {(gpu.memory_used_gb || 0).toFixed(1)}/{(gpu.memory_total_gb || 0).toFixed(0)}GB
                              </span>
                            </div>
                            <Sparkline
                              data={gpuHistory.memoryUsedPct}
                              width={120}
                              height={32}
                              color={getMemoryColor(memoryPct)}
                              fillColor={getMemoryColor(memoryPct)}
                              showDots={false}
                            />
                          </div>

                          {/* Temperature Chart */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] uppercase" style={{ color: 'var(--hydra-text-muted)' }}>
                                Temperature
                              </span>
                              <span className="text-xs font-medium" style={{ color: getTempColor(gpu.temp_c) }}>
                                {formatTemp(gpu.temp_c)}
                              </span>
                            </div>
                            <Sparkline
                              data={gpuHistory.temperature}
                              width={120}
                              height={32}
                              color={getTempColor(gpu.temp_c)}
                              fillColor={getTempColor(gpu.temp_c)}
                              showDots={false}
                            />
                          </div>

                          {/* Power Chart */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] uppercase" style={{ color: 'var(--hydra-text-muted)' }}>
                                Power Draw
                              </span>
                              <span className="text-xs font-medium" style={{ color: 'var(--hydra-magenta)' }}>
                                {gpu.power_w}W
                              </span>
                            </div>
                            <Sparkline
                              data={gpuHistory.powerDraw}
                              width={120}
                              height={32}
                              color="var(--hydra-magenta)"
                              fillColor="var(--hydra-magenta)"
                              showDots={false}
                            />
                          </div>
                        </div>

                        {/* Memory Bar */}
                        <div className="mt-3">
                          <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--hydra-bg-secondary)' }}>
                            <div
                              className="h-full transition-all duration-300"
                              style={{
                                width: `${memoryPct}%`,
                                backgroundColor: getMemoryColor(memoryPct)
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Summary Footer */}
      <div className="mt-4 pt-3 border-t" style={{ borderColor: 'var(--hydra-border)' }}>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-sm font-medium" style={{ color: 'var(--hydra-green)' }}>
              {Math.round(gpus.reduce((sum, g) => sum + g.utilization, 0) / gpus.length)}%
            </div>
            <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>Avg Util</div>
          </div>
          <div>
            <div className="text-sm font-medium" style={{ color: 'var(--hydra-cyan)' }}>
              {gpus.reduce((sum, g) => sum + (g.memory_used_gb || 0), 0).toFixed(1)}GB
            </div>
            <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>Total VRAM Used</div>
          </div>
          <div>
            <div className="text-sm font-medium" style={{ color: getTempColor(gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length) }}>
              {formatTemp(gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length)}
            </div>
            <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>Avg Temp</div>
          </div>
        </div>
      </div>
    </div>
  );
}
