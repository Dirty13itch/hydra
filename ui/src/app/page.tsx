'use client';

import { useEffect, useState, useCallback } from 'react';
import { Header } from '@/components/Header';
import { NodeCard } from '@/components/NodeCard';
import { NodeDetailModal } from '@/components/NodeDetailModal';
import { ServiceList } from '@/components/ServiceList';
import { ContainerList } from '@/components/ContainerList';
import { AuditLog } from '@/components/AuditLog';
import { StatusIndicator } from '@/components/StatusIndicator';
import { LettaChat } from '@/components/LettaChat';
import { StoragePools } from '@/components/StoragePools';
import { HelpGlossary } from '@/components/HelpGlossary';
import { AlertsPanel } from '@/components/AlertsPanel';
import { AIModelsPanel } from '@/components/AIModelsPanel';
import { QuickActions } from '@/components/QuickActions';
import { ServiceDependencyGraph } from '@/components/ServiceDependencyGraph';
import { GPUMetricsPanel } from '@/components/GPUMetricsPanel';
import { StatsSkeleton, NodeCardSkeleton, ServiceListSkeleton, ContainerListSkeleton, AuditLogSkeleton, AIModelsPanelSkeleton, QuickActionsSkeleton } from '@/components/Skeleton';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { usePanelCollapse } from '@/hooks/useLocalStorage';
import { usePullToRefresh } from '@/hooks/usePullToRefresh';
import { useMetricsHistory } from '@/hooks/useMetricsHistory';
import { PullToRefreshIndicator } from '@/components/PullToRefreshIndicator';
import { Sparkline } from '@/components/Sparkline';
import api, { ServiceStatus, ServiceDetailed, NodeMetrics, MetricsSummary, AuditEntry, GpuInfo, Container, StoragePoolsData, Alert } from '@/lib/api';

interface HealthData {
  status: string;
  version: string;
  uptime_seconds: number;
}

export default function Home() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [services, setServices] = useState<ServiceStatus>({});
  const [servicesDetailed, setServicesDetailed] = useState<ServiceDetailed>({});
  const [nodes, setNodes] = useState<NodeMetrics>({});
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [containerCount, setContainerCount] = useState<number>(0);
  const [containers, setContainers] = useState<Container[]>([]);
  const [gpus, setGpus] = useState<GpuInfo[]>([]);
  const [storagePools, setStoragePools] = useState<StoragePoolsData | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [helpOpen, setHelpOpen] = useState(false);
  const [selectedNode, setSelectedNode] = useState<{
    name: string;
    role: string;
    ip: string;
    cpu?: number;
    memory?: number;
    status: 'online' | 'offline' | 'unknown';
    gpus?: string[];
    gpuMetrics?: GpuInfo[];
  } | null>(null);
  const { collapsed, togglePanel } = usePanelCollapse();
  const { history, addDataPoint } = useMetricsHistory();

  // Track metrics history for sparklines
  useEffect(() => {
    const avgGpuTemp = gpus.length > 0
      ? gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length
      : null;
    addDataPoint(
      metrics?.cpu_avg,
      metrics?.memory_used_pct,
      metrics?.disk_used_pct,
      avgGpuTemp
    );
  }, [metrics, gpus, addDataPoint]);

  // Pull-to-refresh for mobile
  const PULL_THRESHOLD = 80;
  const { pullDistance, isRefreshing } = usePullToRefresh({
    onRefresh: () => fetchData(false),
    threshold: PULL_THRESHOLD,
  });

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: '?',
      shift: true,
      action: () => setHelpOpen(true),
      description: 'Open help/glossary'
    },
    {
      key: '/',
      action: () => setHelpOpen(true),
      description: 'Open help/glossary'
    },
    {
      key: 'Escape',
      action: () => setHelpOpen(false),
      description: 'Close modals'
    },
    {
      key: 'r',
      action: () => fetchData(false),
      description: 'Refresh data'
    },
  ]);

  const fetchData = async (isInitial = false) => {
    if (isInitial) setIsLoading(true);
    try {
      const [healthData, servicesData, servicesDetailedData, nodesData, metricsData, auditData, containersData, gpuData, storageData, alertsData] = await Promise.all([
        api.health().catch(() => null),
        api.servicesStatus().catch(() => ({})),
        api.servicesDetailed().catch(() => ({})),
        api.metricsNodes().catch(() => ({})),
        api.metricsSummary().catch(() => null),
        api.auditLog(20).catch(() => ({ entries: [], total: 0 })),
        api.containers().catch(() => ({ containers: [], count: 0 })),
        api.gpuStatus().catch(() => ({ gpus: [] })),
        api.storagePools().catch(() => null),
        api.alerts().catch(() => []),
      ]);

      if (healthData) setHealth(healthData);
      setServices(servicesData);
      setServicesDetailed(servicesDetailedData);
      setNodes(nodesData);
      if (metricsData) setMetrics(metricsData);
      setAuditLog(auditData.entries);
      setContainerCount(containersData.count);
      setContainers(containersData.containers);
      setGpus(gpuData.gpus);
      if (storageData) setStoragePools(storageData);
      setAlerts(alertsData);
      setError(null);
      setLastUpdate(new Date());
    } catch (err) {
      setError('Failed to connect to Hydra MCP');
    } finally {
      if (isInitial) setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData(true);
    const interval = setInterval(() => fetchData(false), 5000);
    return () => clearInterval(interval);
  }, []);

  const nodeConfigs = [
    { key: 'hydra-ai', name: 'hydra-ai', role: 'Primary Inference', gpus: ['RTX 5090', 'RTX 4090'], ip: '192.168.1.250' },
    { key: 'hydra-compute', name: 'hydra-compute', role: 'Secondary / Creative', gpus: ['RTX 5070 Ti', 'RTX 3060'], ip: '192.168.1.251' },
    { key: 'hydra-storage', name: 'hydra-storage', role: 'Storage / Orchestration', gpus: ['Arc A380'], ip: '192.168.1.244' },
  ];

  const getNodeMetrics = (name: string) => {
    const entries = Object.entries(nodes);
    const match = entries.find(([instance]) => instance.includes(name) || instance.includes(name.split('-')[1]));
    return match ? match[1] : null;
  };

  const getNodeGpus = (name: string) => {
    return gpus.filter(gpu => gpu.node === name);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Pull-to-refresh indicator for mobile */}
      <PullToRefreshIndicator
        pullDistance={pullDistance}
        isRefreshing={isRefreshing}
        threshold={PULL_THRESHOLD}
      />

      <Header version={health?.version} uptime={health?.uptime_seconds} refreshInterval={5000} lastUpdate={lastUpdate} />

      <main className="flex-1 container mx-auto px-4 py-6">
        {error && (
          <div className="mb-4 p-4 bg-hydra-red/20 border border-hydra-red rounded-lg text-hydra-red">
            {error}
          </div>
        )}

        {/* Stats Row */}
        {isLoading ? (
          <StatsSkeleton />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4 mb-6">
            <div className="panel p-4 text-center">
              <div className="text-3xl font-bold text-hydra-cyan">{containerCount}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Containers</div>
            </div>
            <div className="panel p-4 text-center">
              <div className="text-3xl font-bold text-hydra-green">
                {metrics?.cpu_avg?.toFixed(1) || '--'}%
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Avg CPU</div>
              <Sparkline data={history.cpu} color="var(--hydra-green)" className="mt-2 justify-center" />
            </div>
            <div className="panel p-4 text-center">
              <div className="text-3xl font-bold text-hydra-magenta">
                {metrics?.memory_used_pct?.toFixed(1) || '--'}%
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Avg Memory</div>
              <Sparkline data={history.memory} color="var(--hydra-magenta)" className="mt-2 justify-center" />
            </div>
            <div className="panel p-4 text-center">
              <div className="text-3xl font-bold text-hydra-yellow">
                {metrics?.disk_used_pct?.toFixed(1) || '--'}%
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Disk Used</div>
              <Sparkline data={history.disk} color="var(--hydra-yellow)" className="mt-2 justify-center" />
            </div>
            <div className="panel p-4 text-center">
              <div className="text-3xl font-bold text-hydra-cyan">{gpus.length}</div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">GPUs</div>
            </div>
            <div className="panel p-4 text-center">
              <div className={`text-3xl font-bold ${gpus.length > 0 && (gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length) >= 65 ? 'text-hydra-yellow' : 'text-hydra-green'}`}>
                {gpus.length > 0 ? `${Math.round((gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length) * 9/5 + 32)}°F` : '--'}
              </div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mt-1">Avg GPU Temp</div>
              <Sparkline data={history.gpuTemp} color={gpus.length > 0 && (gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length) >= 65 ? 'var(--hydra-yellow)' : 'var(--hydra-green)'} className="mt-2 justify-center" />
            </div>
          </div>
        )}

        {/* Main Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 md:gap-6">
          {/* Nodes Column */}
          <div className="space-y-4">
            <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="text-hydra-cyan">&#9632;</span> Cluster Nodes
            </h2>
            {isLoading ? (
              <>
                <NodeCardSkeleton />
                <NodeCardSkeleton />
                <NodeCardSkeleton />
              </>
            ) : (
              <>
                {nodeConfigs.map((node) => {
                  const nodeMetrics = getNodeMetrics(node.name);
                  const nodeGpus = getNodeGpus(node.name);
                  const nodeStatus = nodeMetrics ? 'online' : 'unknown' as const;
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
                      onClick={() => setSelectedNode({
                        name: node.name,
                        role: node.role,
                        ip: node.ip,
                        cpu: nodeMetrics?.cpu_pct,
                        memory: nodeMetrics?.memory_pct,
                        status: nodeStatus,
                        gpus: node.gpus,
                        gpuMetrics: nodeGpus,
                      })}
                    />
                  );
                })}
                <StoragePools data={storagePools} isCollapsed={collapsed.storage} onToggle={() => togglePanel('storage')} />
                <AlertsPanel alerts={alerts} onRefresh={() => fetchData(false)} />
              </>
            )}
          </div>

          {/* Services Column */}
          <div className="space-y-4">
            {isLoading ? (
              <>
                <ServiceListSkeleton />
                <AIModelsPanelSkeleton />
                <QuickActionsSkeleton />
              </>
            ) : (
              <>
                <div>
                  <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <span className="text-hydra-magenta">&#9632;</span> Core Services
                  </h2>
                  <ServiceList services={services} detailed={servicesDetailed} />
                </div>
                <AIModelsPanel gpus={gpus} />
                <GPUMetricsPanel gpus={gpus} />
                <ServiceDependencyGraph services={services} />
                <QuickActions />
              </>
            )}
          </div>

          {/* Containers Column */}
          <div className="min-h-[300px] md:min-h-[400px] xl:h-[500px]">
            <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="text-hydra-green">&#9632;</span> Containers
            </h2>
            {isLoading ? <ContainerListSkeleton /> : <ContainerList containers={containers} onRefresh={fetchData} />}
          </div>

          {/* Audit Log Column */}
          <div className="min-h-[300px] md:min-h-[400px] xl:h-[500px]">
            <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="text-hydra-yellow">&#9632;</span> Activity
            </h2>
            {isLoading ? <AuditLogSkeleton /> : <AuditLog entries={auditLog} />}
          </div>
        </div>

        {/* Footer Status */}
        <div className="mt-8 pt-4 border-t border-hydra-gray/30 flex items-center justify-between text-xs text-gray-600">
          <div className="flex items-center gap-4">
            <StatusIndicator status={health ? 'online' : 'offline'} label="MCP" pulse={false} />
            <span>Last update: {new Date().toLocaleTimeString()}</span>
          </div>
          <div>
            Phase 10: Control Plane Refinement (85%)
          </div>
        </div>
      </main>

      {/* Letta Chat Widget */}
      <LettaChat />

      {/* Help/Glossary Modal */}
      <HelpGlossary externalOpen={helpOpen} onClose={() => setHelpOpen(false)} />

      {/* Node Detail Modal */}
      {selectedNode && (
        <NodeDetailModal
          name={selectedNode.name}
          role={selectedNode.role}
          cpu={selectedNode.cpu}
          memory={selectedNode.memory}
          status={selectedNode.status}
          gpus={selectedNode.gpus}
          gpuMetrics={selectedNode.gpuMetrics}
          ip={selectedNode.ip}
          onClose={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}
