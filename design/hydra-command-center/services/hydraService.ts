/**
 * Hydra Tools API Client
 *
 * Provides TypeScript client for the Hydra Tools API backend:
 * - Unraid management (arrays, disks, containers, VMs)
 * - Cluster metrics and health
 * - SSE real-time streaming
 * - Agent management
 * - Model operations
 */

// API Base URL - can be overridden via environment
const HYDRA_API_URL = 'http://192.168.1.244:8700';

// =============================================================================
// TYPES
// =============================================================================

export interface ArrayStatus {
  state: string;
  numDisks: number;
  numProtected: number;
  numUnprotected: number;
  parityCheck?: {
    status: string;
    progress: number;
    errors: number;
  };
}

export interface DiskInfo {
  device: string;
  name: string;
  size: number;
  temperature: number | null;
  smartStatus: string;
  interfaceType: string;
  spundown: boolean;
}

export interface DiskHealthSummary {
  total_disks: number;
  healthy: number;
  warning: number;
  failed: number;
  avg_temperature: number;
  max_temperature: number;
  disks_spinning: number;
}

export interface ContainerInfo {
  id: string;
  names: string[];
  image: string;
  state: string;
  status: string;
  autoStart: boolean;
  ports: {
    ip?: string;
    privatePort: number;
    publicPort?: number;
    type: string;
  }[];
}

export interface ContainerStats {
  total: number;
  running: number;
  stopped: number;
  other: number;
}

export interface VMInfo {
  uuid: string;
  name: string;
  state: string;
  vcpu: number;
  memory: number;
  autostart: boolean;
}

export interface SystemInfo {
  cpu: {
    model: string;
    cores: number;
    threads: number;
  };
  memory: {
    total: number;
    available: number;
    used: number;
  };
  os: {
    version: string;
    kernel: string;
  };
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy';
  response_time_ms: number;
  version?: string;
  kernel?: string;
  error?: string;
}

export interface UnraidMetrics {
  array: ArrayStatus;
  disks: DiskHealthSummary;
  containers: ContainerStats;
  system: SystemInfo;
  metrics: any | null;
}

export interface SSEEvent {
  event: string;
  data: any;
  id?: string;
}

// =============================================================================
// API CLIENT
// =============================================================================

class HydraApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = HYDRA_API_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  // ===========================================================================
  // HEALTH
  // ===========================================================================

  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.request('/health');
  }

  async unraidHealthCheck(): Promise<HealthCheck> {
    return this.request('/api/v1/unraid/health');
  }

  // ===========================================================================
  // UNRAID - ARRAY
  // ===========================================================================

  async getArrayStatus(): Promise<ArrayStatus> {
    return this.request('/api/v1/unraid/array/status');
  }

  async startArray(): Promise<{ status: string; array: any }> {
    return this.request('/api/v1/unraid/array/start', { method: 'POST' });
  }

  async stopArray(): Promise<{ status: string; array: any }> {
    return this.request('/api/v1/unraid/array/stop', { method: 'POST' });
  }

  async startParityCheck(correct: boolean = false): Promise<{ status: string }> {
    return this.request('/api/v1/unraid/array/parity-check', {
      method: 'POST',
      body: JSON.stringify({ correct }),
    });
  }

  async pauseParityCheck(): Promise<{ status: string }> {
    return this.request('/api/v1/unraid/array/parity-check/pause', { method: 'POST' });
  }

  async resumeParityCheck(): Promise<{ status: string }> {
    return this.request('/api/v1/unraid/array/parity-check/resume', { method: 'POST' });
  }

  async cancelParityCheck(): Promise<{ status: string }> {
    return this.request('/api/v1/unraid/array/parity-check/cancel', { method: 'POST' });
  }

  // ===========================================================================
  // UNRAID - DISKS
  // ===========================================================================

  async getDisks(includeSmart: boolean = false): Promise<DiskInfo[]> {
    const query = includeSmart ? '?include_smart=true' : '';
    return this.request(`/api/v1/unraid/disks${query}`);
  }

  async getDiskHealth(): Promise<DiskHealthSummary> {
    return this.request('/api/v1/unraid/disks/health');
  }

  // ===========================================================================
  // UNRAID - CONTAINERS
  // ===========================================================================

  async getContainers(): Promise<ContainerInfo[]> {
    return this.request('/api/v1/unraid/containers');
  }

  async getContainerStats(): Promise<ContainerStats> {
    return this.request('/api/v1/unraid/containers/stats');
  }

  async getContainer(containerId: string): Promise<ContainerInfo> {
    return this.request(`/api/v1/unraid/containers/${encodeURIComponent(containerId)}`);
  }

  async startContainer(containerId: string): Promise<{ id: string; state: string }> {
    return this.request(`/api/v1/unraid/containers/${encodeURIComponent(containerId)}/start`, {
      method: 'POST',
    });
  }

  async stopContainer(containerId: string): Promise<{ id: string; state: string }> {
    return this.request(`/api/v1/unraid/containers/${encodeURIComponent(containerId)}/stop`, {
      method: 'POST',
    });
  }

  async restartContainer(containerId: string): Promise<{ id: string; state: string }> {
    return this.request(`/api/v1/unraid/containers/${encodeURIComponent(containerId)}/restart`, {
      method: 'POST',
    });
  }

  // ===========================================================================
  // UNRAID - VMs
  // ===========================================================================

  async getVMs(): Promise<VMInfo[]> {
    return this.request('/api/v1/unraid/vms');
  }

  async startVM(vmUuid: string): Promise<{ uuid: string; state: string }> {
    return this.request(`/api/v1/unraid/vms/${encodeURIComponent(vmUuid)}/start`, {
      method: 'POST',
    });
  }

  async stopVM(vmUuid: string): Promise<{ uuid: string; state: string }> {
    return this.request(`/api/v1/unraid/vms/${encodeURIComponent(vmUuid)}/stop`, {
      method: 'POST',
    });
  }

  async pauseVM(vmUuid: string): Promise<{ uuid: string; state: string }> {
    return this.request(`/api/v1/unraid/vms/${encodeURIComponent(vmUuid)}/pause`, {
      method: 'POST',
    });
  }

  async resumeVM(vmUuid: string): Promise<{ uuid: string; state: string }> {
    return this.request(`/api/v1/unraid/vms/${encodeURIComponent(vmUuid)}/resume`, {
      method: 'POST',
    });
  }

  // ===========================================================================
  // UNRAID - SYSTEM
  // ===========================================================================

  async getSystemInfo(): Promise<SystemInfo> {
    return this.request('/api/v1/unraid/system/info');
  }

  async getNotifications(limit: number = 20): Promise<any[]> {
    return this.request(`/api/v1/unraid/notifications?limit=${limit}`);
  }

  async getUsers(): Promise<any[]> {
    return this.request('/api/v1/unraid/users');
  }

  // ===========================================================================
  // UNRAID - COMPREHENSIVE METRICS
  // ===========================================================================

  async getUnraidMetrics(): Promise<UnraidMetrics> {
    return this.request('/api/v1/unraid/metrics');
  }

  async getSimpleMetrics(): Promise<any> {
    return this.request('/api/v1/unraid/metrics/simple');
  }

  // ===========================================================================
  // CLUSTER METRICS
  // ===========================================================================

  async getClusterMetrics(): Promise<any> {
    return this.request('/api/v1/metrics/cluster');
  }

  async getClusterHealth(): Promise<any> {
    return this.request('/api/v1/health/cluster');
  }

  // ===========================================================================
  // SSE - REAL-TIME STREAMING
  // ===========================================================================

  /**
   * Connect to SSE stream for real-time updates.
   *
   * @param options Configuration options
   * @param options.events Comma-separated event types to subscribe to
   * @param options.clientId Optional client identifier
   * @param options.onEvent Callback for each event
   * @param options.onError Callback for errors
   * @param options.onOpen Callback when connection opens
   * @returns Function to close the connection
   */
  connectSSE(options: {
    events?: string;
    clientId?: string;
    onEvent: (event: SSEEvent) => void;
    onError?: (error: Event) => void;
    onOpen?: () => void;
  }): () => void {
    const params = new URLSearchParams();
    if (options.events) params.set('events', options.events);
    if (options.clientId) params.set('client_id', options.clientId);

    const url = `${this.baseUrl}/api/v1/events/stream?${params.toString()}`;
    const eventSource = new EventSource(url);

    // Handle generic message events
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        options.onEvent({ event: 'message', data, id: event.lastEventId });
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    // Handle specific event types
    const eventTypes = [
      'connected',
      'cluster_health',
      'container_status',
      'gpu_metrics',
      'agent_status',
      'alert',
      'notification',
      'model_status',
      'heartbeat',
    ];

    eventTypes.forEach((type) => {
      eventSource.addEventListener(type, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          options.onEvent({ event: type, data, id: event.lastEventId });
        } catch (e) {
          console.error(`Failed to parse ${type} event:`, e);
        }
      });
    });

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      options.onError?.(error);
    };

    eventSource.onopen = () => {
      console.log('SSE connection established');
      options.onOpen?.();
    };

    // Return cleanup function
    return () => {
      eventSource.close();
    };
  }

  /**
   * Get SSE connection status.
   */
  async getSSEStatus(): Promise<{ active_connections: number; timestamp: string }> {
    return this.request('/api/v1/events/status');
  }

  // ===========================================================================
  // AGENTS
  // ===========================================================================

  async getAgents(): Promise<any[]> {
    return this.request('/api/v1/agents');
  }

  async getAgentScheduler(): Promise<any> {
    return this.request('/api/v1/agents/scheduler');
  }

  async createTask(task: any): Promise<any> {
    return this.request('/api/v1/agents/tasks', {
      method: 'POST',
      body: JSON.stringify(task),
    });
  }

  // ===========================================================================
  // MODELS / INFERENCE
  // ===========================================================================

  async getModelStatus(): Promise<any> {
    return this.request('/api/v1/inference/status');
  }

  async loadModel(modelId: string): Promise<any> {
    return this.request('/api/v1/inference/load', {
      method: 'POST',
      body: JSON.stringify({ model_id: modelId }),
    });
  }

  async unloadModel(): Promise<any> {
    return this.request('/api/v1/inference/unload', { method: 'POST' });
  }
}

// =============================================================================
// SINGLETON INSTANCE
// =============================================================================

export const hydraApi = new HydraApiClient();

// =============================================================================
// CONVENIENCE HOOKS (for React Query integration)
// =============================================================================

/**
 * Create a custom hook for fetching data with error handling.
 * Use with TanStack Query for caching and state management.
 *
 * Example:
 *   const { data, isLoading, error } = useQuery({
 *     queryKey: ['unraid', 'metrics'],
 *     queryFn: () => hydraApi.getUnraidMetrics()
 *   });
 */

export default hydraApi;
