'use client';

import { useState, useMemo } from 'react';

const GRAFANA_URL = 'http://192.168.1.244:3003';

// Dashboard mappings - these should match your actual Grafana dashboard UIDs
const DASHBOARDS = {
  cluster: { uid: 'cluster-overview', name: 'Cluster Overview' },
  gpu: { uid: 'gpu-metrics', name: 'GPU Utilization' },
  inference: { uid: 'inference-metrics', name: 'Inference Performance' },
  containers: { uid: 'container-metrics', name: 'Container Metrics' },
  storage: { uid: 'storage-metrics', name: 'Storage Analytics' },
  nodes: { uid: 'node-metrics', name: 'Node Deep Dive' },
};

// Individual panel IDs for embedding specific visualizations
const PANELS = {
  gpuTemp: { dashboard: 'gpu', panelId: 2, name: 'GPU Temperature' },
  gpuPower: { dashboard: 'gpu', panelId: 4, name: 'GPU Power Draw' },
  vramUsage: { dashboard: 'gpu', panelId: 6, name: 'VRAM Usage' },
  cpuUsage: { dashboard: 'cluster', panelId: 1, name: 'CPU Usage' },
  memoryUsage: { dashboard: 'cluster', panelId: 2, name: 'Memory Usage' },
  inferenceLatency: { dashboard: 'inference', panelId: 3, name: 'Inference Latency' },
  tokensPerSec: { dashboard: 'inference', panelId: 5, name: 'Tokens/sec' },
};

type DashboardKey = keyof typeof DASHBOARDS;
type PanelKey = keyof typeof PANELS;
type TimeRange = '15m' | '1h' | '3h' | '6h' | '12h' | '24h' | '7d';

interface GrafanaEmbedProps {
  // Embed a full dashboard
  dashboard?: DashboardKey;
  // Or embed a specific panel
  panel?: PanelKey;
  // Time range
  timeRange?: TimeRange;
  // Custom variables to pass
  variables?: Record<string, string>;
  // Height in pixels
  height?: number;
  // Show header with dashboard selector
  showHeader?: boolean;
  // Callback when dashboard changes
  onDashboardChange?: (dashboard: DashboardKey) => void;
}

export function GrafanaEmbed({
  dashboard = 'cluster',
  panel,
  timeRange = '1h',
  variables = {},
  height = 400,
  showHeader = true,
  onDashboardChange,
}: GrafanaEmbedProps) {
  const [selectedDashboard, setSelectedDashboard] = useState<DashboardKey>(dashboard);
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>(timeRange);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const iframeSrc = useMemo(() => {
    const params = new URLSearchParams({
      orgId: '1',
      from: `now-${selectedTimeRange}`,
      to: 'now',
      theme: 'dark',
      kiosk: 'tv', // Hide Grafana chrome
      ...variables,
    });

    if (panel) {
      // Embed specific panel
      const panelConfig = PANELS[panel];
      const dashboardUid = DASHBOARDS[panelConfig.dashboard as DashboardKey].uid;
      return `${GRAFANA_URL}/d-solo/${dashboardUid}?panelId=${panelConfig.panelId}&${params}`;
    } else {
      // Embed full dashboard
      const dashboardUid = DASHBOARDS[selectedDashboard].uid;
      return `${GRAFANA_URL}/d/${dashboardUid}?${params}`;
    }
  }, [selectedDashboard, selectedTimeRange, panel, variables]);

  const handleDashboardChange = (newDashboard: DashboardKey) => {
    setSelectedDashboard(newDashboard);
    setIsLoading(true);
    setHasError(false);
    onDashboardChange?.(newDashboard);
  };

  return (
    <div className="grafana-embed flex flex-col">
      {showHeader && !panel && (
        <div
          className="flex items-center justify-between px-3 py-2 border-b"
          style={{ borderColor: 'var(--hydra-border)' }}
        >
          {/* Dashboard Selector */}
          <div className="flex items-center gap-2">
            <label className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              Dashboard:
            </label>
            <select
              value={selectedDashboard}
              onChange={(e) => handleDashboardChange(e.target.value as DashboardKey)}
              className="text-xs px-2 py-1 rounded border"
              style={{
                backgroundColor: 'var(--hydra-bg)',
                borderColor: 'var(--hydra-border)',
                color: 'var(--hydra-text)',
              }}
            >
              {Object.entries(DASHBOARDS).map(([key, { name }]) => (
                <option key={key} value={key}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          {/* Time Range Selector */}
          <div className="flex items-center gap-2">
            <label className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              Range:
            </label>
            <select
              value={selectedTimeRange}
              onChange={(e) => {
                setSelectedTimeRange(e.target.value as TimeRange);
                setIsLoading(true);
              }}
              className="text-xs px-2 py-1 rounded border"
              style={{
                backgroundColor: 'var(--hydra-bg)',
                borderColor: 'var(--hydra-border)',
                color: 'var(--hydra-text)',
              }}
            >
              <option value="15m">15 min</option>
              <option value="1h">1 hour</option>
              <option value="3h">3 hours</option>
              <option value="6h">6 hours</option>
              <option value="12h">12 hours</option>
              <option value="24h">24 hours</option>
              <option value="7d">7 days</option>
            </select>
          </div>

          {/* Open in Grafana Link */}
          <a
            href={`${GRAFANA_URL}/d/${DASHBOARDS[selectedDashboard].uid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 rounded transition-colors hover:bg-white/10"
            style={{ color: 'var(--hydra-cyan)' }}
          >
            Open in Grafana →
          </a>
        </div>
      )}

      {/* Iframe Container */}
      <div className="relative" style={{ height }}>
        {/* Loading State */}
        {isLoading && (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ backgroundColor: 'var(--hydra-bg)' }}
          >
            <div className="flex flex-col items-center gap-2">
              <div
                className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
                style={{ borderColor: 'var(--hydra-cyan)', borderTopColor: 'transparent' }}
              />
              <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                Loading Grafana...
              </span>
            </div>
          </div>
        )}

        {/* Error State */}
        {hasError && (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ backgroundColor: 'var(--hydra-bg)' }}
          >
            <div className="flex flex-col items-center gap-2 text-center px-4">
              <span className="text-2xl">⚠️</span>
              <span className="text-sm" style={{ color: 'var(--hydra-yellow)' }}>
                Failed to load Grafana dashboard
              </span>
              <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                Make sure Grafana is configured with allow_embedding=true
              </span>
              <a
                href={`${GRAFANA_URL}/d/${DASHBOARDS[selectedDashboard].uid}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs px-3 py-1.5 rounded mt-2"
                style={{
                  backgroundColor: 'var(--hydra-cyan)',
                  color: 'var(--hydra-bg)',
                }}
              >
                Open in Grafana
              </a>
            </div>
          </div>
        )}

        {/* Grafana iframe */}
        <iframe
          src={iframeSrc}
          width="100%"
          height="100%"
          frameBorder="0"
          onLoad={() => setIsLoading(false)}
          onError={() => {
            setIsLoading(false);
            setHasError(true);
          }}
          className={`${isLoading || hasError ? 'opacity-0' : 'opacity-100'} transition-opacity`}
          style={{ backgroundColor: 'var(--hydra-bg)' }}
        />
      </div>
    </div>
  );
}

// Compact panel embed for use in cards/widgets
interface GrafanaPanelProps {
  panel: PanelKey;
  timeRange?: TimeRange;
  height?: number;
}

export function GrafanaPanel({ panel, timeRange = '1h', height = 150 }: GrafanaPanelProps) {
  const panelConfig = PANELS[panel];

  return (
    <div className="grafana-panel">
      <div
        className="text-xs font-medium mb-1 px-1"
        style={{ color: 'var(--hydra-text-muted)' }}
      >
        {panelConfig.name}
      </div>
      <GrafanaEmbed
        panel={panel}
        timeRange={timeRange}
        height={height}
        showHeader={false}
      />
    </div>
  );
}
