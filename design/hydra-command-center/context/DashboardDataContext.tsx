import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// API base URL for Hydra Tools API
const HYDRA_API_URL = 'http://192.168.1.244:8700';

export interface NodeData {
  id: string;
  name: string;
  ip: string;
  status: 'online' | 'offline' | 'degraded';
  cpu: {
    usage: number;
    cores: number;
  };
  memory: {
    used: number;
    total: number;
    percent: number;
  };
  gpus?: {
    name: string;
    utilization: number;
    vramUsed: number;
    vramTotal: number;
    temperature: number;
    power: number;
  }[];
}

export interface DashboardStats {
  systemPower: number;
  vramUsed: number;
  vramTotal: number;
  activeAgents: number;
  totalAgents: number;
  uptime: string;
  containersRunning: number;
  containersTotal: number;
  servicesHealthy: number;
  servicesTotal: number;
}

export interface ServiceStatus {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'error' | 'unknown';
  health: 'healthy' | 'unhealthy' | 'unknown';
  port?: number;
  uptime?: string;
  responseTime?: number;
}

interface DashboardDataContextType {
  stats: DashboardStats;
  nodes: NodeData[];
  services: ServiceStatus[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastUpdated: Date | null;
}

const DashboardDataContext = createContext<DashboardDataContextType | undefined>(undefined);

// Default mock data - will be replaced with real API data
const DEFAULT_STATS: DashboardStats = {
  systemPower: 1247,
  vramUsed: 42,
  vramTotal: 88,
  activeAgents: 2,
  totalAgents: 4,
  uptime: '14d 03h',
  containersRunning: 58,
  containersTotal: 64,
  servicesHealthy: 22,
  servicesTotal: 25
};

const DEFAULT_NODES: NodeData[] = [
  {
    id: 'hydra-ai',
    name: 'hydra-ai',
    ip: '192.168.1.250',
    status: 'online',
    cpu: { usage: 45, cores: 32 },
    memory: { used: 48, total: 128, percent: 37.5 },
    gpus: [
      { name: 'RTX 5090', utilization: 78, vramUsed: 28, vramTotal: 32, temperature: 72, power: 420 },
      { name: 'RTX 4090', utilization: 65, vramUsed: 18, vramTotal: 24, temperature: 68, power: 280 }
    ]
  },
  {
    id: 'hydra-compute',
    name: 'hydra-compute',
    ip: '192.168.1.203',
    status: 'online',
    cpu: { usage: 32, cores: 32 },
    memory: { used: 45, total: 128, percent: 35.2 },
    gpus: [
      { name: 'RTX 5070 Ti #1', utilization: 42, vramUsed: 8, vramTotal: 16, temperature: 58, power: 180 },
      { name: 'RTX 5070 Ti #2', utilization: 38, vramUsed: 6, vramTotal: 16, temperature: 55, power: 165 }
    ]
  },
  {
    id: 'hydra-storage',
    name: 'hydra-storage',
    ip: '192.168.1.244',
    status: 'online',
    cpu: { usage: 28, cores: 32 },
    memory: { used: 72, total: 180, percent: 40 },
    gpus: []
  }
];

const DEFAULT_SERVICES: ServiceStatus[] = [
  { id: 'tabbyapi', name: 'TabbyAPI', status: 'running', health: 'healthy', port: 5000, responseTime: 45 },
  { id: 'litellm', name: 'LiteLLM', status: 'running', health: 'healthy', port: 4000, responseTime: 32 },
  { id: 'ollama', name: 'Ollama', status: 'running', health: 'healthy', port: 11434, responseTime: 28 },
  { id: 'comfyui', name: 'ComfyUI', status: 'running', health: 'healthy', port: 8188, responseTime: 120 },
  { id: 'qdrant', name: 'Qdrant', status: 'running', health: 'healthy', port: 6333, responseTime: 15 },
  { id: 'postgresql', name: 'PostgreSQL', status: 'running', health: 'healthy', port: 5432, responseTime: 8 },
  { id: 'n8n', name: 'n8n', status: 'running', health: 'healthy', port: 5678, responseTime: 95 },
  { id: 'grafana', name: 'Grafana', status: 'running', health: 'healthy', port: 3003, responseTime: 55 },
  { id: 'prometheus', name: 'Prometheus', status: 'running', health: 'healthy', port: 9090, responseTime: 22 }
];

interface DashboardDataProviderProps {
  children: ReactNode;
}

export const DashboardDataProvider: React.FC<DashboardDataProviderProps> = ({ children }) => {
  const [stats, setStats] = useState<DashboardStats>(DEFAULT_STATS);
  const [nodes, setNodes] = useState<NodeData[]>(DEFAULT_NODES);
  const [services, setServices] = useState<ServiceStatus[]>(DEFAULT_SERVICES);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // Attempt to fetch real data from Hydra Tools API
      const [healthResponse, metricsResponse] = await Promise.allSettled([
        fetch(`${HYDRA_API_URL}/health`),
        fetch(`${HYDRA_API_URL}/api/v1/metrics/cluster`)
      ]);

      // Process health data
      if (healthResponse.status === 'fulfilled' && healthResponse.value.ok) {
        const healthData = await healthResponse.value.json();
        // Update stats from health data if available
        if (healthData.containers) {
          setStats(prev => ({
            ...prev,
            containersRunning: healthData.containers.running || prev.containersRunning,
            containersTotal: healthData.containers.total || prev.containersTotal
          }));
        }
      }

      // Process metrics data
      if (metricsResponse.status === 'fulfilled' && metricsResponse.value.ok) {
        const metricsData = await metricsResponse.value.json();
        // Update nodes from metrics if available
        if (metricsData.nodes) {
          setNodes(metricsData.nodes);
        }
        if (metricsData.services) {
          setServices(metricsData.services);
        }
      }

      setLastUpdated(new Date());
    } catch (err) {
      console.warn('Failed to fetch dashboard data, using defaults:', err);
      // Keep using default data on error - don't fail the UI
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and periodic refresh
  useEffect(() => {
    fetchDashboardData();

    // Refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);

    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  const value: DashboardDataContextType = {
    stats,
    nodes,
    services,
    loading,
    error,
    refresh: fetchDashboardData,
    lastUpdated
  };

  return (
    <DashboardDataContext.Provider value={value}>
      {children}
    </DashboardDataContext.Provider>
  );
};

export const useDashboardData = (): DashboardDataContextType => {
  const context = useContext(DashboardDataContext);
  if (context === undefined) {
    throw new Error('useDashboardData must be used within a DashboardDataProvider');
  }
  return context;
};
