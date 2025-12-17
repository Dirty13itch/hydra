import React, { useState } from 'react';
import { Card, Button, Tabs, Badge, ProgressBar } from '../components/UIComponents';
import { useDashboardData } from '../context/DashboardDataContext';
import { FlaskConical, Cpu, Zap, Download, Trash2, Play, Sparkles, StopCircle, RefreshCw, Loader2 } from 'lucide-react';
import { sendMessageToGemini } from '../services/geminiService';

export const Lab: React.FC = () => {
  const { models, modelsLoading, refreshModels } = useDashboardData();
  const [activeTab, setActiveTab] = useState('MODELS');
  const [systemPrompt, setSystemPrompt] = useState("You are HYDRA, a command center AI. You are concise, technical, and helpful.");
  const [userPrompt, setUserPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [metrics, setMetrics] = useState({ tokens: 0, time: 0 });

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
          <div className="h-64 flex flex-col items-center justify-center text-neutral-600 border border-dashed border-neutral-800 rounded-xl">
            <FlaskConical size={48} className="mb-4 text-neutral-800" />
            <p>No active experiments. Start one to benchmark model performance.</p>
          </div>
        )}

      </div>
    </div>
  );
};
