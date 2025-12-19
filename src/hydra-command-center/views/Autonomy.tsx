import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Tabs, Badge, ProgressBar } from '../components/UIComponents';
import {
  Brain,
  Cpu,
  Database,
  Activity,
  Play,
  Square,
  RefreshCw,
  Loader2,
  Zap,
  Target,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Layers,
  GitBranch,
  BarChart3,
  Sparkles,
  Shield,
  ListTodo
} from 'lucide-react';

const API_BASE = 'http://192.168.1.244:8700';

interface CognitiveStatus {
  running: boolean;
  session_id: string;
  state: string;
  step_number: number;
  model: string;
  loop_interval_seconds: number;
  stats: {
    started_at: string | null;
    cycles_completed: number;
    actions_executed: number;
    actions_succeeded: number;
    actions_failed: number;
    learnings_stored: number;
    errors: number;
    last_cycle_at: string | null;
    last_action_at: string | null;
  };
  current_observation_age_seconds: number | null;
  has_current_plan: boolean;
}

interface DGMStatus {
  running: boolean;
  state: {
    session_id: string;
    started_at: string;
    last_benchmark_at: string | null;
    last_improvement_cycle_at: string | null;
    baseline_scores: Record<string, number>;
    current_scores: Record<string, number>;
    improvements_deployed: number;
    improvements_rolled_back: number;
    total_cycles: number;
  };
  improvements_history_count: number;
  benchmarks_history_count: number;
  config: {
    benchmark_interval_hours: number;
    improvement_cycle_hours: number;
    max_changes_per_cycle: number;
  };
}

interface MemoryStats {
  tier_counts: Record<string, number>;
  total_memories: number;
  storage_backend: string;
  qdrant: {
    collection: string;
    points_count: number;
    status: string;
    embedding_model: string;
    embedding_dimension: number;
  };
}

interface DiagnosisHealth {
  status: string;
  health_score: number;
  recent_failures: number;
  trend: string;
}

interface AgentSchedulerStatus {
  status: string;
  stats: {
    total_scheduled: number;
    total_completed: number;
    total_failed: number;
    queue_size: number;
    running: number;
    max_concurrent: number;
    policy: string;
  };
}

export const Autonomy: React.FC = () => {
  const [activeTab, setActiveTab] = useState('OVERVIEW');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // State for each subsystem
  const [cognitiveStatus, setCognitiveStatus] = useState<CognitiveStatus | null>(null);
  const [dgmStatus, setDgmStatus] = useState<DGMStatus | null>(null);
  const [memoryStats, setMemoryStats] = useState<MemoryStats | null>(null);
  const [diagnosisHealth, setDiagnosisHealth] = useState<DiagnosisHealth | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<AgentSchedulerStatus | null>(null);

  // Action states
  const [startingCognitive, setStartingCognitive] = useState(false);
  const [stoppingCognitive, setStoppingCognitive] = useState(false);
  const [startingDGM, setStartingDGM] = useState(false);
  const [stoppingDGM, setStoppingDGM] = useState(false);
  const [runningBenchmark, setRunningBenchmark] = useState(false);

  const tabs = [
    { id: 'OVERVIEW', label: 'Overview' },
    { id: 'COGNITIVE', label: 'Cognitive Core' },
    { id: 'DGM', label: 'Self-Improvement' },
    { id: 'MEMORY', label: 'Memory System' },
    { id: 'SCHEDULER', label: 'Agent Scheduler' }
  ];

  const fetchAll = useCallback(async () => {
    try {
      const [cognitive, dgm, memory, diagnosis, scheduler] = await Promise.all([
        fetch(`${API_BASE}/cognitive/status`).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/dgm/status`).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/memory/stats`).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/diagnosis/health`).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/agent-scheduler/status`).then(r => r.ok ? r.json() : null),
      ]);

      setCognitiveStatus(cognitive);
      setDgmStatus(dgm);
      setMemoryStats(memory);
      setDiagnosisHealth(diagnosis);
      setSchedulerStatus(scheduler);
    } catch (error) {
      console.error('Failed to fetch autonomy data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAll();
  };

  const handleStartCognitive = async () => {
    setStartingCognitive(true);
    try {
      await fetch(`${API_BASE}/cognitive/start`, { method: 'POST' });
      await fetchAll();
    } catch (error) {
      console.error('Failed to start cognitive core:', error);
    } finally {
      setStartingCognitive(false);
    }
  };

  const handleStopCognitive = async () => {
    setStoppingCognitive(true);
    try {
      await fetch(`${API_BASE}/cognitive/stop`, { method: 'POST' });
      await fetchAll();
    } catch (error) {
      console.error('Failed to stop cognitive core:', error);
    } finally {
      setStoppingCognitive(false);
    }
  };

  const handleStartDGM = async () => {
    setStartingDGM(true);
    try {
      await fetch(`${API_BASE}/dgm/start`, { method: 'POST' });
      await fetchAll();
    } catch (error) {
      console.error('Failed to start DGM:', error);
    } finally {
      setStartingDGM(false);
    }
  };

  const handleStopDGM = async () => {
    setStoppingDGM(true);
    try {
      await fetch(`${API_BASE}/dgm/stop`, { method: 'POST' });
      await fetchAll();
    } catch (error) {
      console.error('Failed to stop DGM:', error);
    } finally {
      setStoppingDGM(false);
    }
  };

  const handleRunBenchmark = async () => {
    setRunningBenchmark(true);
    try {
      await fetch(`${API_BASE}/benchmark/run`, { method: 'POST' });
      await fetchAll();
    } catch (error) {
      console.error('Failed to run benchmark:', error);
    } finally {
      setRunningBenchmark(false);
    }
  };

  const getStatusColor = (running: boolean) => running ? 'emerald' : 'neutral';
  const getHealthColor = (score: number) => {
    if (score >= 90) return 'emerald';
    if (score >= 70) return 'amber';
    return 'red';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface-base">
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-cyan-500">AUTONOMY</span> // AI SELF-MANAGEMENT
          </h2>
          <Tabs
            tabs={tabs}
            activeTab={activeTab}
            onChange={setActiveTab}
            className="mt-4"
            variant="emerald"
          />
        </div>
        <div className="pb-2 flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={refreshing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'OVERVIEW' && (
          <div className="space-y-6">
            {/* Status Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* Cognitive Core */}
              <Card className="border-neutral-800">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`p-2 rounded-lg ${cognitiveStatus?.running ? 'bg-emerald-500/10 text-emerald-500' : 'bg-neutral-700 text-neutral-400'}`}>
                    <Brain size={20} />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">COGNITIVE CORE</p>
                    <Badge variant={getStatusColor(cognitiveStatus?.running || false)}>
                      {cognitiveStatus?.running ? 'RUNNING' : 'IDLE'}
                    </Badge>
                  </div>
                </div>
                <div className="text-2xl font-mono font-bold text-neutral-200">
                  {cognitiveStatus?.stats.cycles_completed || 0}
                </div>
                <p className="text-xs text-neutral-500">cycles completed</p>
              </Card>

              {/* DGM Self-Improvement */}
              <Card className="border-neutral-800">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`p-2 rounded-lg ${dgmStatus?.running ? 'bg-purple-500/10 text-purple-500' : 'bg-neutral-700 text-neutral-400'}`}>
                    <GitBranch size={20} />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">SELF-IMPROVEMENT</p>
                    <Badge variant={dgmStatus?.running ? 'purple' : 'neutral'}>
                      {dgmStatus?.running ? 'ACTIVE' : 'IDLE'}
                    </Badge>
                  </div>
                </div>
                <div className="text-2xl font-mono font-bold text-neutral-200">
                  {dgmStatus?.state.improvements_deployed || 0}
                </div>
                <p className="text-xs text-neutral-500">improvements deployed</p>
              </Card>

              {/* Memory System */}
              <Card className="border-neutral-800">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500">
                    <Database size={20} />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">MEMORY SYSTEM</p>
                    <Badge variant={memoryStats?.qdrant.status === 'green' ? 'emerald' : 'amber'}>
                      {memoryStats?.qdrant.status?.toUpperCase() || 'UNKNOWN'}
                    </Badge>
                  </div>
                </div>
                <div className="text-2xl font-mono font-bold text-neutral-200">
                  {memoryStats?.total_memories || 0}
                </div>
                <p className="text-xs text-neutral-500">memories stored</p>
              </Card>

              {/* Diagnosis */}
              <Card className="border-neutral-800">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`p-2 rounded-lg bg-${getHealthColor(diagnosisHealth?.health_score || 0)}-500/10 text-${getHealthColor(diagnosisHealth?.health_score || 0)}-500`}>
                    <Shield size={20} />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">SYSTEM HEALTH</p>
                    <Badge variant={getHealthColor(diagnosisHealth?.health_score || 0)}>
                      {diagnosisHealth?.status?.toUpperCase() || 'UNKNOWN'}
                    </Badge>
                  </div>
                </div>
                <div className="text-2xl font-mono font-bold text-neutral-200">
                  {diagnosisHealth?.health_score || 0}%
                </div>
                <p className="text-xs text-neutral-500">health score</p>
              </Card>

              {/* Agent Scheduler */}
              <Card className="border-neutral-800">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`p-2 rounded-lg ${schedulerStatus?.status === 'running' ? 'bg-cyan-500/10 text-cyan-500' : 'bg-neutral-700 text-neutral-400'}`}>
                    <ListTodo size={20} />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">AGENT SCHEDULER</p>
                    <Badge variant={schedulerStatus?.status === 'running' ? 'cyan' : 'neutral'}>
                      {schedulerStatus?.status?.toUpperCase() || 'UNKNOWN'}
                    </Badge>
                  </div>
                </div>
                <div className="text-2xl font-mono font-bold text-neutral-200">
                  {schedulerStatus?.stats.total_completed || 0}
                </div>
                <p className="text-xs text-neutral-500">tasks completed</p>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card className="border-neutral-800">
              <h3 className="text-lg font-mono text-neutral-200 mb-4 flex items-center gap-2">
                <Zap size={18} className="text-amber-500" />
                Quick Actions
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Button
                  variant={cognitiveStatus?.running ? 'secondary' : 'primary'}
                  icon={cognitiveStatus?.running ?
                    (stoppingCognitive ? <Loader2 size={14} className="animate-spin" /> : <Square size={14} />) :
                    (startingCognitive ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />)
                  }
                  onClick={cognitiveStatus?.running ? handleStopCognitive : handleStartCognitive}
                  disabled={startingCognitive || stoppingCognitive}
                >
                  {cognitiveStatus?.running ? 'Stop Cognitive' : 'Start Cognitive'}
                </Button>

                <Button
                  variant={dgmStatus?.running ? 'secondary' : 'primary'}
                  icon={dgmStatus?.running ?
                    (stoppingDGM ? <Loader2 size={14} className="animate-spin" /> : <Square size={14} />) :
                    (startingDGM ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />)
                  }
                  onClick={dgmStatus?.running ? handleStopDGM : handleStartDGM}
                  disabled={startingDGM || stoppingDGM}
                >
                  {dgmStatus?.running ? 'Stop DGM' : 'Start DGM'}
                </Button>

                <Button
                  variant="secondary"
                  icon={runningBenchmark ? <Loader2 size={14} className="animate-spin" /> : <BarChart3 size={14} />}
                  onClick={handleRunBenchmark}
                  disabled={runningBenchmark}
                >
                  Run Benchmark
                </Button>

                <Button
                  variant="secondary"
                  icon={<Activity size={14} />}
                  onClick={() => setActiveTab('MEMORY')}
                >
                  View Memory
                </Button>
              </div>
            </Card>

            {/* Memory Tier Breakdown */}
            {memoryStats && (
              <Card className="border-neutral-800">
                <h3 className="text-lg font-mono text-neutral-200 mb-4 flex items-center gap-2">
                  <Layers size={18} className="text-amber-500" />
                  Memory Tier Distribution
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                  {Object.entries(memoryStats.tier_counts).map(([tier, count]) => (
                    <div key={tier} className="text-center p-3 bg-neutral-900/50 rounded-lg border border-neutral-800">
                      <div className="text-xl font-mono font-bold text-neutral-200">{count}</div>
                      <div className="text-xs text-neutral-500 capitalize">{tier}</div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'COGNITIVE' && (
          <div className="space-y-6">
            <Card className="border-neutral-800 p-0 overflow-hidden">
              <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                  <Brain size={16} className="text-emerald-500" />
                  COGNITIVE CORE STATUS
                </span>
                <Badge variant={getStatusColor(cognitiveStatus?.running || false)}>
                  {cognitiveStatus?.state?.toUpperCase() || 'UNKNOWN'}
                </Badge>
              </div>
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 bg-neutral-900/50 rounded-lg">
                    <div className="text-xs text-neutral-500 mb-1">Session ID</div>
                    <div className="font-mono text-sm text-neutral-300">{cognitiveStatus?.session_id || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-neutral-900/50 rounded-lg">
                    <div className="text-xs text-neutral-500 mb-1">Model</div>
                    <div className="font-mono text-sm text-neutral-300">{cognitiveStatus?.model || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-neutral-900/50 rounded-lg">
                    <div className="text-xs text-neutral-500 mb-1">Loop Interval</div>
                    <div className="font-mono text-sm text-neutral-300">{cognitiveStatus?.loop_interval_seconds || 0}s</div>
                  </div>
                  <div className="p-3 bg-neutral-900/50 rounded-lg">
                    <div className="text-xs text-neutral-500 mb-1">Step Number</div>
                    <div className="font-mono text-sm text-neutral-300">{cognitiveStatus?.step_number || 0}</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div className="text-center p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                    <div className="text-2xl font-mono font-bold text-emerald-400">{cognitiveStatus?.stats.cycles_completed || 0}</div>
                    <div className="text-xs text-neutral-500">Cycles</div>
                  </div>
                  <div className="text-center p-3 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
                    <div className="text-2xl font-mono font-bold text-cyan-400">{cognitiveStatus?.stats.actions_executed || 0}</div>
                    <div className="text-xs text-neutral-500">Actions</div>
                  </div>
                  <div className="text-center p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                    <div className="text-2xl font-mono font-bold text-emerald-400">{cognitiveStatus?.stats.actions_succeeded || 0}</div>
                    <div className="text-xs text-neutral-500">Succeeded</div>
                  </div>
                  <div className="text-center p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                    <div className="text-2xl font-mono font-bold text-red-400">{cognitiveStatus?.stats.actions_failed || 0}</div>
                    <div className="text-xs text-neutral-500">Failed</div>
                  </div>
                  <div className="text-center p-3 bg-purple-500/10 rounded-lg border border-purple-500/20">
                    <div className="text-2xl font-mono font-bold text-purple-400">{cognitiveStatus?.stats.learnings_stored || 0}</div>
                    <div className="text-xs text-neutral-500">Learnings</div>
                  </div>
                </div>

                <div className="flex gap-3 pt-4 border-t border-neutral-800">
                  <Button
                    variant={cognitiveStatus?.running ? 'secondary' : 'primary'}
                    icon={cognitiveStatus?.running ?
                      (stoppingCognitive ? <Loader2 size={14} className="animate-spin" /> : <Square size={14} />) :
                      (startingCognitive ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />)
                    }
                    onClick={cognitiveStatus?.running ? handleStopCognitive : handleStartCognitive}
                    disabled={startingCognitive || stoppingCognitive}
                  >
                    {cognitiveStatus?.running ? 'Stop Cognitive Core' : 'Start Cognitive Core'}
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'DGM' && (
          <div className="space-y-6">
            <Card className="border-neutral-800 p-0 overflow-hidden">
              <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                  <GitBranch size={16} className="text-purple-500" />
                  DARWIN GÖDEL MACHINE (DGM) - SELF-IMPROVEMENT ENGINE
                </span>
                <Badge variant={dgmStatus?.running ? 'purple' : 'neutral'}>
                  {dgmStatus?.running ? 'ACTIVE' : 'IDLE'}
                </Badge>
              </div>
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 bg-purple-500/10 rounded-lg border border-purple-500/20">
                    <div className="text-2xl font-mono font-bold text-purple-400">{dgmStatus?.state.total_cycles || 0}</div>
                    <div className="text-xs text-neutral-500">Total Cycles</div>
                  </div>
                  <div className="text-center p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                    <div className="text-2xl font-mono font-bold text-emerald-400">{dgmStatus?.state.improvements_deployed || 0}</div>
                    <div className="text-xs text-neutral-500">Deployed</div>
                  </div>
                  <div className="text-center p-3 bg-amber-500/10 rounded-lg border border-amber-500/20">
                    <div className="text-2xl font-mono font-bold text-amber-400">{dgmStatus?.state.improvements_rolled_back || 0}</div>
                    <div className="text-xs text-neutral-500">Rolled Back</div>
                  </div>
                  <div className="text-center p-3 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
                    <div className="text-2xl font-mono font-bold text-cyan-400">{dgmStatus?.benchmarks_history_count || 0}</div>
                    <div className="text-xs text-neutral-500">Benchmarks</div>
                  </div>
                </div>

                <div className="p-4 bg-neutral-900/50 rounded-lg border border-neutral-800">
                  <h4 className="text-sm font-mono text-neutral-400 mb-3">Configuration</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-neutral-500">Benchmark Interval:</span>
                      <span className="ml-2 text-neutral-300">{dgmStatus?.config.benchmark_interval_hours || 0}h</span>
                    </div>
                    <div>
                      <span className="text-neutral-500">Improvement Cycle:</span>
                      <span className="ml-2 text-neutral-300">{dgmStatus?.config.improvement_cycle_hours || 0}h</span>
                    </div>
                    <div>
                      <span className="text-neutral-500">Max Changes/Cycle:</span>
                      <span className="ml-2 text-neutral-300">{dgmStatus?.config.max_changes_per_cycle || 0}</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 pt-4 border-t border-neutral-800">
                  <Button
                    variant={dgmStatus?.running ? 'secondary' : 'primary'}
                    icon={dgmStatus?.running ?
                      (stoppingDGM ? <Loader2 size={14} className="animate-spin" /> : <Square size={14} />) :
                      (startingDGM ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />)
                    }
                    onClick={dgmStatus?.running ? handleStopDGM : handleStartDGM}
                    disabled={startingDGM || stoppingDGM}
                  >
                    {dgmStatus?.running ? 'Stop DGM Engine' : 'Start DGM Engine'}
                  </Button>
                  <Button
                    variant="secondary"
                    icon={runningBenchmark ? <Loader2 size={14} className="animate-spin" /> : <BarChart3 size={14} />}
                    onClick={handleRunBenchmark}
                    disabled={runningBenchmark}
                  >
                    Run Benchmark Now
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'MEMORY' && (
          <div className="space-y-6">
            <Card className="border-neutral-800 p-0 overflow-hidden">
              <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                  <Database size={16} className="text-amber-500" />
                  MIRIX 6-TIER MEMORY SYSTEM
                </span>
                <Badge variant={memoryStats?.qdrant.status === 'green' ? 'emerald' : 'amber'}>
                  {memoryStats?.qdrant.status?.toUpperCase() || 'UNKNOWN'}
                </Badge>
              </div>
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="p-3 bg-neutral-900/50 rounded-lg">
                    <div className="text-xs text-neutral-500 mb-1">Storage Backend</div>
                    <div className="font-mono text-sm text-neutral-300">{memoryStats?.storage_backend || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-neutral-900/50 rounded-lg">
                    <div className="text-xs text-neutral-500 mb-1">Embedding Model</div>
                    <div className="font-mono text-sm text-neutral-300">{memoryStats?.qdrant.embedding_model || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-neutral-900/50 rounded-lg">
                    <div className="text-xs text-neutral-500 mb-1">Embedding Dimension</div>
                    <div className="font-mono text-sm text-neutral-300">{memoryStats?.qdrant.embedding_dimension || 0}</div>
                  </div>
                </div>

                <h4 className="text-sm font-mono text-neutral-400 mt-6 mb-3">Memory Tiers</h4>
                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                  {memoryStats && Object.entries(memoryStats.tier_counts).map(([tier, count]) => {
                    const tierColors: Record<string, string> = {
                      core: 'red',
                      episodic: 'cyan',
                      semantic: 'purple',
                      procedural: 'emerald',
                      resource: 'amber',
                      vault: 'neutral'
                    };
                    const color = tierColors[tier] || 'neutral';
                    return (
                      <div key={tier} className={`text-center p-4 bg-${color}-500/10 rounded-lg border border-${color}-500/20`}>
                        <div className={`text-3xl font-mono font-bold text-${color}-400`}>{count}</div>
                        <div className="text-xs text-neutral-500 capitalize mt-1">{tier}</div>
                        <div className="mt-2">
                          <ProgressBar
                            value={memoryStats.total_memories > 0 ? (count / memoryStats.total_memories) * 100 : 0}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="p-4 bg-neutral-900/50 rounded-lg border border-neutral-800 mt-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm text-neutral-400">Total Memories</div>
                      <div className="text-3xl font-mono font-bold text-neutral-200">{memoryStats?.total_memories || 0}</div>
                    </div>
                    <div>
                      <div className="text-sm text-neutral-400">Qdrant Points</div>
                      <div className="text-3xl font-mono font-bold text-neutral-200">{memoryStats?.qdrant.points_count || 0}</div>
                    </div>
                    <div>
                      <div className="text-sm text-neutral-400">Collection</div>
                      <div className="font-mono text-neutral-300">{memoryStats?.qdrant.collection || 'N/A'}</div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'SCHEDULER' && (
          <div className="space-y-6">
            <Card className="border-neutral-800 p-0 overflow-hidden">
              <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                  <ListTodo size={16} className="text-cyan-500" />
                  AGENT SCHEDULER (AIOS)
                </span>
                <Badge variant={schedulerStatus?.status === 'running' ? 'cyan' : 'neutral'}>
                  {schedulerStatus?.status?.toUpperCase() || 'UNKNOWN'}
                </Badge>
              </div>
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-3 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
                    <div className="text-2xl font-mono font-bold text-cyan-400">{schedulerStatus?.stats.total_scheduled || 0}</div>
                    <div className="text-xs text-neutral-500">Scheduled</div>
                  </div>
                  <div className="text-center p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                    <div className="text-2xl font-mono font-bold text-emerald-400">{schedulerStatus?.stats.total_completed || 0}</div>
                    <div className="text-xs text-neutral-500">Completed</div>
                  </div>
                  <div className="text-center p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                    <div className="text-2xl font-mono font-bold text-red-400">{schedulerStatus?.stats.total_failed || 0}</div>
                    <div className="text-xs text-neutral-500">Failed</div>
                  </div>
                  <div className="text-center p-3 bg-amber-500/10 rounded-lg border border-amber-500/20">
                    <div className="text-2xl font-mono font-bold text-amber-400">{schedulerStatus?.stats.queue_size || 0}</div>
                    <div className="text-xs text-neutral-500">In Queue</div>
                  </div>
                </div>

                <div className="p-4 bg-neutral-900/50 rounded-lg border border-neutral-800">
                  <h4 className="text-sm font-mono text-neutral-400 mb-3">Scheduler Configuration</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-neutral-500">Policy:</span>
                      <span className="ml-2 text-neutral-300">{schedulerStatus?.stats.policy || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-neutral-500">Max Concurrent:</span>
                      <span className="ml-2 text-neutral-300">{schedulerStatus?.stats.max_concurrent || 0}</span>
                    </div>
                    <div>
                      <span className="text-neutral-500">Currently Running:</span>
                      <span className="ml-2 text-neutral-300">{schedulerStatus?.stats.running || 0}</span>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Autonomy;
