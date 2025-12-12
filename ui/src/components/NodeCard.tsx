'use client';

import { StatusIndicator } from './StatusIndicator';
import { GpuInfo } from '@/lib/api';

interface NodeCardProps {
  name: string;
  role: string;
  cpu?: number;
  memory?: number;
  status: 'online' | 'offline' | 'unknown';
  gpus?: string[];
  gpuMetrics?: GpuInfo[];
  ip?: string;
  onClick?: () => void;
}

export function NodeCard({ name, role, cpu, memory, status, gpus, gpuMetrics, ip, onClick }: NodeCardProps) {
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

  const getMemColor = (pct: number) => {
    if (pct >= 90) return 'bg-hydra-red';
    if (pct >= 70) return 'bg-hydra-yellow';
    return 'bg-hydra-magenta';
  };

  return (
    <div
      className={`panel p-4 hover:border-hydra-cyan/60 transition-colors ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-hydra-cyan font-bold text-lg">{name}</h3>
          <p className="text-gray-500 text-xs uppercase tracking-wider">{role}</p>
        </div>
        <StatusIndicator status={status} />
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-400">CPU</span>
          <span className={cpu && cpu > 80 ? 'text-hydra-red' : 'text-hydra-green'}>
            {cpu !== undefined ? `${cpu.toFixed(1)}%` : '--'}
          </span>
        </div>
        <div className="h-1 bg-hydra-dark rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${cpu && cpu > 80 ? 'bg-hydra-red' : 'bg-hydra-cyan'}`}
            style={{ width: `${cpu || 0}%` }}
          />
        </div>

        <div className="flex justify-between text-sm mt-2">
          <span className="text-gray-400">Memory</span>
          <span className={memory && memory > 80 ? 'text-hydra-red' : 'text-hydra-green'}>
            {memory !== undefined ? `${memory.toFixed(1)}%` : '--'}
          </span>
        </div>
        <div className="h-1 bg-hydra-dark rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${memory && memory > 80 ? 'bg-hydra-red' : 'bg-hydra-magenta'}`}
            style={{ width: `${memory || 0}%` }}
          />
        </div>

        {gpuMetrics && gpuMetrics.length > 0 ? (
          <div className="mt-3 pt-2 border-t border-hydra-gray space-y-2">
            <span className="text-gray-500 text-xs uppercase tracking-wider">GPUS</span>
            {gpuMetrics.map((gpu, i) => {
              const memPct = gpu.memory_used_gb !== undefined && gpu.memory_total_gb
                ? (gpu.memory_used_gb / gpu.memory_total_gb) * 100
                : 0;
              return (
                <div key={i} className="bg-hydra-dark/50 rounded p-2">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-xs text-hydra-cyan font-medium">{gpu.name}</span>
                    <span className={`text-xs ${getTempColor(gpu.temp_c)}`}>{toFahrenheit(gpu.temp_c)}°F</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500">Util</span>
                      <span className={`ml-1 ${getUtilColor(gpu.utilization)}`}>{gpu.utilization}%</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Pwr</span>
                      <span className="ml-1 text-hydra-yellow">{gpu.power_w.toFixed(0)}W</span>
                    </div>
                  </div>
                  {gpu.memory_used_gb !== undefined && gpu.memory_total_gb !== undefined && (
                    <div className="mt-1">
                      <div className="flex justify-between items-center text-xs mb-0.5">
                        <span className="text-gray-500">VRAM</span>
                        <span className="text-hydra-magenta">
                          {gpu.memory_used_gb.toFixed(1)}/{gpu.memory_total_gb.toFixed(0)}G ({memPct.toFixed(0)}%)
                        </span>
                      </div>
                      <div className="h-1 bg-hydra-dark rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${getMemColor(memPct)}`}
                          style={{ width: `${memPct}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : gpus && gpus.length > 0 ? (
          <div className="mt-3 pt-2 border-t border-hydra-gray">
            <span className="text-gray-500 text-xs">GPUs:</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {gpus.map((gpu, i) => (
                <span key={i} className="text-xs bg-hydra-gray-light px-2 py-0.5 rounded text-hydra-cyan">
                  {gpu}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
