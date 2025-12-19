import React, { useState, useEffect, useCallback } from 'react';
import { Card, Badge, Button, Tabs } from './UIComponents';
import {
  Bot, Zap, Code, Send, RefreshCw, Loader2,
  CheckCircle, XCircle, Clock, Server, Cpu
} from 'lucide-react';

interface OrchestratorAgent {
  id: string;
  name: string;
  type: string;
  model: string;
  endpoint: string | null;
  capabilities: string[];
  cost_tier: string;
  status: string;
}

interface AgentHealth {
  agents: Record<string, boolean>;
  any_available: boolean;
}

interface TaskResult {
  task_id: string;
  agent_id: string;
  status: string;
  output: string;
  files_modified: string[];
  execution_time_ms: number;
  tokens_used: number | null;
  error: string | null;
}

const API_BASE = 'http://192.168.1.244:8700';

export const CodingAgents: React.FC = () => {
  const [agents, setAgents] = useState<OrchestratorAgent[]>([]);
  const [health, setHealth] = useState<AgentHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [history, setHistory] = useState<TaskResult[]>([]);
  const [activeTab, setActiveTab] = useState('AGENTS');

  const fetchAgents = useCallback(async () => {
    try {
      const [agentsRes, healthRes] = await Promise.all([
        fetch(`${API_BASE}/agents/`),
        fetch(`${API_BASE}/agents/health`)
      ]);
      const agentsData = await agentsRes.json();
      const healthData = await healthRes.json();
      setAgents(agentsData.agents || []);
      setHealth(healthData);
    } catch (err) {
      console.error('Failed to fetch agents:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/history?limit=20`);
      const data = await res.json();
      setHistory(data.tasks || []);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
    fetchHistory();
  }, [fetchAgents, fetchHistory]);

  const executeTask = async () => {
    if (!prompt.trim() || !selectedAgent) return;

    setExecuting(true);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/agents/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt,
          prefer_agent: selectedAgent,
          prefer_local: true
        })
      });
      const data = await res.json();
      setResult(data);
      fetchHistory();
    } catch (err) {
      setResult({
        task_id: 'error',
        agent_id: selectedAgent,
        status: 'error',
        output: '',
        files_modified: [],
        execution_time_ms: 0,
        tokens_used: null,
        error: String(err)
      });
    } finally {
      setExecuting(false);
    }
  };

  const getStatusIcon = (status: string, isHealthy: boolean | undefined) => {
    if (!isHealthy) return <XCircle size={16} className="text-red-500" />;
    if (status === 'available') return <CheckCircle size={16} className="text-emerald-500" />;
    return <Clock size={16} className="text-amber-500" />;
  };

  const getCostBadge = (tier: string) => {
    const variants: Record<string, 'emerald' | 'cyan' | 'amber' | 'purple'> = {
      free: 'emerald',
      low: 'cyan',
      medium: 'amber',
      high: 'purple'
    };
    return <Badge variant={variants[tier] || 'neutral'}>{tier.toUpperCase()}</Badge>;
  };

  const tabs = [
    { id: 'AGENTS', label: 'Available Agents' },
    { id: 'EXECUTE', label: 'Execute Task' },
    { id: 'HISTORY', label: 'History' }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 size={32} className="animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-mono font-bold text-neutral-200">CODING_AGENTS</h3>
          <p className="text-sm text-neutral-500 font-mono">
            {health?.any_available ?
              `${Object.values(health.agents || {}).filter(Boolean).length} agents online` :
              'No agents available'}
          </p>
        </div>
        <Button
          variant="secondary"
          icon={<RefreshCw size={16} />}
          onClick={fetchAgents}
        >
          Refresh
        </Button>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {/* Agents List */}
      {activeTab === 'AGENTS' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((agent) => {
            const isHealthy = health?.agents?.[agent.id];
            return (
              <Card
                key={agent.id}
                className={`cursor-pointer transition-all ${
                  selectedAgent === agent.id ? 'border-emerald-500' : 'hover:border-neutral-700'
                }`}
              >
                <div
                  className="p-4"
                  onClick={() => setSelectedAgent(agent.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${
                        isHealthy ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                      }`}>
                        {agent.type === 'aider' ? <Code size={20} /> : <Cpu size={20} />}
                      </div>
                      <div>
                        <h4 className="font-bold text-neutral-200">{agent.name}</h4>
                        <p className="text-xs text-neutral-500 font-mono mt-0.5">
                          {agent.model.length > 35 ? agent.model.substring(0, 35) + '...' : agent.model}
                        </p>
                      </div>
                    </div>
                    {getStatusIcon(agent.status, isHealthy)}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {getCostBadge(agent.cost_tier)}
                    <Badge variant="purple">{agent.type}</Badge>
                    {agent.capabilities.includes('uncensored') && (
                      <Badge variant="amber">UNCENSORED</Badge>
                    )}
                  </div>

                  {agent.endpoint && (
                    <div className="mt-3 flex items-center gap-2 text-xs text-neutral-500">
                      <Server size={12} />
                      <span className="font-mono">{agent.endpoint}</span>
                    </div>
                  )}

                  <div className="mt-3 flex flex-wrap gap-1">
                    {agent.capabilities.slice(0, 4).map((cap) => (
                      <span key={cap} className="text-xs bg-neutral-800 px-2 py-0.5 rounded text-neutral-400">
                        {cap.replace('_', ' ')}
                      </span>
                    ))}
                    {agent.capabilities.length > 4 && (
                      <span className="text-xs text-neutral-500">+{agent.capabilities.length - 4}</span>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Execute Tab */}
      {activeTab === 'EXECUTE' && (
        <div className="space-y-4">
          {/* Agent Selection */}
          <Card>
            <div className="p-4">
              <label className="text-sm text-neutral-400 font-mono block mb-2">SELECT AGENT</label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {agents.filter(a => health?.agents?.[a.id]).map((agent) => (
                  <button
                    key={agent.id}
                    onClick={() => setSelectedAgent(agent.id)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      selectedAgent === agent.id
                        ? 'border-emerald-500 bg-emerald-500/10'
                        : 'border-neutral-700 hover:border-neutral-600'
                    }`}
                  >
                    <div className="font-mono text-sm text-neutral-200">{agent.name}</div>
                    <div className="text-xs text-neutral-500 mt-1 truncate">{agent.model}</div>
                  </button>
                ))}
              </div>
            </div>
          </Card>

          {/* Prompt Input */}
          <Card>
            <div className="p-4">
              <label className="text-sm text-neutral-400 font-mono block mb-2">PROMPT</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Write a Python function to..."
                className="w-full h-32 bg-neutral-900 border border-neutral-700 rounded-lg p-3 text-neutral-200 font-mono text-sm resize-none focus:border-emerald-500 focus:outline-none"
              />
              <div className="mt-3 flex justify-end">
                <Button
                  variant="primary"
                  icon={executing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                  onClick={executeTask}
                  disabled={!prompt.trim() || !selectedAgent || executing}
                >
                  {executing ? 'Executing...' : 'Execute'}
                </Button>
              </div>
            </div>
          </Card>

          {/* Result */}
          {result && (
            <Card className={result.status === 'success' ? 'border-emerald-500/30' : 'border-red-500/30'}>
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {result.status === 'success' ? (
                      <CheckCircle size={18} className="text-emerald-500" />
                    ) : (
                      <XCircle size={18} className="text-red-500" />
                    )}
                    <span className="font-mono text-sm text-neutral-400">
                      {result.agent_id} • {result.execution_time_ms}ms
                    </span>
                    {result.tokens_used && (
                      <Badge variant="neutral">{result.tokens_used} tokens</Badge>
                    )}
                  </div>
                </div>

                {result.error ? (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                    <pre className="text-sm text-red-400 font-mono whitespace-pre-wrap">{result.error}</pre>
                  </div>
                ) : (
                  <div className="bg-neutral-900 border border-neutral-700 rounded-lg p-3 max-h-96 overflow-y-auto">
                    <pre className="text-sm text-neutral-200 font-mono whitespace-pre-wrap">{result.output}</pre>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'HISTORY' && (
        <div className="space-y-3">
          {history.length === 0 ? (
            <Card>
              <div className="p-8 text-center text-neutral-500">
                No execution history yet
              </div>
            </Card>
          ) : (
            history.map((task) => (
              <Card key={task.task_id}>
                <div className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {task.status === 'success' ? (
                      <CheckCircle size={18} className="text-emerald-500" />
                    ) : (
                      <XCircle size={18} className="text-red-500" />
                    )}
                    <div>
                      <p className="font-mono text-sm text-neutral-200">{task.agent_id}</p>
                      <p className="text-xs text-neutral-500">{task.task_id.substring(0, 8)}...</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm text-neutral-400">{task.execution_time_ms}ms</p>
                    <Badge variant={task.status === 'success' ? 'emerald' : 'red'}>{task.status}</Badge>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default CodingAgents;
