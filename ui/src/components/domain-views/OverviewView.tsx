'use client';

import { DomainView } from '../DomainTabs';
import { NodeCard } from '../NodeCard';
import { GrafanaEmbed, GrafanaPanel } from '../embedded';
import { WorkflowStatusPanel } from '../embedded';
import { HomeControlWidget } from '../embedded';
import { QuickActions } from '../QuickActions';
import { Sparkline } from '../Sparkline';
import { AgentOrchestrationPanel } from '../AgentOrchestrationPanel';
import { VoiceInterfacePanel } from '../VoiceInterfacePanel';
import { SelfImprovementPanel } from '../SelfImprovementPanel';
import type { GpuInfo, NodeMetrics, MetricsSummary, Container, Alert } from '@/lib/api';

interface OverviewViewProps {
  nodes: NodeMetrics;
  gpus: GpuInfo[];
  metrics: MetricsSummary | null;
  containers: Container[];
  alerts: Alert[];
  containerCount: number;
  metricsHistory: {
    cpu: number[];
    memory: number[];
    disk: number[];
    gpuTemp: number[];
  };
  onNodeClick: (node: {
    name: string;
    role: string;
    ip: string;
    cpu?: number;
    memory?: number;
    status: 'online' | 'offline' | 'unknown';
    gpus?: string[];
    gpuMetrics?: GpuInfo[];
  }) => void;
}

const NODE_CONFIGS = [
  { key: 'hydra-ai', name: 'hydra-ai', role: 'Primary Inference', gpus: ['RTX 5090', 'RTX 4090'], ip: '192.168.1.250' },
  { key: 'hydra-compute', name: 'hydra-compute', role: 'Secondary / Creative', gpus: ['RTX 5070 Ti', 'RTX 5070 Ti'], ip: '192.168.1.203' },
  { key: 'hydra-storage', name: 'hydra-storage', role: 'Storage / Orchestration', gpus: ['Arc A380'], ip: '192.168.1.244' },
];

export function OverviewView({
  nodes,
  gpus,
  metrics,
  containers,
  alerts,
  containerCount,
  metricsHistory,
  onNodeClick,
}: OverviewViewProps) {
  const getNodeMetrics = (name: string) => {
    const entries = Object.entries(nodes);
    const match = entries.find(([instance]) => instance.includes(name) || instance.includes(name.split('-')[1]));
    return match ? match[1] : null;
  };

  const getNodeGpus = (name: string) => {
    return gpus.filter((gpu) => gpu.node === name);
  };

  const activeAlerts = alerts.filter((a) => a.status === 'firing');

  return (
    <DomainView
      title="Overview"
      icon="📊"
      description="Cluster-wide status and quick actions"
      actions={
        <div className="flex items-center gap-3">
          {activeAlerts.length > 0 && (
            <span
              className="px-2 py-1 rounded text-xs animate-pulse"
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                color: 'var(--hydra-red)',
              }}
            >
              {activeAlerts.length} Active Alert{activeAlerts.length !== 1 ? 's' : ''}
            </span>
          )}
          <a
            href="http://192.168.1.244:3003"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(234, 179, 8, 0.1)',
              color: 'var(--hydra-yellow)',
              border: '1px solid var(--hydra-yellow)',
            }}
          >
            Grafana →
          </a>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Top Stats Row */}
        <div className="grid grid-cols-6 gap-4">
          <div
            className="p-4 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-3xl font-bold" style={{ color: 'var(--hydra-cyan)' }}>
              {containerCount}
            </div>
            <div className="text-xs uppercase tracking-wider mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Containers
            </div>
          </div>
          <div
            className="p-4 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-3xl font-bold" style={{ color: 'var(--hydra-green)' }}>
              {metrics?.cpu_avg?.toFixed(1) || '--'}%
            </div>
            <div className="text-xs uppercase tracking-wider mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Avg CPU
            </div>
            <Sparkline data={metricsHistory.cpu} color="var(--hydra-green)" className="mt-2 justify-center" />
          </div>
          <div
            className="p-4 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-3xl font-bold" style={{ color: 'var(--hydra-magenta)' }}>
              {metrics?.memory_used_pct?.toFixed(1) || '--'}%
            </div>
            <div className="text-xs uppercase tracking-wider mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Avg Memory
            </div>
            <Sparkline data={metricsHistory.memory} color="var(--hydra-magenta)" className="mt-2 justify-center" />
          </div>
          <div
            className="p-4 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-3xl font-bold" style={{ color: 'var(--hydra-yellow)' }}>
              {metrics?.disk_used_pct?.toFixed(1) || '--'}%
            </div>
            <div className="text-xs uppercase tracking-wider mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Disk Used
            </div>
            <Sparkline data={metricsHistory.disk} color="var(--hydra-yellow)" className="mt-2 justify-center" />
          </div>
          <div
            className="p-4 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-3xl font-bold" style={{ color: 'var(--hydra-cyan)' }}>
              {gpus.length}
            </div>
            <div className="text-xs uppercase tracking-wider mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
              GPUs
            </div>
          </div>
          <div
            className="p-4 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div
              className="text-3xl font-bold"
              style={{
                color:
                  gpus.length > 0 && gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length >= 65
                    ? 'var(--hydra-yellow)'
                    : 'var(--hydra-green)',
              }}
            >
              {gpus.length > 0
                ? `${Math.round((gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length) * (9 / 5) + 32)}°F`
                : '--'}
            </div>
            <div className="text-xs uppercase tracking-wider mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
              Avg GPU Temp
            </div>
            <Sparkline
              data={metricsHistory.gpuTemp}
              color={
                gpus.length > 0 && gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length >= 65
                  ? 'var(--hydra-yellow)'
                  : 'var(--hydra-green)'
              }
              className="mt-2 justify-center"
            />
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-4 gap-6">
          {/* Nodes Column */}
          <div className="space-y-3">
            <div className="text-xs uppercase tracking-wider font-medium" style={{ color: 'var(--hydra-text-muted)' }}>
              Cluster Nodes
            </div>
            {NODE_CONFIGS.map((node) => {
              const nodeMetrics = getNodeMetrics(node.name);
              const nodeGpus = getNodeGpus(node.name);
              const nodeStatus = nodeMetrics ? ('online' as const) : ('unknown' as const);
              return (
                <NodeCard
                  key={node.key}
                  name={node.name}
                  role={node.role}
                  cpu={nodeMetrics?.cpu_pct}
                  memory={nodeMetrics?.memory_pct}
                  status={nodeStatus}
                  gpus={node.gpus}
                  gpuMetrics={nodeGpus}
                  ip={node.ip}
                  onClick={() =>
                    onNodeClick({
                      name: node.name,
                      role: node.role,
                      ip: node.ip,
                      cpu: nodeMetrics?.cpu_pct,
                      memory: nodeMetrics?.memory_pct,
                      status: nodeStatus,
                      gpus: node.gpus,
                      gpuMetrics: nodeGpus,
                    })
                  }
                />
              );
            })}
          </div>

          {/* Center: Grafana Dashboard */}
          <div className="col-span-2">
            <div
              className="rounded-lg border overflow-hidden h-full"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <GrafanaEmbed dashboard="cluster" height={420} showHeader={true} />
            </div>
          </div>

          {/* Right Column: Quick Panels */}
          <div className="space-y-4">
            {/* Quick Actions */}
            <QuickActions />

            {/* AI Systems Status */}
            <div
              className="rounded-lg border p-3"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-xs uppercase tracking-wider mb-2" style={{ color: 'var(--hydra-text-muted)' }}>
                AI Systems
              </div>
              <div className="space-y-2">
                <AgentOrchestrationPanel compact />
                <VoiceInterfacePanel compact />
                <SelfImprovementPanel compact />
              </div>
            </div>

            {/* Workflows Compact */}
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <WorkflowStatusPanel category="monitoring" compact={false} height={150} limit={3} showHeader={true} />
            </div>

            {/* Home Control Compact */}
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <HomeControlWidget showScenes={true} showLights={true} showClimate={false} height={140} showHeader={true} />
            </div>
          </div>
        </div>

        {/* Bottom Row: Mini Metric Panels */}
        <div className="grid grid-cols-4 gap-4">
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="cpuUsage" height={100} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="memoryUsage" height={100} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="gpuTemp" height={100} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <GrafanaPanel panel="vramUsage" height={100} />
          </div>
        </div>
      </div>
    </DomainView>
  );
}
