import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { Project, Node, Service, KnowledgeCollection, AIModel, Artifact } from '../types';
import {
  getDashboardProjects,
  getDashboardNodes,
  getDashboardServices,
  getDashboardModels,
  getDashboardCollections,
  getDashboardStats,
  getSystemHealth,
  getRecentAlerts,
} from '../services/hydraApi';

interface SystemStats {
  activeAgents: number;
  totalAgents: number;
  systemPower: number;
  vramUsed: number;
  vramTotal: number;
  uptime: string;
}

interface Alert {
  id: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
}

interface DashboardDataContextType {
  // Data
  projects: Project[];
  nodes: Node[];
  services: Service[];
  models: AIModel[];
  collections: KnowledgeCollection[];
  artifacts: Artifact[];
  stats: SystemStats | null;
  alerts: Alert[];

  // Loading states
  isLoading: boolean;
  projectsLoading: boolean;
  nodesLoading: boolean;
  servicesLoading: boolean;
  modelsLoading: boolean;
  collectionsLoading: boolean;

  // Error states
  error: string | null;

  // Actions
  refreshAll: () => Promise<void>;
  refreshProjects: () => Promise<void>;
  refreshNodes: () => Promise<void>;
  refreshServices: () => Promise<void>;
  refreshModels: () => Promise<void>;
  refreshCollections: () => Promise<void>;
  refreshStats: () => Promise<void>;
}

const DashboardDataContext = createContext<DashboardDataContextType | undefined>(undefined);

export const DashboardDataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Data state
  const [projects, setProjects] = useState<Project[]>([]);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [collections, setCollections] = useState<KnowledgeCollection[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  // Loading states
  const [isLoading, setIsLoading] = useState(true);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [nodesLoading, setNodesLoading] = useState(false);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [collectionsLoading, setCollectionsLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  // Transform API responses to UI types
  const transformProject = (apiProject: any): Project => ({
    id: apiProject.id,
    name: apiProject.name,
    status: apiProject.status as Project['status'],
    agentCount: apiProject.agentCount,
    agentIds: apiProject.agentIds || [],
    progress: apiProject.progress,
    description: apiProject.description,
    lastUpdated: apiProject.lastUpdated,
  });

  const transformNode = (apiNode: any): Node => ({
    id: apiNode.id,
    name: apiNode.name,
    ip: apiNode.ip,
    cpu: apiNode.cpu,
    ram: apiNode.ram,
    gpus: apiNode.gpus,
    status: apiNode.status as Node['status'],
    uptime: apiNode.uptime,
  });

  const transformService = (apiService: any): Service => ({
    id: apiService.id,
    name: apiService.name,
    node: apiService.node,
    port: apiService.port,
    status: apiService.status as Service['status'],
    uptime: apiService.uptime,
  });

  const transformModel = (apiModel: any): AIModel => ({
    id: apiModel.id,
    name: apiModel.name,
    paramSize: apiModel.paramSize,
    quantization: apiModel.quantization,
    vramUsage: apiModel.vramUsage,
    contextLength: apiModel.contextLength,
    status: apiModel.status as AIModel['status'],
    provider: apiModel.provider as AIModel['provider'],
  });

  const transformCollection = (apiCollection: any): KnowledgeCollection => ({
    id: apiCollection.id,
    name: apiCollection.name,
    docCount: apiCollection.docCount,
    chunkCount: apiCollection.chunkCount,
    lastIngested: apiCollection.lastIngested,
    topics: apiCollection.topics || [],
    status: apiCollection.status as KnowledgeCollection['status'],
  });

  // Refresh functions
  const refreshProjects = useCallback(async () => {
    setProjectsLoading(true);
    try {
      const result = await getDashboardProjects();
      if (result.data) {
        setProjects(result.data.projects.map(transformProject));
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  const refreshNodes = useCallback(async () => {
    setNodesLoading(true);
    try {
      const result = await getDashboardNodes();
      if (result.data) {
        setNodes(result.data.nodes.map(transformNode));
      }
    } catch (err) {
      console.error('Failed to fetch nodes:', err);
    } finally {
      setNodesLoading(false);
    }
  }, []);

  const refreshServices = useCallback(async () => {
    setServicesLoading(true);
    try {
      const result = await getDashboardServices();
      if (result.data) {
        setServices(result.data.services.map(transformService));
      }
    } catch (err) {
      console.error('Failed to fetch services:', err);
    } finally {
      setServicesLoading(false);
    }
  }, []);

  const refreshModels = useCallback(async () => {
    setModelsLoading(true);
    try {
      const result = await getDashboardModels();
      if (result.data) {
        setModels(result.data.models.map(transformModel));
      }
    } catch (err) {
      console.error('Failed to fetch models:', err);
    } finally {
      setModelsLoading(false);
    }
  }, []);

  const refreshCollections = useCallback(async () => {
    setCollectionsLoading(true);
    try {
      const result = await getDashboardCollections();
      if (result.data) {
        setCollections(result.data.collections.map(transformCollection));
      }
    } catch (err) {
      console.error('Failed to fetch collections:', err);
    } finally {
      setCollectionsLoading(false);
    }
  }, []);

  const refreshStats = useCallback(async () => {
    try {
      const result = await getDashboardStats();
      if (result.data) {
        setStats(result.data);
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);

  const refreshAlerts = useCallback(async () => {
    try {
      const result = await getRecentAlerts();
      if (result.data) {
        setAlerts(result.data.alerts || []);
      }
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      await Promise.all([
        refreshProjects(),
        refreshNodes(),
        refreshServices(),
        refreshModels(),
        refreshCollections(),
        refreshStats(),
        refreshAlerts(),
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, [refreshProjects, refreshNodes, refreshServices, refreshModels, refreshCollections, refreshStats, refreshAlerts]);

  // Initial load
  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  // Auto-refresh nodes every 30 seconds (for GPU metrics)
  useEffect(() => {
    const interval = setInterval(refreshNodes, 30000);
    return () => clearInterval(interval);
  }, [refreshNodes]);

  // Auto-refresh stats every 15 seconds
  useEffect(() => {
    const interval = setInterval(refreshStats, 15000);
    return () => clearInterval(interval);
  }, [refreshStats]);

  return (
    <DashboardDataContext.Provider
      value={{
        projects,
        nodes,
        services,
        models,
        collections,
        artifacts,
        stats,
        alerts,
        isLoading,
        projectsLoading,
        nodesLoading,
        servicesLoading,
        modelsLoading,
        collectionsLoading,
        error,
        refreshAll,
        refreshProjects,
        refreshNodes,
        refreshServices,
        refreshModels,
        refreshCollections,
        refreshStats,
      }}
    >
      {children}
    </DashboardDataContext.Provider>
  );
};

export const useDashboardData = () => {
  const context = useContext(DashboardDataContext);
  if (context === undefined) {
    throw new Error('useDashboardData must be used within a DashboardDataProvider');
  }
  return context;
};
