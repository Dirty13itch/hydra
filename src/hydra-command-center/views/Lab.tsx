import React, { useState, useEffect } from 'react';
import { Card, Button, Tabs, Badge, ProgressBar } from '../components/UIComponents';
import { useDashboardData } from '../context/DashboardDataContext';
import { FlaskConical, Cpu, Zap, Download, Trash2, Play, Sparkles, StopCircle, RefreshCw, Loader2, Activity, Terminal, CheckCircle, XCircle, Clock } from 'lucide-react';
import { sendMessageToGemini } from '../services/geminiService';

const API_BASE = 'http://192.168.1.244:8700';

interface BenchmarkResult {
  suite_id: string;
  started_at: string;
  finished_at: string;
  overall_score: number;
  category_scores: Record<string, number>;
  results: Array<{
    name: string;
    category: string;
    score: number;
    passed: boolean;
    details?: Record<string, any>;
  }>;
}

interface SandboxExecution {
  execution_id: string;
  language: string;
  status: 'running' | 'completed' | 'failed' | 'timeout';
  exit_code?: number;
  stdout?: string;
  stderr?: string;
  duration_ms?: number;
  created_at: string;
}

export const Lab: React.FC = () => {
  const { models, modelsLoading, refreshModels } = useDashboardData();
  const [activeTab, setActiveTab] = useState('MODELS');
  const [systemPrompt, setSystemPrompt] = useState("You are HYDRA, a command center AI. You are concise, technical, and helpful.");
  const [userPrompt, setUserPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [metrics, setMetrics] = useState({ tokens: 0, time: 0 });

  // Experiments state
  const [benchmarkStatus, setBenchmarkStatus] = useState<{ status: string; categories: string[] } | null>(null);
  const [latestBenchmark, setLatestBenchmark] = useState<BenchmarkResult | null>(null);
  const [runningBenchmark, setRunningBenchmark] = useState(false);
  const [sandboxCode, setSandboxCode] = useState('print("Hello from HYDRA sandbox!")');
  const [sandboxLanguage, setSandboxLanguage] = useState<'python' | 'bash' | 'javascript'>('python');
  const [sandboxResult, setSandboxResult] = useState<SandboxExecution | null>(null);
  const [runningSandbox, setRunningSandbox] = useState(false);

  // Fetch benchmark data
  useEffect(() => {
    if (activeTab === 'EXPERIMENTS') {
      fetchBenchmarkData();
    }
  }, [activeTab]);

  const fetchBenchmarkData = async () => {
    try {
      const [statusRes, latestRes] = await Promise.all([
        fetch(`${API_BASE}/benchmark/status`),
        fetch(`${API_BASE}/benchmark/latest`)
      ]);
      if (statusRes.ok) {
        setBenchmarkStatus(await statusRes.json());
      }
      if (latestRes.ok) {
        const data = await latestRes.json();
        if (data.results && data.results.length > 0) {
          setLatestBenchmark(data.results[0]);
        }
      }
    } catch (e) {
      console.error('Failed to fetch benchmark data:', e);
    }
  };

  const runBenchmark = async () => {
    setRunningBenchmark(true);
    try {
      const res = await fetch(`${API_BASE}/benchmark/run`, { method: 'POST' });
      if (res.ok) {
        // Poll for results
        await new Promise(r => setTimeout(r, 2000));
        await fetchBenchmarkData();
      }
    } catch (e) {
      console.error('Failed to run benchmark:', e);
    } finally {
      setRunningBenchmark(false);
    }
  };

  const runSandbox = async () => {
    setRunningSandbox(true);
    setSandboxResult(null);
    try {
      const res = await fetch(`${API_BASE}/sandbox/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: sandboxCode,
          language: sandboxLanguage,
          timeout: 30
        })
      });
      if (res.ok) {
        const result = await res.json();
        setSandboxResult(result);
      }
    } catch (e) {
      console.error('Failed to execute sandbox:', e);
    } finally {
      setRunningSandbox(false);
    }
  };

  const tabs = [
    { id: 'MODELS', label: 'Models' },
    { id: 'PLAYGROUND', label: 'Playground' },
    { id: 'EXPERIMENTS', label: 'Experiments' }
  ];

  const handleGenerate = async () => {
    if (!userPrompt.trim()) return;

    setIsGenerating(true);
    setOutput("");
    const startTime = Date.now();

    try {
      // Use the actual service
      const response = await sendMessageToGemini(userPrompt, systemPrompt);
      const endTime = Date.now();

      setOutput(response.text);
      setMetrics({
        tokens: response.text.split(/\s+/).length * 1.3, // Rough estimation
        time: endTime - startTime
      });
    } catch (e) {
      setOutput("Error generating response. Check that the API is configured.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Calculate total VRAM usage
  const totalVramUsed = models
    .filter(m => m.status === 'loaded' && m.provider === 'local')
    .reduce((sum, m) => sum + m.vramUsage, 0);

  const loadedModels = models.filter(m => m.status === 'loaded');
  const localModels = models.filter(m => m.provider === 'local');
  const apiModels = models.filter(m => m.provider === 'api');

  return (
    <div className="flex flex-col h-full bg-surface-base">
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-emerald-500">LABORATORY</span> // MODEL OPS
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
            icon={modelsLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            onClick={refreshModels}
          >
            Refresh
          </Button>
          <Button variant="primary" size="sm" icon={<FlaskConical size={14} />}>New Experiment</Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">

        {activeTab === 'MODELS' && (
          <div className="space-y-6">
            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card className="bg-surface-dim border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500"><Cpu size={20} /></div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">LOADED MODELS</p>
                    <p className="text-xl font-mono font-bold text-neutral-200">{loadedModels.length}</p>
                  </div>
                </div>
              </Card>
              <Card className="bg-surface-dim border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-500/10 rounded-lg text-purple-500"><Zap size={20} /></div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">VRAM USED</p>
                    <p className="text-xl font-mono font-bold text-neutral-200">{totalVramUsed} GB</p>
                  </div>
                </div>
              </Card>
              <Card className="bg-surface-dim border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-500"><FlaskConical size={20} /></div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">LOCAL MODELS</p>
                    <p className="text-xl font-mono font-bold text-neutral-200">{localModels.length}</p>
                  </div>
                </div>
              </Card>
              <Card className="bg-surface-dim border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-500/10 rounded-lg text-amber-500"><Sparkles size={20} /></div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">API MODELS</p>
                    <p className="text-xl font-mono font-bold text-neutral-200">{apiModels.length}</p>
                  </div>
                </div>
              </Card>
            </div>

            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-neutral-300">Available Models</h3>
              <div className="flex gap-4 text-sm font-mono text-neutral-500">
                <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-emerald-500"></div> LOADED</span>
                <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-neutral-600"></div> UNLOADED</span>
              </div>
            </div>

            {modelsLoading && models.length === 0 ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <Card key={i} className="animate-pulse">
                    <div className="h-6 bg-neutral-800 rounded w-2/3 mb-4" />
                    <div className="h-4 bg-neutral-800 rounded w-full mb-2" />
                    <div className="h-10 bg-neutral-800 rounded" />
                  </Card>
                ))}
              </div>
            ) : models.length === 0 ? (
              <Card className="p-8 text-center text-neutral-500">
                <Cpu size={32} className="mx-auto mb-2 opacity-50" />
                <p>No models found</p>
                <p className="text-xs mt-1">Models will appear when loaded in TabbyAPI or Ollama</p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {models.map((model) => (
                  <Card key={model.id} className={`border-l-4 ${model.status === 'loaded' ? 'border-l-emerald-500 border-neutral-800' : 'border-l-neutral-700 border-neutral-800 opacity-80'}`}>
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-neutral-200 text-lg">{model.name}</h4>
                          {model.provider === 'api' && <Badge variant="cyan">API</Badge>}
                          {model.provider === 'local' && <Badge variant="neutral">LOCAL</Badge>}
                        </div>
                        <p className="text-sm text-neutral-500 font-mono mt-1">
                          {model.paramSize} • {model.quantization} • {model.contextLength} Context
                        </p>
                      </div>
                      <div className="flex gap-2">
                        {model.status === 'loaded' ? (
                          <Button variant="danger" size="sm" className="!py-1 !px-2 text-xs">Unload</Button>
                        ) : (
                          <Button variant="secondary" size="sm" className="!py-1 !px-2 text-xs">Load</Button>
                        )}
                      </div>
                    </div>

                    {model.provider === 'local' && model.vramUsage > 0 && (
                      <div className="space-y-3 bg-neutral-900/50 p-3 rounded-lg border border-neutral-800">
                        <div className="flex justify-between items-center text-xs font-mono text-neutral-400 mb-1">
                          <span>ESTIMATED VRAM</span>
                          <span>{model.vramUsage} GB</span>
                        </div>
                        <div className="flex gap-1 h-2">
                          {[...Array(Math.min(48, Math.ceil(model.vramUsage * 2)))].map((_, i) => (
                            <div
                              key={i}
                              className={`flex-1 rounded-sm ${i < model.vramUsage * 2 ? (model.status === 'loaded' ? 'bg-emerald-500' : 'bg-neutral-600') : 'bg-neutral-800'}`}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'PLAYGROUND' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
            <div className="flex flex-col gap-4">
              <Card className="flex-1 flex flex-col border-neutral-800 p-0 overflow-hidden min-h-[150px]">
                <div className="bg-surface-dim px-4 py-2 border-b border-neutral-800 text-xs font-mono text-neutral-500">SYSTEM PROMPT</div>
                <textarea
                  className="flex-1 bg-surface-default p-4 text-sm text-neutral-300 outline-none resize-none font-mono focus:bg-surface-raised transition-colors"
                  placeholder="You are a helpful AI assistant..."
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                />
              </Card>
              <Card className="flex-1 flex flex-col border-neutral-800 p-0 overflow-hidden min-h-[150px]">
                <div className="bg-surface-dim px-4 py-2 border-b border-neutral-800 text-xs font-mono text-neutral-500">USER INPUT</div>
                <textarea
                  className="flex-1 bg-surface-default p-4 text-sm text-neutral-300 outline-none resize-none font-mono focus:bg-surface-raised transition-colors"
                  placeholder="Enter your prompt here..."
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                />
                <div className="p-2 bg-surface-dim border-t border-neutral-800 flex justify-end">
                  <Button
                    variant="primary"
                    icon={isGenerating ? <Sparkles size={14} className="animate-spin" /> : <Play size={14} />}
                    onClick={handleGenerate}
                    disabled={isGenerating || !userPrompt.trim()}
                  >
                    {isGenerating ? 'Generating...' : 'Generate'}
                  </Button>
                </div>
              </Card>
            </div>
            <Card className="flex flex-col border-neutral-800 p-0 overflow-hidden h-full min-h-[400px]">
              <div className="bg-surface-dim px-4 py-2 border-b border-neutral-800 text-xs font-mono text-neutral-500 flex justify-between">
                <span>OUTPUT</span>
                <div className="flex gap-3">
                  <span>{Math.round(metrics.tokens)} est. tokens</span>
                  <span>{metrics.time}ms</span>
                </div>
              </div>
              <div className="flex-1 bg-surface-base p-4 text-sm text-neutral-300 font-mono whitespace-pre-wrap overflow-y-auto leading-relaxed">
                {isGenerating ? (
                  <div className="flex items-center gap-2 text-emerald-500 animate-pulse">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
                    <span>Computing response...</span>
                  </div>
                ) : output ? output : (
                  <span className="text-neutral-600 italic">Waiting for generation...</span>
                )}
              </div>
            </Card>
          </div>
        )}

        {activeTab === 'EXPERIMENTS' && (
          <div className="space-y-6">
            {/* Benchmark Section */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-neutral-300 flex items-center gap-2">
                  <Activity size={20} className="text-emerald-500" />
                  System Benchmarks
                </h3>
                <Button
                  variant="primary"
                  size="sm"
                  icon={runningBenchmark ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                  onClick={runBenchmark}
                  disabled={runningBenchmark}
                >
                  {runningBenchmark ? 'Running...' : 'Run Benchmark'}
                </Button>
              </div>

              {latestBenchmark ? (
                <div className="space-y-4">
                  {/* Overall Score */}
                  <Card className="bg-surface-dim border-neutral-800">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <p className="text-xs text-neutral-500 font-mono">OVERALL SCORE</p>
                        <p className={`text-4xl font-mono font-bold ${latestBenchmark.overall_score >= 90 ? 'text-emerald-400' : latestBenchmark.overall_score >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                          {latestBenchmark.overall_score.toFixed(1)}%
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-neutral-500 font-mono">SUITE ID</p>
                        <p className="text-sm font-mono text-neutral-400">{latestBenchmark.suite_id}</p>
                        <p className="text-xs text-neutral-600 mt-1">
                          <Clock size={12} className="inline mr-1" />
                          {new Date(latestBenchmark.finished_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <ProgressBar value={latestBenchmark.overall_score} colorClass={latestBenchmark.overall_score >= 90 ? 'bg-emerald-500' : latestBenchmark.overall_score >= 70 ? 'bg-amber-500' : 'bg-red-500'} />
                  </Card>

                  {/* Category Scores */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    {Object.entries(latestBenchmark.category_scores).map(([category, score]) => (
                      <Card key={category} className="bg-surface-dim border-neutral-800 text-center">
                        <p className={`text-2xl font-mono font-bold ${score >= 90 ? 'text-emerald-400' : score >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                          {score.toFixed(0)}%
                        </p>
                        <p className="text-xs text-neutral-500 capitalize mt-1">{category.replace('_', ' ')}</p>
                      </Card>
                    ))}
                  </div>

                  {/* Individual Results */}
                  <Card className="bg-surface-dim border-neutral-800 p-0">
                    <div className="bg-surface-dim px-4 py-2 border-b border-neutral-800 text-xs font-mono text-neutral-500">
                      TEST RESULTS ({latestBenchmark.results.length} tests)
                    </div>
                    <div className="max-h-48 overflow-y-auto">
                      {latestBenchmark.results.map((result, idx) => (
                        <div key={idx} className="flex items-center justify-between px-4 py-2 border-b border-neutral-800/50 last:border-b-0">
                          <div className="flex items-center gap-2">
                            {result.passed ? (
                              <CheckCircle size={14} className="text-emerald-500" />
                            ) : (
                              <XCircle size={14} className="text-red-500" />
                            )}
                            <span className="text-sm text-neutral-300">{result.name.replace(/_/g, ' ')}</span>
                            <Badge variant="neutral">{result.category}</Badge>
                          </div>
                          <span className={`text-sm font-mono ${result.score >= 90 ? 'text-emerald-400' : result.score >= 70 ? 'text-amber-400' : 'text-red-400'}`}>
                            {result.score.toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              ) : (
                <Card className="p-8 text-center text-neutral-500 border-neutral-800">
                  <Activity size={32} className="mx-auto mb-2 opacity-50" />
                  <p>No benchmark results yet</p>
                  <p className="text-xs mt-1">Run a benchmark to see system performance metrics</p>
                </Card>
              )}
            </div>

            {/* Sandbox Section */}
            <div>
              <h3 className="text-lg font-medium text-neutral-300 flex items-center gap-2 mb-4">
                <Terminal size={20} className="text-purple-500" />
                Code Sandbox
              </h3>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card className="bg-surface-dim border-neutral-800 p-0 flex flex-col">
                  <div className="bg-surface-dim px-4 py-2 border-b border-neutral-800 flex items-center justify-between">
                    <span className="text-xs font-mono text-neutral-500">CODE INPUT</span>
                    <select
                      value={sandboxLanguage}
                      onChange={(e) => setSandboxLanguage(e.target.value as 'python' | 'bash' | 'javascript')}
                      className="bg-neutral-800 text-neutral-300 text-xs px-2 py-1 rounded border border-neutral-700"
                    >
                      <option value="python">Python</option>
                      <option value="bash">Bash</option>
                      <option value="javascript">JavaScript</option>
                    </select>
                  </div>
                  <textarea
                    className="flex-1 bg-surface-base p-4 text-sm text-neutral-300 outline-none resize-none font-mono focus:bg-surface-raised transition-colors min-h-[200px]"
                    placeholder="Enter code to execute..."
                    value={sandboxCode}
                    onChange={(e) => setSandboxCode(e.target.value)}
                  />
                  <div className="p-2 bg-surface-dim border-t border-neutral-800 flex justify-end">
                    <Button
                      variant="primary"
                      size="sm"
                      icon={runningSandbox ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                      onClick={runSandbox}
                      disabled={runningSandbox || !sandboxCode.trim()}
                    >
                      {runningSandbox ? 'Running...' : 'Execute'}
                    </Button>
                  </div>
                </Card>

                <Card className="bg-surface-dim border-neutral-800 p-0 flex flex-col">
                  <div className="bg-surface-dim px-4 py-2 border-b border-neutral-800 flex items-center justify-between">
                    <span className="text-xs font-mono text-neutral-500">OUTPUT</span>
                    {sandboxResult && (
                      <div className="flex items-center gap-2">
                        {sandboxResult.status === 'completed' ? (
                          <Badge variant="emerald">Success</Badge>
                        ) : sandboxResult.status === 'failed' ? (
                          <Badge variant="red">Failed</Badge>
                        ) : sandboxResult.status === 'timeout' ? (
                          <Badge variant="amber">Timeout</Badge>
                        ) : (
                          <Badge variant="neutral">Running</Badge>
                        )}
                        {sandboxResult.duration_ms && (
                          <span className="text-xs text-neutral-500">{sandboxResult.duration_ms}ms</span>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 bg-surface-base p-4 text-sm font-mono whitespace-pre-wrap overflow-y-auto min-h-[200px]">
                    {runningSandbox ? (
                      <div className="flex items-center gap-2 text-purple-500 animate-pulse">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span>Executing in sandbox...</span>
                      </div>
                    ) : sandboxResult ? (
                      <div>
                        {sandboxResult.stdout && (
                          <div className="text-neutral-300 mb-2">{sandboxResult.stdout}</div>
                        )}
                        {sandboxResult.stderr && (
                          <div className="text-red-400">{sandboxResult.stderr}</div>
                        )}
                        {!sandboxResult.stdout && !sandboxResult.stderr && (
                          <span className="text-neutral-600">(No output)</span>
                        )}
                      </div>
                    ) : (
                      <span className="text-neutral-600 italic">Sandbox output will appear here...</span>
                    )}
                  </div>
                </Card>
              </div>

              <div className="mt-3 text-xs text-neutral-600 flex items-center gap-4">
                <span>Sandbox config: 256MB RAM, 0.5 CPU, 30s timeout, no network</span>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
