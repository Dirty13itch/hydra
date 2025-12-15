'use client';

import { useState, useEffect, useCallback } from 'react';

interface AgentInstance {
  id: string;
  name: string;
  type: 'letta' | 'crewai' | 'langgraph' | 'autogen';
  status: 'active' | 'idle' | 'working' | 'error' | 'offline';
  currentTask?: string;
  memory: {
    blocks: number;
    lastAccess: string;
  };
  stats: {
    tasksCompleted: number;
    successRate: number;
    avgLatency: number;
  };
}

interface CrewInstance {
  id: string;
  name: string;
  status: 'running' | 'idle' | 'completed' | 'error';
  agents: string[];
  currentTask?: string;
  progress?: number;
}

interface OrchestrationStatus {
  agents: AgentInstance[];
  crews: CrewInstance[];
  routingStats: {
    totalRequests: number;
    avgRoutingTime: number;
    modelDistribution: { [model: string]: number };
  };
}

const MOCK_STATUS: OrchestrationStatus = {
  agents: [
    {
      id: 'a1',
      name: 'hydra-steward',
      type: 'letta',
      status: 'active',
      currentTask: 'Monitoring cluster health',
      memory: { blocks: 5, lastAccess: '2m ago' },
      stats: { tasksCompleted: 234, successRate: 0.94, avgLatency: 1.2 },
    },
    {
      id: 'a2',
      name: 'research-assistant',
      type: 'letta',
      status: 'idle',
      memory: { blocks: 3, lastAccess: '15m ago' },
      stats: { tasksCompleted: 45, successRate: 0.91, avgLatency: 2.8 },
    },
    {
      id: 'a3',
      name: 'code-reviewer',
      type: 'langgraph',
      status: 'working',
      currentTask: 'Reviewing PR #127',
      memory: { blocks: 2, lastAccess: '1m ago' },
      stats: { tasksCompleted: 89, successRate: 0.97, avgLatency: 4.5 },
    },
  ],
  crews: [
    {
      id: 'c1',
      name: 'Research Crew',
      status: 'idle',
      agents: ['Market Analyst', 'Tech Researcher', 'Report Writer'],
    },
    {
      id: 'c2',
      name: 'Maintenance Crew',
      status: 'running',
      agents: ['System Monitor', 'Optimizer', 'Documenter'],
      currentTask: 'Weekly optimization scan',
      progress: 65,
    },
  ],
  routingStats: {
    totalRequests: 1247,
    avgRoutingTime: 45,
    modelDistribution: {
      'Llama-3.3-70B': 456,
      'Mistral-Nemo-12B': 523,
      'Codestral-22B': 189,
      'Qwen2.5-7B': 79,
    },
  },
};

interface AgentOrchestrationPanelProps {
  compact?: boolean;
}

export function AgentOrchestrationPanel({ compact = false }: AgentOrchestrationPanelProps) {
  const [status, setStatus] = useState<OrchestrationStatus>(MOCK_STATUS);
  const [activeTab, setActiveTab] = useState<'agents' | 'crews' | 'routing'>('agents');

  const getStatusColor = (s: AgentInstance['status'] | CrewInstance['status']) => {
    switch (s) {
      case 'active':
      case 'running':
        return 'var(--hydra-green)';
      case 'working':
        return 'var(--hydra-cyan)';
      case 'idle':
        return 'var(--hydra-yellow)';
      case 'completed':
        return 'var(--hydra-purple)';
      case 'error':
        return 'var(--hydra-red)';
      case 'offline':
        return 'var(--hydra-text-muted)';
      default:
        return 'var(--hydra-text-muted)';
    }
  };

  const getStatusBg = (s: AgentInstance['status'] | CrewInstance['status']) => {
    switch (s) {
      case 'active':
      case 'running':
        return 'rgba(0, 255, 136, 0.1)';
      case 'working':
        return 'rgba(0, 255, 255, 0.1)';
      case 'idle':
        return 'rgba(255, 204, 0, 0.1)';
      case 'completed':
        return 'rgba(139, 92, 246, 0.1)';
      case 'error':
        return 'rgba(255, 51, 102, 0.1)';
      case 'offline':
        return 'rgba(136, 136, 136, 0.1)';
      default:
        return 'rgba(136, 136, 136, 0.1)';
    }
  };

  const getTypeIcon = (type: AgentInstance['type']) => {
    switch (type) {
      case 'letta':
        return '🧠';
      case 'crewai':
        return '👥';
      case 'langgraph':
        return '🔗';
      case 'autogen':
        return '🤖';
    }
  };

  if (compact) {
    const activeAgents = status.agents.filter((a) => a.status === 'active' || a.status === 'working').length;
    const runningCrews = status.crews.filter((c) => c.status === 'running').length;

    return (
      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-2 px-2 py-1 rounded text-xs"
          style={{
            backgroundColor: 'rgba(6, 182, 212, 0.1)',
            border: '1px solid var(--hydra-cyan)',
          }}
        >
          <span>🤖</span>
          <span style={{ color: 'var(--hydra-cyan)' }}>
            {activeAgents}/{status.agents.length} agents
          </span>
        </div>
        {runningCrews > 0 && (
          <span className="text-xs" style={{ color: 'var(--hydra-green)' }}>
            {runningCrews} crew{runningCrews > 1 ? 's' : ''} active
          </span>
        )}
      </div>
    );
  }

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: 'var(--hydra-bg)',
        borderColor: 'var(--hydra-border)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--hydra-border)' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">🤖</span>
          <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
            Agent Orchestration
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              backgroundColor: 'rgba(6, 182, 212, 0.1)',
              color: 'var(--hydra-cyan)',
            }}
          >
            Layer 5
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span style={{ color: 'var(--hydra-green)' }}>
            {status.agents.filter((a) => a.status !== 'offline').length} online
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b" style={{ borderColor: 'var(--hydra-border)' }}>
        {(['agents', 'crews', 'routing'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="flex-1 px-3 py-2 text-xs font-medium transition-colors"
            style={{
              backgroundColor: activeTab === tab ? 'rgba(6, 182, 212, 0.1)' : 'transparent',
              color: activeTab === tab ? 'var(--hydra-cyan)' : 'var(--hydra-text-muted)',
              borderBottom: activeTab === tab ? '2px solid var(--hydra-cyan)' : 'none',
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
        {activeTab === 'agents' && (
          <>
            {status.agents.map((agent) => (
              <div
                key={agent.id}
                className="p-3 rounded-lg border"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderColor: 'var(--hydra-border)',
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{getTypeIcon(agent.type)}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                          {agent.name}
                        </span>
                        <span
                          className="text-xs px-1.5 py-0.5 rounded uppercase"
                          style={{
                            backgroundColor: getStatusBg(agent.status),
                            color: getStatusColor(agent.status),
                          }}
                        >
                          {agent.status}
                        </span>
                      </div>
                      <div className="text-xs mt-0.5" style={{ color: 'var(--hydra-text-muted)' }}>
                        {agent.type} • {agent.memory.blocks} memory blocks
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs" style={{ color: 'var(--hydra-green)' }}>
                      {Math.round(agent.stats.successRate * 100)}% success
                    </div>
                    <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                      {agent.stats.tasksCompleted} tasks
                    </div>
                  </div>
                </div>
                {agent.currentTask && (
                  <div
                    className="mt-2 px-2 py-1 rounded text-xs"
                    style={{ backgroundColor: 'rgba(0, 255, 255, 0.05)' }}
                  >
                    <span style={{ color: 'var(--hydra-text-muted)' }}>Task: </span>
                    <span style={{ color: 'var(--hydra-cyan)' }}>{agent.currentTask}</span>
                  </div>
                )}
              </div>
            ))}
          </>
        )}

        {activeTab === 'crews' && (
          <>
            {status.crews.map((crew) => (
              <div
                key={crew.id}
                className="p-3 rounded-lg border"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderColor: 'var(--hydra-border)',
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">👥</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                          {crew.name}
                        </span>
                        <span
                          className="text-xs px-1.5 py-0.5 rounded uppercase"
                          style={{
                            backgroundColor: getStatusBg(crew.status),
                            color: getStatusColor(crew.status),
                          }}
                        >
                          {crew.status}
                        </span>
                      </div>
                      <div className="text-xs mt-0.5" style={{ color: 'var(--hydra-text-muted)' }}>
                        {crew.agents.length} agents: {crew.agents.join(', ')}
                      </div>
                    </div>
                  </div>
                </div>
                {crew.currentTask && (
                  <div className="mt-2">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span style={{ color: 'var(--hydra-text-muted)' }}>{crew.currentTask}</span>
                      <span style={{ color: 'var(--hydra-cyan)' }}>{crew.progress}%</span>
                    </div>
                    <div
                      className="h-1.5 rounded-full overflow-hidden"
                      style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
                    >
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${crew.progress}%`,
                          backgroundColor: 'var(--hydra-cyan)',
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
            <button
              className="w-full p-2 rounded border text-sm transition-colors"
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                borderColor: 'var(--hydra-border)',
                color: 'var(--hydra-text-muted)',
              }}
            >
              + Create New Crew
            </button>
          </>
        )}

        {activeTab === 'routing' && (
          <div className="space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-2 gap-3">
              <div
                className="p-3 rounded text-center"
                style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
              >
                <div className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
                  {status.routingStats.totalRequests.toLocaleString()}
                </div>
                <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  Total Requests
                </div>
              </div>
              <div
                className="p-3 rounded text-center"
                style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
              >
                <div className="text-lg font-bold" style={{ color: 'var(--hydra-green)' }}>
                  {status.routingStats.avgRoutingTime}ms
                </div>
                <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  Avg Routing Time
                </div>
              </div>
            </div>

            {/* Model Distribution */}
            <div>
              <div className="text-xs font-medium mb-2" style={{ color: 'var(--hydra-text-muted)' }}>
                Model Distribution
              </div>
              <div className="space-y-2">
                {Object.entries(status.routingStats.modelDistribution).map(([model, count]) => {
                  const total = Object.values(status.routingStats.modelDistribution).reduce(
                    (a, b) => a + b,
                    0
                  );
                  const percentage = Math.round((count / total) * 100);
                  return (
                    <div key={model}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span style={{ color: 'var(--hydra-text)' }}>{model}</span>
                        <span style={{ color: 'var(--hydra-text-muted)' }}>
                          {count} ({percentage}%)
                        </span>
                      </div>
                      <div
                        className="h-1.5 rounded-full overflow-hidden"
                        style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }}
                      >
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${percentage}%`,
                            backgroundColor: 'var(--hydra-purple)',
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
