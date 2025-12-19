import React, { useState, useEffect } from 'react';
import { Card, Button, Tabs, Badge, ProgressBar } from '../components/UIComponents';
import {
  Search,
  Globe,
  Server,
  FileText,
  Clock,
  Download,
  Loader2,
  ExternalLink,
  Sparkles,
  Database,
  RefreshCw,
  BookOpen,
  AlertCircle,
  TrendingUp,
  Lightbulb,
  Zap,
  Plus,
  CheckCircle,
  Target
} from 'lucide-react';

const API_BASE = 'http://192.168.1.244:8700';

interface ResearchResult {
  id: string;
  query: string;
  mode: 'local' | 'cloud' | 'hybrid';
  status: 'pending' | 'running' | 'completed' | 'failed';
  startedAt: string;
  completedAt?: string;
  report?: string;
  sources?: Array<{ title: string; url: string }>;
  error?: string;
}

interface TrendingTopic {
  topic: string;
  mention_count: number;
  relevance_score: number;
  matched_focus_areas: string[];
  sample_entries: string[];
  first_seen: string;
  last_seen: string;
}

interface ResearchSuggestion {
  id: string;
  topic: string;
  suggested_query: string;
  reason: string;
  priority: 'high' | 'medium' | 'low';
  focus_areas: string[];
  generated_at: string;
  source: string;
}

interface NewsIntelligenceStatus {
  status: string;
  last_scan: string | null;
  trending_topics_count: number;
  news_sources: string[];
  focus_areas: string[];
  suggestions_available: number;
}

export const Research: React.FC = () => {
  const [activeTab, setActiveTab] = useState('NEW');
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'local' | 'cloud' | 'hybrid'>('local');
  const [isResearching, setIsResearching] = useState(false);
  const [results, setResults] = useState<ResearchResult[]>([]);
  const [currentResult, setCurrentResult] = useState<ResearchResult | null>(null);
  const [gptResearcherStatus, setGptResearcherStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const [localResearchStatus, setLocalResearchStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  // News Intelligence state
  const [newsIntelStatus, setNewsIntelStatus] = useState<NewsIntelligenceStatus | null>(null);
  const [trendingTopics, setTrendingTopics] = useState<TrendingTopic[]>([]);
  const [suggestions, setSuggestions] = useState<ResearchSuggestion[]>([]);
  const [loadingIntel, setLoadingIntel] = useState(false);
  const [queuingSuggestion, setQueuingSuggestion] = useState<string | null>(null);

  const tabs = [
    { id: 'NEW', label: 'New Research' },
    { id: 'AI', label: 'AI Suggestions' },
    { id: 'HISTORY', label: 'History' },
    { id: 'TOOLS', label: 'Tools' }
  ];

  // Check tool health on mount
  useEffect(() => {
    const checkHealth = async () => {
      // Check GPT Researcher
      try {
        const res = await fetch('http://192.168.1.244:8090/', { method: 'HEAD' });
        setGptResearcherStatus(res.ok ? 'online' : 'offline');
      } catch {
        setGptResearcherStatus('offline');
      }

      // Check Local Deep Research
      try {
        const res = await fetch('http://192.168.1.244:5050/', { method: 'HEAD' });
        setLocalResearchStatus(res.ok ? 'online' : 'offline');
      } catch {
        setLocalResearchStatus('offline');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Fetch news intelligence data
  useEffect(() => {
    const fetchNewsIntelligence = async () => {
      setLoadingIntel(true);
      try {
        // Fetch status
        const statusRes = await fetch(`${API_BASE}/news/intelligence/status`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          setNewsIntelStatus(statusData);
        }

        // Fetch trending topics
        const trendingRes = await fetch(`${API_BASE}/news/intelligence/trending?limit=10`);
        if (trendingRes.ok) {
          const trendingData = await trendingRes.json();
          setTrendingTopics(trendingData.topics || []);
        }

        // Fetch suggestions
        const suggestionsRes = await fetch(`${API_BASE}/news/intelligence/suggestions`);
        if (suggestionsRes.ok) {
          const suggestionsData = await suggestionsRes.json();
          setSuggestions(suggestionsData.suggestions || []);
        }

        // Fetch focus areas
        const focusRes = await fetch(`${API_BASE}/news/intelligence/focus-areas`);
        if (focusRes.ok) {
          const focusData = await focusRes.json();
          setNewsIntelStatus(prev => prev ? { ...prev, focus_areas: focusData.focus_areas || [] } : { focus_areas: focusData.focus_areas || [] } as any);
        }
      } catch (error) {
        console.error('Failed to fetch news intelligence:', error);
      } finally {
        setLoadingIntel(false);
      }
    };

    fetchNewsIntelligence();
    const interval = setInterval(fetchNewsIntelligence, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const handleQueueSuggestion = async (suggestion: ResearchSuggestion) => {
    setQueuingSuggestion(suggestion.id);
    try {
      const res = await fetch(`${API_BASE}/news/intelligence/suggestions/queue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suggestion_id: suggestion.id }),
      });
      if (res.ok) {
        // Remove from suggestions list
        setSuggestions(prev => prev.filter(s => s.id !== suggestion.id));
      }
    } catch (error) {
      console.error('Failed to queue suggestion:', error);
    } finally {
      setQueuingSuggestion(null);
    }
  };

  const handleUseSuggestion = (suggestion: ResearchSuggestion) => {
    setQuery(suggestion.suggested_query);
    setActiveTab('NEW');
  };

  const refreshNewsIntelligence = async () => {
    setLoadingIntel(true);
    try {
      const statusRes = await fetch(`${API_BASE}/news/intelligence/status`);
      if (statusRes.ok) setNewsIntelStatus(await statusRes.json());

      const trendingRes = await fetch(`${API_BASE}/news/intelligence/trending?limit=10`);
      if (trendingRes.ok) {
        const data = await trendingRes.json();
        setTrendingTopics(data.topics || []);
      }

      const suggestionsRes = await fetch(`${API_BASE}/news/intelligence/suggestions`);
      if (suggestionsRes.ok) {
        const data = await suggestionsRes.json();
        setSuggestions(data.suggestions || []);
      }

      const focusRes = await fetch(`${API_BASE}/news/intelligence/focus-areas`);
      if (focusRes.ok) {
        const focusData = await focusRes.json();
        setNewsIntelStatus(prev => prev ? { ...prev, focus_areas: focusData.focus_areas || [] } : { focus_areas: focusData.focus_areas || [] } as any);
      }
    } catch (error) {
      console.error('Failed to refresh news intelligence:', error);
    } finally {
      setLoadingIntel(false);
    }
  };

  const handleResearch = async () => {
    if (!query.trim()) return;

    setIsResearching(true);
    const newResult: ResearchResult = {
      id: `res-${Date.now()}`,
      query: query.trim(),
      mode,
      status: 'running',
      startedAt: new Date().toISOString(),
    };
    setCurrentResult(newResult);
    setActiveTab('NEW');

    try {
      // For now, we'll show the embedded tools
      // In the future, we could call APIs directly
      setCurrentResult({
        ...newResult,
        status: 'completed',
        completedAt: new Date().toISOString(),
        report: `Research initiated for: "${query}"\n\nPlease use the embedded research tools below to conduct your research.\n\n` +
                `- GPT Researcher: http://192.168.1.244:8090\n` +
                `- Local Deep Research: http://192.168.1.244:5050\n` +
                `- Perplexica: http://192.168.1.244:3030`,
      });
      setResults(prev => [newResult, ...prev]);
    } catch (error) {
      setCurrentResult({
        ...newResult,
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    } finally {
      setIsResearching(false);
    }
  };

  const StatusBadge = ({ status }: { status: 'online' | 'offline' | 'checking' }) => {
    if (status === 'checking') {
      return <Badge variant="neutral"><Loader2 size={10} className="animate-spin mr-1" /> Checking</Badge>;
    }
    return status === 'online'
      ? <Badge variant="emerald">Online</Badge>
      : <Badge variant="red">Offline</Badge>;
  };

  return (
    <div className="flex flex-col h-full bg-surface-base">
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-emerald-500">RESEARCH</span> // DEEP SEARCH
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
          <Button variant="secondary" size="sm" icon={<RefreshCw size={14} />}>
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">

        {activeTab === 'NEW' && (
          <div className="space-y-6">
            {/* Research Input */}
            <Card className="border-neutral-800 p-0 overflow-hidden">
              <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                  <Search size={16} />
                  RESEARCH QUERY
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setMode('local')}
                    className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
                      mode === 'local'
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
                        : 'bg-neutral-800 text-neutral-400 border border-neutral-700 hover:border-neutral-600'
                    }`}
                  >
                    <Server size={12} className="inline mr-1" /> Local
                  </button>
                  <button
                    onClick={() => setMode('cloud')}
                    className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
                      mode === 'cloud'
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/50'
                        : 'bg-neutral-800 text-neutral-400 border border-neutral-700 hover:border-neutral-600'
                    }`}
                  >
                    <Globe size={12} className="inline mr-1" /> Cloud
                  </button>
                  <button
                    onClick={() => setMode('hybrid')}
                    className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
                      mode === 'hybrid'
                        ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50'
                        : 'bg-neutral-800 text-neutral-400 border border-neutral-700 hover:border-neutral-600'
                    }`}
                  >
                    <Sparkles size={12} className="inline mr-1" /> Hybrid
                  </button>
                </div>
              </div>
              <textarea
                className="w-full bg-surface-default p-4 text-neutral-300 outline-none resize-none font-mono text-sm min-h-[120px] focus:bg-surface-raised transition-colors"
                placeholder="Enter your research topic or question..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <div className="p-3 bg-surface-dim border-t border-neutral-800 flex justify-between items-center">
                <div className="text-xs text-neutral-500 font-mono">
                  {mode === 'local' && 'Using: Local Deep Research + Midnight-Miqu-70B + SearXNG'}
                  {mode === 'cloud' && 'Using: GPT Researcher + Perplexity Deep Research'}
                  {mode === 'hybrid' && 'Using: Best of both local and cloud sources'}
                </div>
                <Button
                  variant="primary"
                  icon={isResearching ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
                  onClick={handleResearch}
                  disabled={isResearching || !query.trim()}
                >
                  {isResearching ? 'Researching...' : 'Start Research'}
                </Button>
              </div>
            </Card>

            {/* Research Tools Quick Access */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="border-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer group"
                    onClick={() => window.open('http://192.168.1.244:8090', '_blank')}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-purple-500/10 rounded-lg text-purple-500">
                      <Globe size={20} />
                    </div>
                    <div>
                      <h4 className="font-bold text-neutral-200">GPT Researcher</h4>
                      <p className="text-xs text-neutral-500">Cloud + Local Research</p>
                    </div>
                  </div>
                  <StatusBadge status={gptResearcherStatus} />
                </div>
                <p className="text-xs text-neutral-500 mb-3">
                  Comprehensive research reports with citations. Supports cloud APIs for best quality.
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-neutral-600">:8090</span>
                  <ExternalLink size={14} className="text-neutral-600 group-hover:text-emerald-500 transition-colors" />
                </div>
              </Card>

              <Card className="border-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer group"
                    onClick={() => window.open('http://192.168.1.244:5050', '_blank')}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500">
                      <Server size={20} />
                    </div>
                    <div>
                      <h4 className="font-bold text-neutral-200">Local Deep Research</h4>
                      <p className="text-xs text-neutral-500">100% Private Research</p>
                    </div>
                  </div>
                  <StatusBadge status={localResearchStatus} />
                </div>
                <p className="text-xs text-neutral-500 mb-3">
                  Privacy-first research using local LLMs. ~95% SimpleQA accuracy.
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-neutral-600">:5050</span>
                  <ExternalLink size={14} className="text-neutral-600 group-hover:text-emerald-500 transition-colors" />
                </div>
              </Card>

              <Card className="border-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer group"
                    onClick={() => window.open('http://192.168.1.244:3030', '_blank')}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-500">
                      <Search size={20} />
                    </div>
                    <div>
                      <h4 className="font-bold text-neutral-200">Perplexica</h4>
                      <p className="text-xs text-neutral-500">Quick Web Search AI</p>
                    </div>
                  </div>
                  <Badge variant="emerald">Online</Badge>
                </div>
                <p className="text-xs text-neutral-500 mb-3">
                  Fast web search with AI summarization. Uses SearXNG backend.
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-neutral-600">:3030</span>
                  <ExternalLink size={14} className="text-neutral-600 group-hover:text-emerald-500 transition-colors" />
                </div>
              </Card>
            </div>

            {/* Current/Recent Result */}
            {currentResult && (
              <Card className="border-neutral-800 p-0 overflow-hidden">
                <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                  <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                    <FileText size={16} />
                    RESEARCH RESULT
                  </span>
                  <div className="flex items-center gap-2">
                    <Badge variant={currentResult.status === 'completed' ? 'emerald' : currentResult.status === 'running' ? 'cyan' : 'red'}>
                      {currentResult.status.toUpperCase()}
                    </Badge>
                    {currentResult.mode === 'local' && <Badge variant="neutral">LOCAL</Badge>}
                    {currentResult.mode === 'cloud' && <Badge variant="cyan">CLOUD</Badge>}
                    {currentResult.mode === 'hybrid' && <Badge variant="purple">HYBRID</Badge>}
                  </div>
                </div>
                <div className="p-4">
                  <h4 className="font-mono text-neutral-200 mb-2">{currentResult.query}</h4>
                  {currentResult.status === 'running' && (
                    <div className="flex items-center gap-2 text-cyan-500">
                      <Loader2 size={16} className="animate-spin" />
                      <span className="text-sm">Researching...</span>
                    </div>
                  )}
                  {currentResult.report && (
                    <div className="mt-4 p-4 bg-neutral-900/50 rounded-lg border border-neutral-800">
                      <pre className="text-sm text-neutral-300 whitespace-pre-wrap font-mono">
                        {currentResult.report}
                      </pre>
                    </div>
                  )}
                  {currentResult.error && (
                    <div className="mt-4 p-4 bg-red-900/20 rounded-lg border border-red-800 text-red-400 text-sm">
                      <AlertCircle size={16} className="inline mr-2" />
                      {currentResult.error}
                    </div>
                  )}
                </div>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'AI' && (
          <div className="space-y-6">
            {/* Intelligence Status Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-sm text-neutral-400">
                  <Sparkles size={16} className="text-amber-500" />
                  <span>
                    {newsIntelStatus?.trending_topics_count || 0} Trending Topics
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm text-neutral-400">
                  <Lightbulb size={16} className="text-cyan-500" />
                  <span>
                    {suggestions.length} Suggestions
                  </span>
                </div>
                {newsIntelStatus?.last_scan && (
                  <div className="text-xs text-neutral-500">
                    Last scan: {new Date(newsIntelStatus.last_scan).toLocaleString()}
                  </div>
                )}
              </div>
              <Button
                variant="secondary"
                size="sm"
                icon={loadingIntel ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                onClick={refreshNewsIntelligence}
                disabled={loadingIntel}
              >
                Refresh
              </Button>
            </div>

            {/* Research Suggestions */}
            <Card className="border-neutral-800 p-0 overflow-hidden">
              <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                  <Lightbulb size={16} className="text-cyan-500" />
                  AI RESEARCH SUGGESTIONS
                </span>
                <Badge variant="cyan">{suggestions.length} Available</Badge>
              </div>
              <div className="p-4">
                {suggestions.length === 0 ? (
                  <div className="text-center py-8 text-neutral-500">
                    <Lightbulb size={32} className="mx-auto mb-2 opacity-50" />
                    <p>No suggestions available</p>
                    <p className="text-xs mt-1">Configure news sources to generate research suggestions</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {suggestions.map(suggestion => (
                      <div
                        key={suggestion.id}
                        className="p-4 bg-neutral-900/50 rounded-lg border border-neutral-800 hover:border-neutral-700 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge variant={suggestion.priority === 'high' ? 'red' : suggestion.priority === 'medium' ? 'amber' : 'neutral'}>
                                {suggestion.priority.toUpperCase()}
                              </Badge>
                              <h4 className="font-medium text-neutral-200">{suggestion.topic}</h4>
                            </div>
                            <p className="text-sm text-neutral-400 mb-2">{suggestion.suggested_query}</p>
                            <p className="text-xs text-neutral-500">{suggestion.reason}</p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {suggestion.focus_areas.map(area => (
                                <span key={area} className="px-2 py-0.5 text-xs bg-emerald-500/10 text-emerald-500 rounded">
                                  {area}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="flex flex-col gap-2">
                            <Button
                              variant="primary"
                              size="sm"
                              icon={<Search size={12} />}
                              onClick={() => handleUseSuggestion(suggestion)}
                            >
                              Use
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              icon={queuingSuggestion === suggestion.id ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
                              onClick={() => handleQueueSuggestion(suggestion)}
                              disabled={queuingSuggestion === suggestion.id}
                            >
                              Queue
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>

            {/* Trending Topics */}
            <Card className="border-neutral-800 p-0 overflow-hidden">
              <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                  <TrendingUp size={16} className="text-amber-500" />
                  TRENDING TOPICS
                </span>
                <Badge variant="amber">{trendingTopics.length} Topics</Badge>
              </div>
              <div className="p-4">
                {trendingTopics.length === 0 ? (
                  <div className="text-center py-8 text-neutral-500">
                    <TrendingUp size={32} className="mx-auto mb-2 opacity-50" />
                    <p>No trending topics detected</p>
                    <p className="text-xs mt-1">Topics from news feeds will appear here</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {trendingTopics.map((topic, index) => (
                      <div
                        key={index}
                        className="p-3 bg-neutral-900/50 rounded-lg border border-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer"
                        onClick={() => {
                          setQuery(topic.topic);
                          setActiveTab('NEW');
                        }}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-neutral-200 text-sm">{topic.topic}</h4>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-neutral-500">{topic.mention_count} mentions</span>
                            <div
                              className="w-2 h-2 rounded-full"
                              style={{
                                backgroundColor: topic.relevance_score > 0.7 ? '#10b981' : topic.relevance_score > 0.4 ? '#f59e0b' : '#6b7280'
                              }}
                              title={`Relevance: ${(topic.relevance_score * 100).toFixed(0)}%`}
                            />
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {topic.matched_focus_areas.slice(0, 3).map(area => (
                            <span key={area} className="px-1.5 py-0.5 text-xs bg-cyan-500/10 text-cyan-500 rounded">
                              {area}
                            </span>
                          ))}
                          {topic.matched_focus_areas.length > 3 && (
                            <span className="text-xs text-neutral-500">
                              +{topic.matched_focus_areas.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </Card>

            {/* Focus Areas */}
            {newsIntelStatus && (
              <Card className="border-neutral-800">
                <div className="flex items-center gap-2 mb-3">
                  <Target size={16} className="text-emerald-500" />
                  <h3 className="font-mono text-neutral-300 text-sm">HYDRA FOCUS AREAS</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {newsIntelStatus.focus_areas.map(area => (
                    <span
                      key={area}
                      className="px-2 py-1 text-xs bg-emerald-500/10 text-emerald-400 rounded border border-emerald-500/20"
                    >
                      {area}
                    </span>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'HISTORY' && (
          <div className="space-y-4">
            {results.length === 0 ? (
              <Card className="p-8 text-center text-neutral-500 border-neutral-800">
                <Clock size={32} className="mx-auto mb-2 opacity-50" />
                <p>No research history yet</p>
                <p className="text-xs mt-1">Your completed research will appear here</p>
              </Card>
            ) : (
              results.map(result => (
                <Card key={result.id} className="border-neutral-800 hover:border-neutral-700 transition-colors cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-neutral-200">{result.query}</h4>
                      <p className="text-xs text-neutral-500 mt-1">
                        {new Date(result.startedAt).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Badge variant={result.mode === 'local' ? 'neutral' : result.mode === 'cloud' ? 'cyan' : 'purple'}>
                        {result.mode.toUpperCase()}
                      </Badge>
                      <Badge variant={result.status === 'completed' ? 'emerald' : 'red'}>
                        {result.status.toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}

        {activeTab === 'TOOLS' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* GPT Researcher Embed */}
              <Card className="border-neutral-800 p-0 overflow-hidden">
                <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                  <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                    <Globe size={16} />
                    GPT RESEARCHER
                  </span>
                  <StatusBadge status={gptResearcherStatus} />
                </div>
                <div className="h-[500px]">
                  <iframe
                    src="http://192.168.1.244:8090"
                    className="w-full h-full border-0"
                    title="GPT Researcher"
                  />
                </div>
              </Card>

              {/* Local Deep Research Embed */}
              <Card className="border-neutral-800 p-0 overflow-hidden">
                <div className="bg-surface-dim px-4 py-3 border-b border-neutral-800 flex items-center justify-between">
                  <span className="text-sm font-mono text-neutral-400 flex items-center gap-2">
                    <Server size={16} />
                    LOCAL DEEP RESEARCH
                  </span>
                  <StatusBadge status={localResearchStatus} />
                </div>
                <div className="h-[500px]">
                  <iframe
                    src="http://192.168.1.244:5050"
                    className="w-full h-full border-0"
                    title="Local Deep Research"
                  />
                </div>
              </Card>
            </div>

            {/* Additional Tools Info */}
            <Card className="border-neutral-800">
              <h3 className="text-lg font-mono text-neutral-200 mb-4">Research Stack Architecture</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                <div className="p-3 bg-neutral-900/50 rounded-lg border border-neutral-800">
                  <div className="font-mono text-emerald-500 mb-1">Local LLM</div>
                  <div className="text-neutral-400">Midnight-Miqu-70B via TabbyAPI</div>
                </div>
                <div className="p-3 bg-neutral-900/50 rounded-lg border border-neutral-800">
                  <div className="font-mono text-cyan-500 mb-1">Web Search</div>
                  <div className="text-neutral-400">SearXNG (Self-hosted)</div>
                </div>
                <div className="p-3 bg-neutral-900/50 rounded-lg border border-neutral-800">
                  <div className="font-mono text-purple-500 mb-1">Embeddings</div>
                  <div className="text-neutral-400">nomic-embed-text via Ollama</div>
                </div>
                <div className="p-3 bg-neutral-900/50 rounded-lg border border-neutral-800">
                  <div className="font-mono text-amber-500 mb-1">Cloud Fallback</div>
                  <div className="text-neutral-400">Perplexity, Claude, GPT-4o</div>
                </div>
              </div>
            </Card>
          </div>
        )}

      </div>
    </div>
  );
};
