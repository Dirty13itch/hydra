const MCP_URL = 'http://192.168.1.244:8600';

export interface ClusterStatus {
  timestamp: string;
  prometheus?: { up: number; total: number } | { error: string };
  letta?: any;
  crewai?: any;
  qdrant?: { collections: number } | { error: string };
}

export interface ServiceStatus {
  [key: string]: string;
}

export interface ServiceDetailed {
  [key: string]: {
    status: string;
    uptime_seconds: number | null;
  };
}

export interface MetricsSummary {
  cpu_avg: number | null;
  memory_used_pct: number | null;
  disk_used_pct: number | null;
}

export interface NodeMetrics {
  [instance: string]: {
    name: string;
    cpu_pct?: number;
    memory_pct?: number;
  };
}

export interface Container {
  id?: string;
  name: string;
  image?: string;
  status?: string;
  state?: string;
  protected: boolean;
}

export interface ContainersResponse {
  containers: Container[];
  count: number;
  source?: string;
}

export interface AuditEntry {
  timestamp: string;
  action: string;
  details: Record<string, any>;
  result: string;
  ip: string;
}

export interface GpuInfo {
  node: string;
  index: string;
  name: string;
  temp_c: number;
  utilization: number;
  power_w: number;
  memory_used_gb?: number;
  memory_total_gb?: number;
}

export interface StoragePool {
  name: string;
  type: string;
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  percent_used: number;
  disk_count?: number;
  status: string;
}

export interface StoragePoolsData {
  timestamp: string;
  pools: StoragePool[];
  summary: {
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    percent_used: number;
  };
}

export interface Alert {
  status: 'firing' | 'resolved';
  labels: {
    alertname: string;
    severity?: string;
    instance?: string;
    job?: string;
    [key: string]: string | undefined;
  };
  annotations: {
    summary?: string;
    description?: string;
    [key: string]: string | undefined;
  };
  startsAt: string;
  endsAt: string;
  fingerprint: string;
}

export interface AlertsResponse {
  alerts: Alert[];
  status: string;
}

export interface AlertSilence {
  id?: string;
  matchers: Array<{
    name: string;
    value: string;
    isRegex: boolean;
    isEqual?: boolean;
  }>;
  startsAt: string;
  endsAt: string;
  createdBy: string;
  comment: string;
  status?: {
    state: 'active' | 'pending' | 'expired';
  };
}

export interface OllamaModel {
  name: string;
  model: string;
  size: number;
  digest: string;
  details: {
    parameter_size: string;
    quantization_level: string;
  };
}

export interface OllamaRunningModel {
  name: string;
  model: string;
  size: number;
  size_vram: number;
  expires_at: string;
}

export interface OllamaModelsResponse {
  models: OllamaModel[];
}

export interface OllamaRunningResponse {
  models: OllamaRunningModel[];
}

export interface LettaAgent {
  id: string;
  name: string;
  description?: string;
}

export interface LettaMessage {
  id: string;
  date: string;
  message_type: 'system_message' | 'reasoning_message' | 'assistant_message' | 'user_message';
  content: string;
}

export interface LettaSendResponse {
  messages?: LettaMessage[];
  error?: {
    type: string;
    message: string;
    detail?: string;
  };
}

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${MCP_URL}${path}`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

async function postJSON<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${MCP_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return res.json();
}

async function deleteJSON(path: string): Promise<void> {
  const res = await fetch(`${MCP_URL}${path}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
}

export interface RestartResponse {
  status: string;
  message?: string;
  confirmation_token?: string;
  expires_in_seconds?: number;
  warning?: string;
}

export const api = {
  health: () => fetchJSON<{ status: string; version: string; uptime_seconds: number }>('/health'),
  clusterStatus: () => fetchJSON<ClusterStatus>('/cluster/status'),
  servicesStatus: () => fetchJSON<ServiceStatus>('/services/status'),
  servicesDetailed: () => fetchJSON<ServiceDetailed>('/services/detailed'),
  metricsSummary: () => fetchJSON<MetricsSummary>('/metrics/summary'),
  metricsNodes: () => fetchJSON<NodeMetrics>('/metrics/nodes'),
  containers: () => fetchJSON<ContainersResponse>('/containers/list'),
  auditLog: (limit = 50) => fetchJSON<{ entries: AuditEntry[]; total: number }>(`/audit/log?limit=${limit}`),
  protectedContainers: () => fetchJSON<{ protected_containers: string[] }>('/safety/protected'),
  pendingConfirmations: () => fetchJSON<{ pending: any[] }>('/safety/pending'),
  gpuStatus: () => fetchJSON<{ gpus: GpuInfo[] }>('/gpu/status'),
  storagePools: () => fetchJSON<StoragePoolsData>('/storage/pools'),

  // Alertmanager via MCP proxy
  alerts: () => fetchJSON<Alert[]>('/proxy/alertmanager/alerts'),
  alertSilences: () => fetchJSON<AlertSilence[]>('/proxy/alertmanager/silences'),
  createAlertSilence: (silence: Omit<AlertSilence, 'id' | 'status'>) =>
    postJSON<{ silenceID: string }>('/proxy/alertmanager/silences', silence),
  deleteAlertSilence: (silenceId: string) =>
    deleteJSON(`/proxy/alertmanager/silence/${silenceId}`),

  // Ollama via MCP proxy
  ollamaModels: () => fetchJSON<OllamaModelsResponse>('/proxy/ollama/tags'),
  ollamaRunning: () => fetchJSON<OllamaRunningResponse>('/proxy/ollama/ps'),
  ollamaLoadModel: (model: string) =>
    postJSON<any>('/proxy/ollama/generate', { model, prompt: '', keep_alive: '30m' }),
  ollamaUnloadModel: (model: string) =>
    postJSON<any>('/proxy/ollama/generate', { model, prompt: '', keep_alive: 0 }),

  // Container control
  restartContainer: (container: string, confirmationToken?: string) =>
    postJSON<RestartResponse>('/containers/restart', { container, confirmation_token: confirmationToken }),
  containerLogs: (container: string, tail = 100) =>
    fetchJSON<{ container: string; logs: string }>(`/containers/${container}/logs?tail=${tail}`),
  startContainer: (container: string) =>
    postJSON<RestartResponse>('/containers/start', { container }),
  stopContainer: (container: string) =>
    postJSON<RestartResponse>('/containers/stop', { container }),

  // Letta via MCP proxy
  lettaAgents: () => fetchJSON<LettaAgent[]>('/proxy/letta/agents'),
  lettaMessages: (agentId: string) => fetchJSON<LettaMessage[]>(`/proxy/letta/agents/${agentId}/messages`),
  lettaSendMessage: (agentId: string, content: string) =>
    postJSON<LettaSendResponse>(`/proxy/letta/agents/${agentId}/messages`, {
      messages: [{ role: 'user', content }]
    }),
};

export default api;
