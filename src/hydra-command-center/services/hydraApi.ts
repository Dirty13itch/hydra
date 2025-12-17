/**
 * Hydra API Service
 * Connects the Command Center UI to the real Hydra Tools API
 */

const HYDRA_API_BASE = import.meta.env.VITE_HYDRA_API_URL || 'http://192.168.1.244:8700';

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${HYDRA_API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return { data, error: null };
  } catch (err) {
    console.error(`API call failed: ${endpoint}`, err);
    return { data: null, error: err instanceof Error ? err.message : 'Unknown error' };
  }
}

// ============= Health & Status =============

export async function getSystemHealth() {
  return fetchApi<{
    status: string;
    components: Record<string, { status: string; message?: string }>;
  }>('/health');
}

export async function getContainerHealth() {
  return fetchApi<{
    summary: { total: number; healthy: number; unhealthy: number };
    containers: Array<{
      name: string;
      status: string;
      healthy: boolean;
      message?: string;
    }>;
  }>('/container-health/status');
}

export async function getUnhealthyContainers() {
  return fetchApi<{
    containers: Array<{
      name: string;
      status: string;
      message: string;
      consecutive_failures: number;
    }>;
  }>('/container-health/unhealthy');
}

// ============= Agent Scheduler =============

export async function getAgentSchedulerStatus() {
  return fetchApi<{
    running: boolean;
    active_tasks: number;
    completed_tasks: number;
    queue_depth: number;
  }>('/agent-scheduler/status');
}

export async function getAgentQueue() {
  return fetchApi<{
    tasks: Array<{
      task_id: string;
      description: string;
      agent_type: string;
      status: string;
      progress: number;
      created_at: string;
      started_at?: string;
    }>;
  }>('/agent-scheduler/queue');
}

export async function scheduleAgentTask(task: {
  description: string;
  agent_type: string;
  payload: Record<string, unknown>;
  priority?: number;
}) {
  return fetchApi<{ task_id: string; status: string }>('/agent-scheduler/schedule', {
    method: 'POST',
    body: JSON.stringify(task),
  });
}

// ============= Crews =============

export async function getCrewsStatus() {
  return fetchApi<{
    crews: Array<{
      name: string;
      status: string;
      last_run?: string;
    }>;
  }>('/crews/status');
}

export async function runMonitoringCrew(type: 'quick' | 'full' = 'quick') {
  return fetchApi<{ status: string; results: unknown }>(`/crews/monitoring/${type}`, {
    method: 'POST',
  });
}

// ============= Memory =============

export async function getMemoryStatus() {
  return fetchApi<{
    stats: {
      total_memories: number;
      by_tier: Record<string, number>;
    };
  }>('/memory/status');
}

export async function searchMemory(query: string, limit = 10) {
  return fetchApi<{
    results: Array<{
      id: string;
      content: string;
      score: number;
      metadata: Record<string, unknown>;
    }>;
  }>(`/memory/search?query=${encodeURIComponent(query)}&limit=${limit}`);
}

// ============= Self-Improvement =============

export async function getSelfImprovementStatus() {
  return fetchApi<{
    pending_proposals: number;
    benchmarks_run: number;
    last_improvement?: string;
  }>('/self-improvement/status');
}

export async function runBenchmark() {
  return fetchApi<{
    overall_score: number;
    categories: Record<string, { score: number; tests: number }>;
  }>('/benchmark/run', { method: 'POST' });
}

// ============= Infrastructure Metrics =============

export async function getInferenceStatus() {
  return fetchApi<{
    model_loaded: boolean;
    model_name?: string;
    vram_used_gb?: number;
    tokens_per_second?: number;
  }>('/crews/monitoring/inference', { method: 'POST' });
}

export async function getGpuStatus() {
  return fetchApi<{
    gpus: Array<{
      name: string;
      memory_used: number;
      memory_total: number;
      utilization: number;
      temperature: number;
      power_draw: number;
    }>;
  }>('/crews/monitoring/gpus', { method: 'POST' });
}

// ============= Voice Pipeline =============

export async function getVoiceStatus() {
  return fetchApi<{
    wake_word_enabled: boolean;
    tts_ready: boolean;
    stt_ready: boolean;
  }>('/voice/status');
}

export async function synthesizeSpeech(text: string) {
  return fetchApi<{
    audio_base64: string;
    duration_ms: number;
  }>('/voice/speak', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

// ============= Knowledge / RAG =============

export async function getKnowledgeCollections() {
  return fetchApi<{
    collections: Array<{
      name: string;
      document_count: number;
      chunk_count: number;
      status: string;
    }>;
  }>('/rag/collections');
}

// ============= Audit Log =============

export async function getRecentAuditLogs(limit = 50) {
  return fetchApi<{
    logs: Array<{
      id: string;
      action: string;
      status: string;
      timestamp: string;
      data?: Record<string, unknown>;
    }>;
  }>(`/audit/recent?limit=${limit}`);
}

// ============= Alerts =============

export async function getRecentAlerts() {
  return fetchApi<{
    alerts: Array<{
      id: string;
      severity: 'info' | 'warning' | 'error' | 'critical';
      message: string;
      timestamp: string;
    }>;
  }>('/alerts/recent');
}

// ============= Dashboard Endpoints (Command Center) =============

export async function getDashboardAgents() {
  return fetchApi<{
    agents: Array<{
      id: string;
      name: string;
      type: string;
      status: string;
      model: string;
      task: string;
      progress: number;
      uptime: string;
      tools: string[];
      dependencies: string[];
      config: {
        temperature: number;
        top_p: number;
        top_k: number;
        max_output_tokens: number;
        system_instruction: string;
      };
      thinkingStream: Array<{
        step_id: string;
        timestamp: string;
        content: string;
        step_type: string;
      }>;
      lastActivity: string;
    }>;
    count: number;
  }>('/dashboard/agents');
}

export async function getDashboardAgent(agentId: string) {
  return fetchApi<{
    id: string;
    name: string;
    type: string;
    status: string;
    model: string;
    task: string;
    progress: number;
    uptime: string;
    tools: string[];
    thinkingStream: Array<{
      step_id: string;
      timestamp: string;
      content: string;
      step_type: string;
    }>;
  }>(`/dashboard/agents/${agentId}`);
}

export async function getAgentThinking(agentId: string, limit = 20) {
  return fetchApi<{
    agentId: string;
    agentName: string;
    steps: Array<{
      step_id: string;
      timestamp: string;
      content: string;
      step_type: string;
    }>;
  }>(`/dashboard/agents/${agentId}/thinking?limit=${limit}`);
}

export async function updateDashboardAgent(agentId: string, updates: { status?: string; task?: string; progress?: number }) {
  return fetchApi<{
    id: string;
    status: string;
    task: string;
    progress: number;
  }>(`/dashboard/agents/${agentId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export async function addAgentThinkingStep(agentId: string, content: string, stepType = 'reasoning') {
  return fetchApi<{
    step_id: string;
    timestamp: string;
    content: string;
    step_type: string;
  }>(`/dashboard/agents/${agentId}/thinking`, {
    method: 'POST',
    body: JSON.stringify({ content, step_type: stepType }),
  });
}

export async function updateAgentConfig(agentId: string, config: {
  temperature?: number;
  top_p?: number;
  top_k?: number;
  max_output_tokens?: number;
  system_instruction?: string;
}) {
  return fetchApi<{
    id: string;
    name: string;
    type: string;
    config: {
      temperature: number;
      top_p: number;
      top_k: number;
      max_output_tokens: number;
      system_instruction: string;
    };
  }>(`/dashboard/agents/${agentId}/config`, {
    method: 'PATCH',
    body: JSON.stringify(config),
  });
}

export async function createDashboardAgent(agent: {
  name: string;
  type?: string;
  model?: string;
  task?: string;
  tools?: string[];
  config?: {
    temperature?: number;
    top_p?: number;
    top_k?: number;
    max_output_tokens?: number;
    system_instruction?: string;
  };
}) {
  return fetchApi<{
    id: string;
    name: string;
    type: string;
    status: string;
    model: string;
    task: string;
    progress: number;
    tools: string[];
    config: Record<string, unknown>;
  }>('/dashboard/agents', {
    method: 'POST',
    body: JSON.stringify(agent),
  });
}

export async function deleteDashboardAgent(agentId: string) {
  return fetchApi<{
    success: boolean;
    agentId: string;
  }>(`/dashboard/agents/${agentId}`, {
    method: 'DELETE',
  });
}

export async function getDashboardProjects() {
  return fetchApi<{
    projects: Array<{
      id: string;
      name: string;
      status: string;
      agentCount: number;
      agentIds: string[];
      progress: number;
      description: string;
      lastUpdated: string;
    }>;
    count: number;
  }>('/dashboard/projects');
}

export async function getDashboardNodes() {
  return fetchApi<{
    nodes: Array<{
      id: string;
      name: string;
      ip: string;
      cpu: number;
      ram: { used: number; total: number };
      gpus: Array<{
        name: string;
        util: number;
        vram: number;
        totalVram: number;
        temp: number;
        power: number;
      }>;
      status: string;
      uptime: string;
    }>;
    count: number;
  }>('/dashboard/nodes');
}

export async function getDashboardServices() {
  return fetchApi<{
    services: Array<{
      id: string;
      name: string;
      node: string;
      port: number;
      status: string;
      uptime: string;
    }>;
    count: number;
  }>('/dashboard/services');
}

export async function getDashboardModels() {
  return fetchApi<{
    models: Array<{
      id: string;
      name: string;
      paramSize: string;
      quantization: string;
      vramUsage: number;
      contextLength: string;
      status: string;
      provider: string;
    }>;
    count: number;
  }>('/dashboard/models');
}

export async function getDashboardCollections() {
  return fetchApi<{
    collections: Array<{
      id: string;
      name: string;
      docCount: number;
      chunkCount: number;
      lastIngested: string;
      topics: string[];
      status: string;
    }>;
    count: number;
  }>('/dashboard/collections');
}

export async function getDashboardStats() {
  return fetchApi<{
    activeAgents: number;
    totalAgents: number;
    systemPower: number;
    vramUsed: number;
    vramTotal: number;
    uptime: string;
    timestamp: string;
  }>('/dashboard/stats');
}

// ============= WebSocket for Real-time Updates =============

export function createDashboardWebSocket(
  onMessage: (type: string, data: unknown) => void,
  onConnect?: () => void,
  onDisconnect?: () => void
): WebSocket {
  const wsUrl = HYDRA_API_BASE.replace('http', 'ws') + '/dashboard/ws';
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('Dashboard WebSocket connected');
    onConnect?.();
  };

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      onMessage(message.type, message.data);
    } catch (err) {
      console.error('WebSocket message parse error:', err);
    }
  };

  ws.onerror = (err) => {
    console.error('WebSocket error:', err);
  };

  ws.onclose = () => {
    console.log('Dashboard WebSocket disconnected');
    onDisconnect?.();
  };

  return ws;
}

// Legacy WebSocket function for backwards compatibility
export function createWebSocketConnection(onMessage: (data: unknown) => void) {
  return createDashboardWebSocket((type, data) => onMessage({ type, data }));
}

// ============= Home Automation API =============

export interface Room {
  id: string;
  name: string;
  temp: number | null;
  humidity: number | null;
  devices: number;
  lights_on: boolean;
  active: boolean;
  area_id?: string;
}

export interface HomeDevice {
  id: string;
  name: string;
  entity_id: string;
  device_type: string;
  state: string;
  room_id?: string;
  attributes: Record<string, unknown>;
}

export interface HomeScene {
  id: string;
  name: string;
  entity_id: string;
  icon?: string;
}

export async function getHomeStatus() {
  return fetchApi<{
    connected: boolean;
    configured: boolean;
    url: string;
    message?: string;
    error?: string;
  }>('/home/status');
}

export async function getHomeRooms() {
  return fetchApi<{
    rooms: Room[];
  }>('/home/rooms');
}

export async function getHomeDevices(roomId?: string) {
  const params = roomId ? `?room_id=${roomId}` : '';
  return fetchApi<{
    devices: HomeDevice[];
  }>(`/home/devices${params}`);
}

export async function getHomeScenes() {
  return fetchApi<{
    scenes: HomeScene[];
  }>('/home/scenes');
}

export async function controlLight(entityId: string, action: 'on' | 'off' | 'toggle', brightness?: number) {
  return fetchApi<{ success: boolean }>('/home/light/control', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: entityId,
      action,
      brightness,
    }),
  });
}

export async function activateScene(entityId: string) {
  return fetchApi<{ success: boolean }>('/home/scene/activate', {
    method: 'POST',
    body: JSON.stringify({ entity_id: entityId }),
  });
}

export async function controlRoomLights(roomId: string, action: 'on' | 'off' | 'toggle') {
  return fetchApi<{
    room_id: string;
    action: string;
    controlled: Array<{ entity_id: string; success: boolean }>;
  }>(`/home/room/${roomId}/lights/${action}`, {
    method: 'POST',
  });
}

// ============= Logs API (Loki) =============

export interface LogEntry {
  timestamp: string;
  level: string;
  service: string;
  message: string;
  labels: Record<string, string>;
}

export async function getLogsHealth() {
  return fetchApi<{
    status: string;
    url: string;
    ready?: boolean;
    error?: string;
  }>('/logs/health');
}

export async function getLogsServices() {
  return fetchApi<{
    services: string[];
  }>('/logs/services');
}

export async function queryLogs(params: {
  service?: string;
  level?: string;
  search?: string;
  hours?: number;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params.service) searchParams.append('service', params.service);
  if (params.level) searchParams.append('level', params.level);
  if (params.search) searchParams.append('search', params.search);
  if (params.hours) searchParams.append('hours', params.hours.toString());
  if (params.limit) searchParams.append('limit', params.limit.toString());

  return fetchApi<{
    logs: LogEntry[];
    total: number;
    query: string;
    time_range: { start: string; end: string };
  }>(`/logs/query?${searchParams.toString()}`);
}

// ============= Unified Services API (Homepage Integration) =============

export interface UnifiedService {
  id: string;
  name: string;
  category: string;
  url: string;
  icon?: string;
  description?: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  latency_ms?: number;
  source: 'hydra' | 'homepage';
  node: string;
}

export interface UnifiedServicesResponse {
  services: UnifiedService[];
  categories: string[];
  counts: {
    total: number;
    healthy: number;
    unhealthy: number;
    unknown: number;
  };
  timestamp: string;
}

export async function getUnifiedServices() {
  return fetchApi<UnifiedServicesResponse>('/services/unified');
}

export async function getServiceCategories() {
  return fetchApi<{
    categories: Array<{
      name: string;
      count: number;
      healthy: number;
    }>;
    total_categories: number;
  }>('/services/categories');
}

export async function getServicesByCategory(category: string) {
  return fetchApi<{
    category: string;
    services: UnifiedService[];
    count: number;
  }>(`/services/by-category/${category}`);
}

export async function getServicesByNode(node: string) {
  return fetchApi<{
    node: string;
    services: UnifiedService[];
    count: number;
  }>(`/services/by-node/${node}`);
}

export async function getServicesHealthSummary() {
  return fetchApi<{
    homepage_services: number;
    monitored_services: number;
    healthy: number;
    unhealthy: number;
    unmonitored: number;
    health_percentage: number;
    timestamp: string;
  }>('/services/health-summary');
}

// SSE Stream for real-time service status updates
export interface ServiceStatusUpdate {
  type: 'status_update' | 'error';
  timestamp: string;
  summary?: {
    total: number;
    monitored: number;
    healthy: number;
    unhealthy: number;
    health_percentage: number;
  };
  services?: Record<string, {
    status: string;
    latency_ms: number | null;
  }>;
  message?: string;
}

export function createServicesEventSource(
  onUpdate: (data: ServiceStatusUpdate) => void,
  onError?: (error: Error) => void
): EventSource {
  const url = `${HYDRA_API_BASE}/services/stream`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as ServiceStatusUpdate;
      onUpdate(data);
    } catch (err) {
      console.error('Failed to parse SSE message:', err);
    }
  };

  eventSource.onerror = (event) => {
    console.error('SSE connection error:', event);
    onError?.(new Error('SSE connection failed'));
  };

  return eventSource;
}

// ============= Knowledge Ingestion API =============

export async function ingestUrl(url: string, collection?: string, metadata?: Record<string, string>) {
  return fetchApi<{
    document_id: string;
    chunks_created: number;
    status: string;
  }>('/ingest/url', {
    method: 'POST',
    body: JSON.stringify({ url, collection: collection || 'hydra_knowledge', metadata }),
  });
}

export async function ingestDocument(content: string, filename: string, collection?: string) {
  return fetchApi<{
    document_id: string;
    chunks_created: number;
    status: string;
  }>('/ingest/document', {
    method: 'POST',
    body: JSON.stringify({
      content,
      filename,
      collection: collection || 'hydra_knowledge',
    }),
  });
}

export async function getKnowledgeMetrics() {
  return fetchApi<{
    total_entries: number;
    entries_by_source: Record<string, number>;
    entries_by_category: Record<string, number>;
    stale_entries: number;
    redundant_entries: number;
    avg_relevance_score: number;
    total_size_mb: number;
    recommendations: string[];
  }>('/knowledge/metrics');
}

export async function getKnowledgeHealth() {
  return fetchApi<{
    status: string;
    qdrant: { connected: boolean; collections: number };
    meilisearch: { connected: boolean; indexes: number };
  }>('/knowledge/health');
}

export async function crawlUrl(url: string, maxPages?: number) {
  return fetchApi<{
    task_id: string;
    status: string;
    pages_found: number;
  }>('/research/crawl', {
    method: 'POST',
    body: JSON.stringify({ url, max_pages: maxPages || 10 }),
  });
}

export async function webSearch(query: string, numResults?: number) {
  return fetchApi<{
    results: Array<{
      title: string;
      url: string;
      snippet: string;
    }>;
    total: number;
  }>('/research/web', {
    method: 'POST',
    body: JSON.stringify({ query, num_results: numResults || 10 }),
  });
}

export default {
  getSystemHealth,
  getContainerHealth,
  getUnhealthyContainers,
  getAgentSchedulerStatus,
  getAgentQueue,
  scheduleAgentTask,
  getCrewsStatus,
  runMonitoringCrew,
  getMemoryStatus,
  searchMemory,
  getSelfImprovementStatus,
  runBenchmark,
  getInferenceStatus,
  getGpuStatus,
  getVoiceStatus,
  synthesizeSpeech,
  getKnowledgeCollections,
  getRecentAuditLogs,
  getRecentAlerts,
  createWebSocketConnection,
  ingestUrl,
  ingestDocument,
  getKnowledgeMetrics,
  crawlUrl,
  webSearch,
};
