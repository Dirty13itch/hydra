'use client';

import { DomainView } from '../DomainTabs';
import { GrafanaEmbed, GrafanaPanel } from '../embedded';
import { AIModelsPanel } from '../AIModelsPanel';
import { GPUMetricsPanel } from '../GPUMetricsPanel';
import type { GpuInfo } from '@/lib/api';

interface InferenceViewProps {
  gpus: GpuInfo[];
}

export function InferenceView({ gpus }: InferenceViewProps) {
  return (
    <DomainView
      title="Inference"
      icon="🧠"
      description="Models, VRAM allocation, and performance metrics"
      actions={
        <div className="flex items-center gap-2">
          <a
            href="http://192.168.1.250:5000"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(6, 182, 212, 0.1)',
              color: 'var(--hydra-cyan)',
              border: '1px solid var(--hydra-cyan)',
            }}
          >
            TabbyAPI →
          </a>
          <a
            href="http://192.168.1.250:3000"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(139, 92, 246, 0.1)',
              color: 'var(--hydra-purple)',
              border: '1px solid var(--hydra-purple)',
            }}
          >
            Open WebUI →
          </a>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Quick Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Active Model
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
              Llama-3.3-70B
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              4.65 bpw EXL2
            </div>
          </div>
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              VRAM Used
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-magenta)' }}>
              {gpus.reduce((sum, g) => sum + g.memory_used_gb, 0).toFixed(1)} GB
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              of {gpus.reduce((sum, g) => sum + g.memory_total_gb, 0).toFixed(0)} GB total
            </div>
          </div>
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Avg Temp
            </div>
            <div
              className="text-lg font-bold"
              style={{
                color: gpus.length > 0 && gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length > 70
                  ? 'var(--hydra-yellow)'
                  : 'var(--hydra-green)',
              }}
            >
              {gpus.length > 0
                ? `${Math.round((gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length) * 9 / 5 + 32)}°F`
                : '--'}
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              {gpus.length} GPUs online
            </div>
          </div>
          <div
            className="p-4 rounded-lg border"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Power Draw
            </div>
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-yellow)' }}>
              {gpus.reduce((sum, g) => sum + g.power_draw_w, 0).toFixed(0)} W
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              of {gpus.reduce((sum, g) => sum + g.power_limit_w, 0).toFixed(0)} W limit
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left Column: GPU Details */}
          <div className="col-span-1 space-y-4">
            <GPUMetricsPanel gpus={gpus} />
            <AIModelsPanel gpus={gpus} />
          </div>

          {/* Right Column: Grafana Metrics */}
          <div className="col-span-2">
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <GrafanaEmbed
                dashboard="gpu"
                height={500}
                showHeader={true}
              />
            </div>
          </div>
        </div>

        {/* Embedded Metric Panels */}
        <div className="grid grid-cols-4 gap-4">
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="gpuTemp" height={120} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="vramUsage" height={120} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="inferenceLatency" height={120} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="tokensPerSec" height={120} />
          </div>
        </div>
      </div>
    </DomainView>
  );
}
