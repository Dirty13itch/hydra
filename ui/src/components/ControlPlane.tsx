'use client';

import { useState, useEffect, useCallback } from 'react';
import { StatusBar } from './StatusBar';
import { DomainTabs, type Domain } from './DomainTabs';
import { LettaChat } from './LettaChat';
import { NodeDetailModal } from './NodeDetailModal';
import { HelpGlossary } from './HelpGlossary';
import { ActivityFeed } from './ActivityFeed';
import { AutomationControlPanel } from './AutomationControlPanel';
import {
  OverviewView,
  InferenceView,
  StorageView,
  AutomationView,
  CreativeView,
  HomeView,
  IntelligenceView,
} from './domain-views';
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';
import { useMetricsHistory } from '@/hooks/useMetricsHistory';
import api, {
  ServiceStatus,
  ServiceDetailed,
  NodeMetrics,
  MetricsSummary,
  AuditEntry,
  GpuInfo,
  Container,
  StoragePoolsData,
  Alert,
  Activity,
  PendingApproval,
  SystemMode,
} from '@/lib/api';

interface HealthData {
  status: string;
  version: string;
  uptime_seconds: number;
}

export function ControlPlane() {
  // Data state
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
  const [activities, setActivities] = useState<Activity[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<PendingApproval[]>([]);
  const [systemMode, setSystemMode] = useState<SystemMode | null>(null);

  // UI state
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [activeDomain, setActiveDomain] = useState<Domain>('overview');
  const [helpOpen, setHelpOpen] = useState(false);
  const [activityPanelOpen, setActivityPanelOpen] = useState(false);
  const [controlPanelOpen, setControlPanelOpen] = useState(false);
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

  // Metrics history for sparklines
  const { history, addDataPoint } = useMetricsHistory();

  // Track metrics history
  useEffect(() => {
    const avgGpuTemp =
      gpus.length > 0 ? gpus.reduce((sum, g) => sum + g.temp_c, 0) / gpus.length : null;
    addDataPoint(metrics?.cpu_avg, metrics?.memory_used_pct, metrics?.disk_used_pct, avgGpuTemp);
  }, [metrics, gpus, addDataPoint]);

  // Keyboard shortcuts
  useKeyboardShortcuts([
    {
      key: '?',
      shift: true,
      action: () => setHelpOpen(true),
      description: 'Open help/glossary',
    },
    {
      key: '/',
      action: () => setHelpOpen(true),
      description: 'Open help/glossary',
    },
    {
      key: 'Escape',
      action: () => {
        setHelpOpen(false);
        setSelectedNode(null);
        setActivityPanelOpen(false);
        setControlPanelOpen(false);
      },
      description: 'Close modals',
    },
    {
      key: 'a',
      action: () => setActivityPanelOpen((prev) => !prev),
      description: 'Toggle activity panel',
    },
    {
      key: 'c',
      action: () => setControlPanelOpen((prev) => !prev),
      description: 'Toggle control panel',
    },
    {
      key: 'r',
      action: () => fetchData(false),
      description: 'Refresh data',
    },
    // Domain shortcuts
    {
      key: '1',
      action: () => setActiveDomain('overview'),
      description: 'Go to Overview',
    },
    {
      key: '2',
      action: () => setActiveDomain('inference'),
      description: 'Go to Inference',
    },
    {
      key: '3',
      action: () => setActiveDomain('storage'),
      description: 'Go to Storage',
    },
    {
      key: '4',
      action: () => setActiveDomain('automation'),
      description: 'Go to Automation',
    },
    {
      key: '5',
      action: () => setActiveDomain('creative'),
      description: 'Go to Creative',
    },
    {
      key: '6',
      action: () => setActiveDomain('intelligence'),
      description: 'Go to Intelligence',
    },
    {
      key: '7',
      action: () => setActiveDomain('home'),
      description: 'Go to Home',
    },
  ]);

  const fetchData = useCallback(async (isInitial = false) => {
    if (isInitial) setIsLoading(true);
    try {
      const [
        healthData,
        servicesData,
        servicesDetailedData,
        nodesData,
        metricsData,
        auditData,
        containersData,
        gpuData,
        storageData,
        alertsData,
        activitiesData,
        pendingData,
        modeData,
      ] = await Promise.all([
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
        api.activities({ limit: 50 }).catch(() => ({ activities: [], count: 0 })),
        api.pendingApprovals().catch(() => ({ pending: [], count: 0 })),
        api.systemMode().catch(() => null),
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
      setActivities(activitiesData.activities);
      setPendingApprovals(pendingData.pending);
      if (modeData) setSystemMode(modeData);
      setError(null);
      setLastUpdate(new Date());
    } catch (err) {
      setError('Failed to connect to Hydra MCP');
    } finally {
      if (isInitial) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(true);
    const interval = setInterval(() => fetchData(false), 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Handler for mode changes
  const handleModeChange = useCallback(async (mode: string) => {
    try {
      const newMode = await api.setSystemMode(mode);
      setSystemMode(newMode);
    } catch (err) {
      console.error('Failed to change mode:', err);
      setError('Failed to change system mode');
    }
  }, []);

  // Handler for emergency stop
  const handleEmergencyStop = useCallback(async () => {
    try {
      const result = await api.emergencyStop();
      if (result.mode) {
        setSystemMode(result.mode);
      }
      // Refresh data after emergency stop
      fetchData(false);
    } catch (err) {
      console.error('Emergency stop failed:', err);
      setError('Emergency stop failed');
    }
  }, [fetchData]);

  // Handler for approving an activity
  const handleApprove = useCallback(async (id: number) => {
    try {
      await api.approveActivity(id);
      // Refresh pending approvals
      const pendingData = await api.pendingApprovals();
      setPendingApprovals(pendingData.pending);
      // Refresh activities
      const activitiesData = await api.activities({ limit: 50 });
      setActivities(activitiesData.activities);
    } catch (err) {
      console.error('Failed to approve activity:', err);
      setError('Failed to approve activity');
    }
  }, []);

  // Handler for rejecting an activity
  const handleReject = useCallback(async (id: number) => {
    try {
      await api.rejectActivity(id);
      // Refresh pending approvals
      const pendingData = await api.pendingApprovals();
      setPendingApprovals(pendingData.pending);
      // Refresh activities
      const activitiesData = await api.activities({ limit: 50 });
      setActivities(activitiesData.activities);
    } catch (err) {
      console.error('Failed to reject activity:', err);
      setError('Failed to reject activity');
    }
  }, []);

  // Render the active domain view
  const renderDomainView = () => {
    if (isLoading) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div
              className="w-12 h-12 border-4 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--hydra-cyan)', borderTopColor: 'transparent' }}
            />
            <span style={{ color: 'var(--hydra-text-muted)' }}>Loading cluster data...</span>
          </div>
        </div>
      );
    }

    switch (activeDomain) {
      case 'overview':
        return (
          <OverviewView
            nodes={nodes}
            gpus={gpus}
            metrics={metrics}
            containers={containers}
            alerts={alerts}
            containerCount={containerCount}
            metricsHistory={history}
            onNodeClick={setSelectedNode}
          />
        );
      case 'inference':
        return <InferenceView gpus={gpus} />;
      case 'storage':
        return <StorageView storagePools={storagePools} />;
      case 'automation':
        return <AutomationView alerts={alerts} onRefresh={() => fetchData(false)} />;
      case 'creative':
        return <CreativeView />;
      case 'intelligence':
        return <IntelligenceView />;
      case 'home':
        return <HomeView />;
      default:
        return null;
    }
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ backgroundColor: 'var(--hydra-bg-dark)' }}>
      {/* Layer 0: Ambient Status Bar */}
      <StatusBar
        onModeClick={() => setControlPanelOpen(true)}
        onPendingClick={() => setControlPanelOpen(true)}
        onActivityClick={() => setActivityPanelOpen(true)}
      />

      {/* Header Bar */}
      <header
        className="flex items-center justify-between px-4 py-2 border-b"
        style={{ borderColor: 'var(--hydra-border)' }}
      >
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
            TYPHON COMMAND
          </h1>
          <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            v{health?.version || '0.0.0'}
          </span>
        </div>

        <div className="flex items-center gap-4">
          {error && (
            <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.2)', color: 'var(--hydra-red)' }}>
              {error}
            </span>
          )}
          <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Updated: {lastUpdate.toLocaleTimeString()}
          </span>
          <button
            onClick={() => fetchData(false)}
            className="text-xs px-2 py-1 rounded transition-colors hover:bg-white/10"
            style={{ color: 'var(--hydra-cyan)' }}
          >
            Refresh
          </button>
          <button
            onClick={() => setHelpOpen(true)}
            className="text-xs px-2 py-1 rounded transition-colors hover:bg-white/10"
            style={{ color: 'var(--hydra-text-muted)' }}
          >
            ? Help
          </button>
        </div>
      </header>

      {/* Layer 2: Domain Tabs */}
      <DomainTabs activeDomain={activeDomain} onDomainChange={setActiveDomain} />

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden">{renderDomainView()}</main>

      {/* Footer */}
      <footer
        className="px-4 py-2 border-t flex items-center justify-between text-xs"
        style={{ borderColor: 'var(--hydra-border)', color: 'var(--hydra-text-muted)' }}
      >
        <div className="flex items-center gap-4">
          <span>
            <span
              className="inline-block w-2 h-2 rounded-full mr-1.5"
              style={{ backgroundColor: health ? 'var(--hydra-green)' : 'var(--hydra-red)' }}
            />
            MCP {health ? 'Connected' : 'Disconnected'}
          </span>
          <span>{containerCount} containers</span>
          <span>{gpus.length} GPUs</span>
        </div>
        <div className="flex items-center gap-2">
          <span>Keyboard: 1-7 domains, A activity, C control, R refresh, ? help</span>
        </div>
      </footer>

      {/* Layer 3: Letta Chat (AI Copilot) */}
      <LettaChat />

      {/* Modals */}
      <HelpGlossary externalOpen={helpOpen} onClose={() => setHelpOpen(false)} />

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

      {/* Activity Panel Slideover */}
      {activityPanelOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setActivityPanelOpen(false)}
          />
          {/* Panel */}
          <div
            className="relative w-full max-w-lg h-full animate-in slide-in-from-right duration-300"
            style={{ backgroundColor: 'var(--hydra-bg-dark)' }}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--hydra-border)' }}>
              <h2 className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
                Activity Stream
              </h2>
              <button
                onClick={() => setActivityPanelOpen(false)}
                className="p-2 rounded hover:bg-white/10 transition-colors"
                style={{ color: 'var(--hydra-text-muted)' }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="h-[calc(100%-60px)] overflow-hidden">
              <ActivityFeed
                activities={activities}
                onRefresh={() => fetchData(false)}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            </div>
          </div>
        </div>
      )}

      {/* Control Panel Slideover */}
      {controlPanelOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setControlPanelOpen(false)}
          />
          {/* Panel */}
          <div
            className="relative w-full max-w-md h-full animate-in slide-in-from-right duration-300"
            style={{ backgroundColor: 'var(--hydra-bg-dark)' }}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--hydra-border)' }}>
              <h2 className="text-lg font-bold" style={{ color: 'var(--hydra-yellow)' }}>
                Steward Control
              </h2>
              <button
                onClick={() => setControlPanelOpen(false)}
                className="p-2 rounded hover:bg-white/10 transition-colors"
                style={{ color: 'var(--hydra-text-muted)' }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="h-[calc(100%-60px)] overflow-hidden">
              <AutomationControlPanel
                systemMode={systemMode}
                pendingApprovals={pendingApprovals}
                onModeChange={handleModeChange}
                onEmergencyStop={handleEmergencyStop}
                onApprove={handleApprove}
                onReject={handleReject}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
