'use client';

import { useState, useEffect, useCallback } from 'react';
import { NodeCard } from './NodeCard';
import { ActivityFeed } from './ActivityFeed';
import { AutomationControlPanel } from './AutomationControlPanel';
import { AlertsPanel } from './AlertsPanel';
import { GPUMetricsPanel } from './GPUMetricsPanel';
import { StoragePools } from './StoragePools';
import { Sparkline } from './Sparkline';
import api, {
  Activity,
  SystemMode,
  PendingApproval,
  GpuInfo,
  NodeMetrics,
  MetricsSummary,
  StoragePoolsData,
  Alert
} from '@/lib/api';

interface CommandOverviewProps {
  nodes: NodeMetrics;
  metrics: MetricsSummary | null;
  gpus: GpuInfo[];
  storagePools: StoragePoolsData | null;
  alerts: Alert[];
  containerCount: number;
  onNodeClick?: (node: any) => void;
  onRefresh?: () => void;
  metricsHistory?: {
    cpu: number[];
    memory: number[];
    disk: number[];
    gpuTemp: number[];
  };
}

const NODE_CONFIGS = [
  { key: 'hydra-ai', name: 'hydra-ai', role: 'Primary Inference', gpus: ['RTX 5090', 'RTX 4090'], ip: '192.168.1.250' },
  { key: 'hydra-compute', name: 'hydra-compute', role: 'Secondary / Creative', gpus: ['RTX 5070 Ti', 'RTX 3060'], ip: '192.168.1.203' },
  { key: 'hydra-storage', name: 'hydra-storage', role: 'Storage / Orchestration', gpus: ['Arc A380'], ip: '192.168.1.244' },
];

export function CommandOverview({
  nodes,
  metrics,
  gpus,
  storagePools,
  alerts,
  containerCount,
  onNodeClick,
  onRefresh,
  metricsHistory,
}: CommandOverviewProps) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [systemMode, setSystemMode] = useState<SystemMode | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [activityError, setActivityError] = useState(false);

  // Fetch activity and control data
  const fetchActivityData = useCallback(async () => {
    try {
      const [activityData, modeData, pendingData] = await Promise.all([
        api.activities({ limit: 50 }).catch(() => ({ activities: [], count: 0 })),
        api.systemMode().catch(() => null),
        api.pendingApprovals().catch(() => ({ pending: [], count: 0 })),
      ]);

      setActivities(activityData.activities);
      if (modeData) setSystemMode(modeData);
      setPendingApprovals(pendingData.pending);
      setActivityError(false);
    } catch {
      setActivityError(true);
    }
  }, []);

  useEffect(() => {
    fetchActivityData();
    const interval = setInterval(fetchActivityData, 10000);
    return () => clearInterval(interval);
  }, [fetchActivityData]);

  // Handlers
  const handleModeChange = async (mode: string) => {
    try {
      const result = await api.setSystemMode(mode);
      setSystemMode(result);
    } catch (err) {
      console.error('Failed to change mode:', err);
    }
  };

  const handleEmergencyStop = async () => {
    try {
      await api.emergencyStop();
      fetchActivityData();
    } catch (err) {
      console.error('Emergency stop failed:', err);
    }
  };

  const handleApprove = async (id: number) => {
    try {
      await api.approveActivity(id);
      fetchActivityData();
    } catch (err) {
      console.error('Approval failed:', err);
    }
  };

  const handleReject = async (id: number) => {
    try {
      await api.rejectActivity(id);
      fetchActivityData();
    } catch (err) {
      console.error('Rejection failed:', err);
    }
  };

  // Node helpers
  const getNodeMetrics = (name: string) => {
    const entries = Object.entries(nodes);
    const match = entries.find(([instance]) => instance.includes(name) || instance.includes(name.split('-')[1]));
    return match ? match[1] : null;
  };

  const getNodeGpus = (name: string) => {
    return gpus.filter(gpu => gpu.node === name);
  };

  // Calculate totals
  const avgGpuTemp = gpus.length > 0
    ? gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length
    : null;
  const firingAlerts = alerts.filter(a => a.status === 'firing').length;

  return (
    <div className="h-full flex flex-col">
      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4 px-1">
        <div className="panel p-3 text-center">
          <div className="text-2xl font-bold text-hydra-cyan">{containerCount}</div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">Containers</div>
        </div>
        <div className="panel p-3 text-center">
          <div className="text-2xl font-bold text-hydra-green">
            {metrics?.cpu_avg?.toFixed(1) || '--'}%
          </div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">CPU</div>
          {metricsHistory && <Sparkline data={metricsHistory.cpu} color="var(--hydra-green)" className="mt-1 justify-center" />}
        </div>
        <div className="panel p-3 text-center">
          <div className="text-2xl font-bold text-hydra-magenta">
            {metrics?.memory_used_pct?.toFixed(1) || '--'}%
          </div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">Memory</div>
          {metricsHistory && <Sparkline data={metricsHistory.memory} color="var(--hydra-magenta)" className="mt-1 justify-center" />}
        </div>
        <div className="panel p-3 text-center">
          <div className="text-2xl font-bold text-hydra-yellow">
            {metrics?.disk_used_pct?.toFixed(1) || '--'}%
          </div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">Storage</div>
          {metricsHistory && <Sparkline data={metricsHistory.disk} color="var(--hydra-yellow)" className="mt-1 justify-center" />}
        </div>
        <div className="panel p-3 text-center">
          <div className={`text-2xl font-bold ${avgGpuTemp && avgGpuTemp >= 65 ? 'text-hydra-yellow' : 'text-hydra-green'}`}>
            {avgGpuTemp ? `${Math.round(avgGpuTemp * 9/5 + 32)}°F` : '--'}
          </div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">GPU Temp</div>
          {metricsHistory && <Sparkline data={metricsHistory.gpuTemp} color={avgGpuTemp && avgGpuTemp >= 65 ? 'var(--hydra-yellow)' : 'var(--hydra-green)'} className="mt-1 justify-center" />}
        </div>
        <div className="panel p-3 text-center">
          <div className={`text-2xl font-bold ${firingAlerts > 0 ? 'text-hydra-red' : 'text-hydra-green'}`}>
            {firingAlerts}
          </div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">Alerts</div>
        </div>
      </div>

      {/* Main 3-Column Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0 px-1">
        {/* Left Column: Nodes + Storage + Alerts (4/12) */}
        <div className="lg:col-span-4 flex flex-col gap-4 min-h-0 overflow-auto">
          <div className="flex-shrink-0">
            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
              <span className="text-hydra-cyan">●</span> Cluster Nodes
            </h3>
            <div className="space-y-3">
              {NODE_CONFIGS.map((node) => {
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
                    onClick={() => onNodeClick?.({
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
            </div>
          </div>

          {/* Storage Summary */}
          <div className="flex-shrink-0">
            <StoragePools data={storagePools} isCollapsed={false} onToggle={() => {}} />
          </div>

          {/* Alerts */}
          {alerts.length > 0 && (
            <div className="flex-shrink-0">
              <AlertsPanel alerts={alerts} onRefresh={onRefresh} />
            </div>
          )}
        </div>

        {/* Center Column: Activity Feed (5/12) */}
        <div className="lg:col-span-5 flex flex-col min-h-0">
          <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2 flex-shrink-0">
            <span className="text-hydra-magenta">●</span> Activity Stream
          </h3>
          <div className="flex-1 min-h-0">
            {activityError ? (
              <div className="panel p-4 text-center">
                <span className="text-hydra-yellow">Activity API unavailable</span>
                <p className="text-xs text-gray-500 mt-1">Showing legacy audit log instead</p>
              </div>
            ) : (
              <ActivityFeed
                activities={activities}
                onRefresh={fetchActivityData}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            )}
          </div>
        </div>

        {/* Right Column: Control + GPU (3/12) */}
        <div className="lg:col-span-3 flex flex-col gap-4 min-h-0">
          {/* Automation Control */}
          <div className="flex-shrink-0">
            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
              <span className="text-hydra-green">●</span> Steward Control
            </h3>
            <AutomationControlPanel
              systemMode={systemMode}
              pendingApprovals={pendingApprovals}
              onModeChange={handleModeChange}
              onEmergencyStop={handleEmergencyStop}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          </div>

          {/* GPU Metrics */}
          {gpus.length > 0 && (
            <div className="flex-shrink-0">
              <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                <span className="text-hydra-yellow">●</span> GPU Status
              </h3>
              <GPUMetricsPanel gpus={gpus} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
