import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { Agent, AgentConfig, LogEntry, ActionHistoryEntry } from '../types';
import { useNotifications } from './NotificationContext';
import {
  getDashboardAgents,
  updateDashboardAgent,
  updateAgentConfig as apiUpdateAgentConfig,
  createDashboardWebSocket,
  addAgentThinkingStep as apiAddThinkingStep
} from '../services/hydraApi';

// Generate realistic mock action history based on agent type
const generateMockActionHistory = (agentName: string, agentType: string): ActionHistoryEntry[] => {
  const now = Date.now();
  const hour = 60 * 60 * 1000;

  const actionTemplates: Record<string, ActionHistoryEntry[]> = {
    research: [
      { id: '1', action: 'web_search', description: 'Searched for latest AI architecture papers', timestamp: new Date(now - 2 * hour).toISOString(), duration: '12.3s', status: 'success', tokensUsed: 1247, toolsUsed: ['web_search', 'pdf_parser'] },
      { id: '2', action: 'document_analysis', description: 'Analyzed 15 research papers on transformer optimization', timestamp: new Date(now - 5 * hour).toISOString(), duration: '45.2s', status: 'success', tokensUsed: 8934, toolsUsed: ['pdf_parser', 'summarizer'] },
      { id: '3', action: 'knowledge_indexing', description: 'Indexed findings to Qdrant knowledge base', timestamp: new Date(now - 6 * hour).toISOString(), duration: '8.7s', status: 'success', tokensUsed: 2156, toolsUsed: ['qdrant_insert'] },
      { id: '4', action: 'report_generation', description: 'Generated synthesis report on attention mechanisms', timestamp: new Date(now - 8 * hour).toISOString(), duration: '23.1s', status: 'success', tokensUsed: 4521, toolsUsed: ['markdown_writer'] },
      { id: '5', action: 'citation_fetch', description: 'Failed to fetch citation metadata from arxiv', timestamp: new Date(now - 12 * hour).toISOString(), duration: '30.0s', status: 'failed', tokensUsed: 890, toolsUsed: ['arxiv_api'], output: 'Timeout: arxiv API unresponsive' },
    ],
    coding: [
      { id: '1', action: 'code_generation', description: 'Generated WebSocket handler for real-time updates', timestamp: new Date(now - 1 * hour).toISOString(), duration: '8.4s', status: 'success', tokensUsed: 3421, toolsUsed: ['code_writer', 'typescript_checker'] },
      { id: '2', action: 'bug_fix', description: 'Fixed CORS configuration in API middleware', timestamp: new Date(now - 3 * hour).toISOString(), duration: '15.2s', status: 'success', tokensUsed: 2134, toolsUsed: ['code_reader', 'code_writer'] },
      { id: '3', action: 'test_generation', description: 'Generated unit tests for authentication module', timestamp: new Date(now - 4 * hour).toISOString(), duration: '22.8s', status: 'success', tokensUsed: 5678, toolsUsed: ['code_writer', 'jest_runner'] },
      { id: '4', action: 'refactoring', description: 'Refactored dashboard API endpoints', timestamp: new Date(now - 7 * hour).toISOString(), duration: '34.1s', status: 'success', tokensUsed: 7234, toolsUsed: ['code_reader', 'code_writer', 'git_commit'] },
      { id: '5', action: 'dependency_update', description: 'Updated React dependencies to v19', timestamp: new Date(now - 10 * hour).toISOString(), duration: '18.5s', status: 'partial', tokensUsed: 1890, toolsUsed: ['npm_audit', 'package_updater'], output: '2 peer dependency warnings' },
    ],
    creative: [
      { id: '1', action: 'image_generation', description: 'Generated character portrait for Queen Morrigan', timestamp: new Date(now - 30 * 60000).toISOString(), duration: '45.2s', status: 'success', tokensUsed: 1200, toolsUsed: ['imagen', 'image_upscaler'] },
      { id: '2', action: 'dialogue_writing', description: 'Wrote Act 2 confrontation dialogue', timestamp: new Date(now - 2 * hour).toISOString(), duration: '28.7s', status: 'success', tokensUsed: 4567, toolsUsed: ['dialogue_generator', 'tone_checker'] },
      { id: '3', action: 'scene_composition', description: 'Composed throne room background art', timestamp: new Date(now - 4 * hour).toISOString(), duration: '67.3s', status: 'success', tokensUsed: 2890, toolsUsed: ['imagen', 'layer_composer'] },
      { id: '4', action: 'voice_synthesis', description: 'Synthesized voice samples for 3 characters', timestamp: new Date(now - 6 * hour).toISOString(), duration: '38.9s', status: 'success', tokensUsed: 980, toolsUsed: ['kokoro_tts'] },
      { id: '5', action: 'relationship_mapping', description: 'Updated character relationship graph', timestamp: new Date(now - 9 * hour).toISOString(), duration: '12.4s', status: 'success', tokensUsed: 1567, toolsUsed: ['graph_editor'] },
    ],
    coordinator: [
      { id: '1', action: 'task_delegation', description: 'Assigned 5 subtasks to specialist agents', timestamp: new Date(now - 45 * 60000).toISOString(), duration: '5.2s', status: 'success', tokensUsed: 890, toolsUsed: ['scheduler', 'agent_messenger'] },
      { id: '2', action: 'progress_check', description: 'Collected status from 4 active agents', timestamp: new Date(now - 2 * hour).toISOString(), duration: '8.3s', status: 'success', tokensUsed: 1234, toolsUsed: ['status_aggregator'] },
      { id: '3', action: 'conflict_resolution', description: 'Resolved resource contention between coding agents', timestamp: new Date(now - 4 * hour).toISOString(), duration: '15.7s', status: 'success', tokensUsed: 2341, toolsUsed: ['resource_manager', 'agent_messenger'] },
      { id: '4', action: 'priority_rebalancing', description: 'Rebalanced task priorities based on deadlines', timestamp: new Date(now - 6 * hour).toISOString(), duration: '11.2s', status: 'success', tokensUsed: 1678, toolsUsed: ['priority_queue', 'scheduler'] },
      { id: '5', action: 'report_compilation', description: 'Compiled daily progress report', timestamp: new Date(now - 24 * hour).toISOString(), duration: '19.8s', status: 'success', tokensUsed: 3456, toolsUsed: ['report_generator', 'metrics_collector'] },
    ],
  };

  return actionTemplates[agentType] || actionTemplates.research;
};

// Extended Agent type with thinking stream
interface ThinkingStep {
  step_id: string;
  timestamp: string;
  content: string;
  step_type: string;
}

interface ExtendedAgent extends Agent {
  thinkingStream?: ThinkingStep[];
  lastActivity?: string;
}

interface AgentContextType {
  agents: ExtendedAgent[];
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
  getAgent: (id: string) => ExtendedAgent | undefined;
  updateAgentStatus: (id: string, status: Agent['status']) => void;
  updateAgentTask: (id: string, task: string, progress: number) => void;
  updateAgentConfig: (id: string, updates: Partial<Agent> & { config?: Partial<AgentConfig> }) => void;
  stopAgent: (id: string) => void;
  addThinkingStep: (agentId: string, content: string, stepType?: string) => void;
  refreshAgents: () => Promise<void>;
}

const AgentContext = createContext<AgentContextType | undefined>(undefined);

export const AgentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [agents, setAgents] = useState<ExtendedAgent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { addNotification } = useNotifications();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Transform API response to match UI types
  const transformAgent = (apiAgent: any): ExtendedAgent => ({
    id: apiAgent.id,
    name: apiAgent.name,
    type: apiAgent.type as Agent['type'],
    status: apiAgent.status as Agent['status'],
    model: apiAgent.model,
    task: apiAgent.task,
    progress: apiAgent.progress,
    uptime: apiAgent.uptime,
    tools: apiAgent.tools || [],
    dependencies: apiAgent.dependencies || [],
    config: apiAgent.config ? {
      temperature: apiAgent.config.temperature,
      topP: apiAgent.config.top_p,
      topK: apiAgent.config.top_k,
      maxOutputTokens: apiAgent.config.max_output_tokens,
      systemInstruction: apiAgent.config.system_instruction,
      promptHistory: [],
    } : undefined,
    thinkingStream: apiAgent.thinkingStream || [],
    lastActivity: apiAgent.lastActivity,
    actionHistory: apiAgent.actionHistory || generateMockActionHistory(apiAgent.name, apiAgent.type),
  });

  // Fetch agents from API
  const fetchAgents = useCallback(async () => {
    try {
      setIsLoading(true);
      const result = await getDashboardAgents();

      if (result.error) {
        setError(result.error);
        addNotification('error', 'Connection Error', 'Failed to fetch agents from API');
      } else if (result.data) {
        setAgents(result.data.agents.map(transformAgent));
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [addNotification]);

  // Connect WebSocket for real-time updates
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    wsRef.current = createDashboardWebSocket(
      (type, data) => {
        if (type === 'agent_update') {
          const updatedAgent = transformAgent(data);
          setAgents(prev => prev.map(a => a.id === updatedAgent.id ? updatedAgent : a));
        } else if (type === 'thinking_step') {
          const { agentId, step } = data as { agentId: string; step: ThinkingStep };
          setAgents(prev => prev.map(a => {
            if (a.id !== agentId) return a;
            const newStream = [...(a.thinkingStream || []), step].slice(-50);
            return { ...a, thinkingStream: newStream };
          }));
        }
      },
      () => {
        setIsConnected(true);
        addNotification('success', 'Connected', 'Real-time updates enabled');
      },
      () => {
        setIsConnected(false);
        // Auto-reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
      }
    );
  }, [addNotification]);

  // Initial load and WebSocket connection
  useEffect(() => {
    fetchAgents();
    connectWebSocket();

    return () => {
      wsRef.current?.close();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [fetchAgents, connectWebSocket]);

  // Polling fallback if WebSocket disconnects
  useEffect(() => {
    if (!isConnected) {
      const interval = setInterval(fetchAgents, 10000); // Poll every 10s when disconnected
      return () => clearInterval(interval);
    }
  }, [isConnected, fetchAgents]);

  const getAgent = useCallback((id: string) => {
    return agents.find(a => a.id === id);
  }, [agents]);

  const updateAgentStatus = useCallback(async (id: string, status: Agent['status']) => {
    // Optimistic update
    setAgents(prev => prev.map(a => {
      if (a.id !== id) return a;
      if (status === 'paused' && a.status === 'active') {
        addNotification('warning', 'Agent Paused', `${a.name} execution suspended.`);
      } else if (status === 'active' && a.status === 'paused') {
        addNotification('success', 'Agent Resumed', `${a.name} execution resumed.`);
      }
      return { ...a, status };
    }));

    // Send to API
    const result = await updateDashboardAgent(id, { status });
    if (result.error) {
      addNotification('error', 'Update Failed', result.error);
      fetchAgents(); // Revert on error
    }
  }, [addNotification, fetchAgents]);

  const updateAgentTask = useCallback(async (id: string, task: string, progress: number) => {
    setAgents(prev => prev.map(a => a.id === id ? { ...a, task, progress } : a));

    const result = await updateDashboardAgent(id, { task, progress });
    if (result.error) {
      fetchAgents();
    }
  }, [fetchAgents]);

  const updateAgentConfig = useCallback(async (id: string, updates: any) => {
    // Optimistic update
    setAgents(prev => prev.map(a => {
      if (a.id !== id) return a;

      let newConfig = { ...a.config! };

      if (updates.config) {
        newConfig = { ...newConfig, ...updates.config };
      }

      if (updates.temperature !== undefined) newConfig.temperature = updates.temperature;
      if (updates.topP !== undefined) newConfig.topP = updates.topP;
      if (updates.topK !== undefined) newConfig.topK = updates.topK;
      if (updates.maxOutputTokens !== undefined) newConfig.maxOutputTokens = updates.maxOutputTokens;
      if (updates.systemInstruction !== undefined) newConfig.systemInstruction = updates.systemInstruction;

      const { config, temperature, topP, topK, maxOutputTokens, systemInstruction, promptHistory, ...agentUpdates } = updates;

      return { ...a, ...agentUpdates, config: newConfig };
    }));

    // Send to API for persistence
    const apiConfig: Record<string, unknown> = {};
    if (updates.temperature !== undefined) apiConfig.temperature = updates.temperature;
    if (updates.topP !== undefined) apiConfig.top_p = updates.topP;
    if (updates.topK !== undefined) apiConfig.top_k = updates.topK;
    if (updates.maxOutputTokens !== undefined) apiConfig.max_output_tokens = updates.maxOutputTokens;
    if (updates.systemInstruction !== undefined) apiConfig.system_instruction = updates.systemInstruction;
    if (updates.config) {
      if (updates.config.temperature !== undefined) apiConfig.temperature = updates.config.temperature;
      if (updates.config.topP !== undefined) apiConfig.top_p = updates.config.topP;
      if (updates.config.topK !== undefined) apiConfig.top_k = updates.config.topK;
      if (updates.config.maxOutputTokens !== undefined) apiConfig.max_output_tokens = updates.config.maxOutputTokens;
      if (updates.config.systemInstruction !== undefined) apiConfig.system_instruction = updates.config.systemInstruction;
    }

    if (Object.keys(apiConfig).length > 0) {
      const result = await apiUpdateAgentConfig(id, apiConfig as Parameters<typeof apiUpdateAgentConfig>[1]);
      if (result.error) {
        addNotification('error', 'Config Save Failed', result.error);
        fetchAgents(); // Revert on error
        return;
      }
    }

    addNotification('info', 'Configuration Saved', 'Agent parameters persisted to backend.');
  }, [addNotification, fetchAgents]);

  const stopAgent = useCallback(async (id: string) => {
    const agent = agents.find(a => a.id === id);
    if (agent) {
      addNotification('error', 'Agent Stopped', `Connection to ${agent.name} terminated.`);
    }

    setAgents(prev => prev.map(a => {
      if (a.id !== id) return a;
      return { ...a, status: 'idle', progress: 0, task: 'Awaiting assignment' };
    }));

    await updateDashboardAgent(id, { status: 'idle', progress: 0, task: 'Awaiting assignment' });
  }, [agents, addNotification]);

  const addThinkingStep = useCallback(async (agentId: string, content: string, stepType = 'reasoning') => {
    // Optimistic update
    const step: ThinkingStep = {
      step_id: Math.random().toString(36).substr(2, 8),
      timestamp: new Date().toISOString(),
      content,
      step_type: stepType,
    };

    setAgents(prev => prev.map(a => {
      if (a.id !== agentId) return a;
      const newStream = [...(a.thinkingStream || []), step].slice(-50);
      return { ...a, thinkingStream: newStream };
    }));

    // Send to API
    await apiAddThinkingStep(agentId, content, stepType);
  }, []);

  const refreshAgents = useCallback(async () => {
    await fetchAgents();
  }, [fetchAgents]);

  return (
    <AgentContext.Provider value={{
      agents,
      isLoading,
      error,
      isConnected,
      getAgent,
      updateAgentStatus,
      updateAgentTask,
      updateAgentConfig,
      stopAgent,
      addThinkingStep,
      refreshAgents,
    }}>
      {children}
    </AgentContext.Provider>
  );
};

export const useAgents = () => {
  const context = useContext(AgentContext);
  if (context === undefined) {
    throw new Error('useAgents must be used within an AgentProvider');
  }
  return context;
};
