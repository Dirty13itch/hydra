import React, { useState, useEffect } from 'react';
import { Card, Button, Tabs, Badge, ProgressBar, Modal } from '../components/UIComponents';
import { useDashboardData } from '../context/DashboardDataContext';
import { useNotifications } from '../context/NotificationContext';
import { Database, Search, Upload, Book, FileText, RefreshCw, Loader2, Link, Globe, FileUp, CheckCircle, XCircle, Clock, AlertCircle, Plus, Trash2 } from 'lucide-react';
import { searchMemory, ingestUrl as apiIngestUrl, getKnowledgeMetrics, getKnowledgeHealth, crawlUrl } from '../services/hydraApi';

interface IngestionSource {
  id: string;
  type: 'url' | 'file' | 'crawl';
  name: string;
  url?: string;
  status: 'pending' | 'processing' | 'complete' | 'failed';
  chunksCreated?: number;
  addedAt: string;
  collection: string;
}

export const Knowledge: React.FC = () => {
  const { collections, collectionsLoading, refreshCollections } = useDashboardData();
  const { addNotification } = useNotifications();
  const [activeTab, setActiveTab] = useState('COLLECTIONS');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{ id: string; content: string; score: number }>>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Sources state
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [ingestType, setIngestType] = useState<'url' | 'crawl'>('url');
  const [ingestUrlValue, setIngestUrlValue] = useState('');
  const [ingestCollection, setIngestCollection] = useState('hydra_knowledge');
  const [isIngesting, setIsIngesting] = useState(false);
  const [sources, setSources] = useState<IngestionSource[]>([
    { id: '1', type: 'url', name: 'Anthropic Claude Docs', url: 'https://docs.anthropic.com', status: 'complete', chunksCreated: 156, addedAt: '2h ago', collection: 'hydra_knowledge' },
    { id: '2', type: 'crawl', name: 'OpenAI Cookbook', url: 'https://cookbook.openai.com', status: 'complete', chunksCreated: 423, addedAt: '1d ago', collection: 'hydra_knowledge' },
    { id: '3', type: 'file', name: 'architecture-decisions.md', status: 'complete', chunksCreated: 34, addedAt: '3d ago', collection: 'technical_docs' },
    { id: '4', type: 'url', name: 'LangChain Docs', url: 'https://python.langchain.com', status: 'processing', addedAt: '5m ago', collection: 'hydra_knowledge' },
  ]);

  // Knowledge health state
  const [healthStatus, setHealthStatus] = useState<{ qdrant: boolean; meilisearch: boolean } | null>(null);

  useEffect(() => {
    getKnowledgeHealth().then(result => {
      if (result.data) {
        setHealthStatus({
          qdrant: result.data.qdrant?.connected ?? false,
          meilisearch: result.data.meilisearch?.connected ?? false,
        });
      }
    });
  }, []);

  const tabs = [
    { id: 'COLLECTIONS', label: 'Collections' },
    { id: 'SOURCES', label: 'Sources' },
    { id: 'SEARCH', label: 'Semantic Search' }
  ];

  const handleIngest = async () => {
    if (!ingestUrlValue.trim()) return;

    setIsIngesting(true);
    try {
      if (ingestType === 'url') {
        const result = await apiIngestUrl(ingestUrlValue, ingestCollection);
        if (result.data) {
          const newSource: IngestionSource = {
            id: result.data.document_id,
            type: 'url',
            name: new URL(ingestUrlValue).hostname,
            url: ingestUrlValue,
            status: 'complete',
            chunksCreated: result.data.chunks_created,
            addedAt: 'Just now',
            collection: ingestCollection,
          };
          setSources(prev => [newSource, ...prev]);
          addNotification('success', 'Ingestion Complete', `Created ${result.data.chunks_created} chunks from URL`);
          setIsIngestModalOpen(false);
          setIngestUrlValue('');
        } else {
          addNotification('error', 'Ingestion Failed', result.error || 'Unknown error');
        }
      } else {
        const result = await crawlUrl(ingestUrlValue, 10);
        if (result.data) {
          const newSource: IngestionSource = {
            id: result.data.task_id,
            type: 'crawl',
            name: new URL(ingestUrlValue).hostname,
            url: ingestUrlValue,
            status: 'processing',
            addedAt: 'Just now',
            collection: ingestCollection,
          };
          setSources(prev => [newSource, ...prev]);
          addNotification('info', 'Crawl Started', `Crawling ${result.data.pages_found} pages...`);
          setIsIngestModalOpen(false);
          setIngestUrlValue('');
        }
      }
    } catch (err) {
      addNotification('error', 'Ingestion Error', String(err));
    } finally {
      setIsIngesting(false);
    }
  };

  // Calculate totals from real data
  const totalDocs = collections.reduce((sum, col) => sum + col.docCount, 0);
  const totalChunks = collections.reduce((sum, col) => sum + col.chunkCount, 0);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const result = await searchMemory(searchQuery, 10);
      if (result.data) {
        setSearchResults(result.data.results);
      }
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="flex flex-col h-full bg-surface-base">
      {/* Knowledge Header */}
      <div className="px-6 pt-6 pb-2 border-b border-neutral-800 flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200 flex items-center gap-2">
            <span className="text-cyan-500">KNOWLEDGE</span> // RAG PIPELINE
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
            icon={collectionsLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            onClick={refreshCollections}
          >
            Re-Index
          </Button>
          <Button variant="primary" size="sm" className="bg-cyan-600 hover:bg-cyan-500" icon={<Upload size={14} />}>Ingest</Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">

        {activeTab === 'COLLECTIONS' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Collection Stats */}
              <Card className="bg-surface-dim border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-500"><Book size={20} /></div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">TOTAL DOCS</p>
                    <p className="text-xl font-mono font-bold text-neutral-200">
                      {collectionsLoading ? '--' : totalDocs.toLocaleString()}
                    </p>
                  </div>
                </div>
              </Card>
              <Card className="bg-surface-dim border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-500"><Database size={20} /></div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">VECTOR CHUNKS</p>
                    <p className="text-xl font-mono font-bold text-neutral-200">
                      {collectionsLoading ? '--' : totalChunks.toLocaleString()}
                    </p>
                  </div>
                </div>
              </Card>
              <Card className="bg-surface-dim border-neutral-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-500/10 rounded-lg text-purple-500"><FileText size={20} /></div>
                  <div>
                    <p className="text-xs text-neutral-500 font-mono">COLLECTIONS</p>
                    <p className="text-xl font-mono font-bold text-neutral-200">{collections.length}</p>
                  </div>
                </div>
              </Card>
            </div>

            <h3 className="text-lg font-medium text-neutral-300 mt-8">Active Collections</h3>

            {collectionsLoading && collections.length === 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3].map(i => (
                  <Card key={i} className="animate-pulse">
                    <div className="h-6 bg-neutral-800 rounded w-2/3 mb-4" />
                    <div className="h-4 bg-neutral-800 rounded w-full mb-2" />
                    <div className="h-3 bg-neutral-800 rounded w-3/4" />
                  </Card>
                ))}
              </div>
            ) : collections.length === 0 ? (
              <Card className="p-8 text-center text-neutral-500">
                <Database size={32} className="mx-auto mb-2 opacity-50" />
                <p>No collections found</p>
                <p className="text-xs mt-1">Create a collection in Qdrant to get started</p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {collections.map((col) => (
                  <Card key={col.id} className="hover:border-cyan-500/30 transition-colors group">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-neutral-800 rounded group-hover:text-cyan-400 transition-colors">
                          <Book size={20} />
                        </div>
                        <div>
                          <h4 className="font-bold text-neutral-200">{col.name}</h4>
                          <div className="flex gap-2 text-xs text-neutral-500 font-mono">
                            <span>{col.docCount} DOCS</span>
                            <span>•</span>
                            <span>{col.chunkCount.toLocaleString()} CHUNKS</span>
                          </div>
                        </div>
                      </div>
                      {col.status === 'indexing' && (
                        <Badge variant="amber">Indexing</Badge>
                      )}
                      {col.status === 'ready' && (
                        <Badge variant="emerald">Ready</Badge>
                      )}
                    </div>

                    <div className="space-y-3">
                      {col.topics.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {col.topics.map(topic => (
                            <span key={topic} className="px-1.5 py-0.5 rounded text-[10px] bg-neutral-800 text-neutral-400 border border-neutral-700">
                              #{topic}
                            </span>
                          ))}
                        </div>
                      )}

                      {col.status === 'indexing' && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px] text-neutral-500 uppercase">
                            <span>Indexing Progress</span>
                            <span>45%</span>
                          </div>
                          <ProgressBar value={45} colorClass="bg-amber-500" />
                        </div>
                      )}

                      <div className="pt-3 border-t border-neutral-800 text-xs text-neutral-600 font-mono flex justify-between">
                        <span>Last Ingested: {col.lastIngested}</span>
                        <button className="hover:text-cyan-400 transition-colors">View Docs →</button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'SOURCES' && (
          <div className="space-y-6">
            {/* Ingest Modal */}
            <Modal isOpen={isIngestModalOpen} onClose={() => setIsIngestModalOpen(false)} title="INGEST NEW SOURCE">
              <div className="space-y-4">
                {/* Ingest Type Selector */}
                <div className="flex gap-2">
                  <button
                    className={`flex-1 p-3 rounded-lg border transition-colors ${ingestType === 'url' ? 'border-cyan-500 bg-cyan-500/10 text-cyan-400' : 'border-neutral-700 text-neutral-400 hover:border-neutral-600'}`}
                    onClick={() => setIngestType('url')}
                  >
                    <Link size={20} className="mx-auto mb-1" />
                    <span className="text-xs font-mono">Single URL</span>
                  </button>
                  <button
                    className={`flex-1 p-3 rounded-lg border transition-colors ${ingestType === 'crawl' ? 'border-cyan-500 bg-cyan-500/10 text-cyan-400' : 'border-neutral-700 text-neutral-400 hover:border-neutral-600'}`}
                    onClick={() => setIngestType('crawl')}
                  >
                    <Globe size={20} className="mx-auto mb-1" />
                    <span className="text-xs font-mono">Crawl Site</span>
                  </button>
                </div>

                {/* URL Input */}
                <div>
                  <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">
                    {ingestType === 'url' ? 'Document URL' : 'Site URL to Crawl'}
                  </label>
                  <input
                    type="url"
                    value={ingestUrlValue}
                    onChange={(e) => setIngestUrlValue(e.target.value)}
                    placeholder={ingestType === 'url' ? 'https://docs.example.com/page' : 'https://docs.example.com'}
                    className="w-full bg-surface-dim border border-neutral-700 rounded-lg p-3 text-neutral-200 outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Collection Selector */}
                <div>
                  <label className="block text-xs font-mono text-neutral-500 uppercase mb-2">Target Collection</label>
                  <select
                    value={ingestCollection}
                    onChange={(e) => setIngestCollection(e.target.value)}
                    className="w-full bg-surface-dim border border-neutral-700 rounded-lg p-3 text-neutral-200 outline-none focus:border-cyan-500"
                  >
                    {collections.map(col => (
                      <option key={col.id} value={col.id}>{col.name}</option>
                    ))}
                    <option value="new">+ Create New Collection</option>
                  </select>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <Button variant="ghost" onClick={() => setIsIngestModalOpen(false)}>Cancel</Button>
                  <Button
                    variant="primary"
                    className="bg-cyan-600 hover:bg-cyan-500"
                    icon={isIngesting ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                    onClick={handleIngest}
                    disabled={isIngesting || !ingestUrlValue.trim()}
                  >
                    {isIngesting ? 'Ingesting...' : ingestType === 'url' ? 'Ingest URL' : 'Start Crawl'}
                  </Button>
                </div>
              </div>
            </Modal>

            {/* Sources Header */}
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-medium text-neutral-300">Ingestion Sources</h3>
              <Button
                variant="primary"
                size="sm"
                className="bg-cyan-600 hover:bg-cyan-500"
                icon={<Plus size={14} />}
                onClick={() => setIsIngestModalOpen(true)}
              >
                Add Source
              </Button>
            </div>

            {/* Health Status */}
            {healthStatus && (
              <div className="flex gap-4">
                <Card className="flex-1 bg-surface-dim border-neutral-800">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${healthStatus.qdrant ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                      <Database size={20} />
                    </div>
                    <div>
                      <p className="text-xs text-neutral-500 font-mono">QDRANT</p>
                      <p className="text-sm font-medium text-neutral-200">{healthStatus.qdrant ? 'Connected' : 'Offline'}</p>
                    </div>
                  </div>
                </Card>
                <Card className="flex-1 bg-surface-dim border-neutral-800">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${healthStatus.meilisearch ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'}`}>
                      <Search size={20} />
                    </div>
                    <div>
                      <p className="text-xs text-neutral-500 font-mono">MEILISEARCH</p>
                      <p className="text-sm font-medium text-neutral-200">{healthStatus.meilisearch ? 'Connected' : 'Unavailable'}</p>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Sources List */}
            <div className="space-y-3">
              {sources.map(source => (
                <Card key={source.id} className="hover:border-cyan-500/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${
                        source.type === 'url' ? 'bg-cyan-500/10 text-cyan-400' :
                        source.type === 'crawl' ? 'bg-purple-500/10 text-purple-400' :
                        'bg-neutral-800 text-neutral-400'
                      }`}>
                        {source.type === 'url' && <Link size={18} />}
                        {source.type === 'crawl' && <Globe size={18} />}
                        {source.type === 'file' && <FileUp size={18} />}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-neutral-200">{source.name}</h4>
                          <Badge variant={
                            source.status === 'complete' ? 'emerald' :
                            source.status === 'processing' ? 'amber' :
                            source.status === 'failed' ? 'red' : 'neutral'
                          }>
                            {source.status}
                          </Badge>
                        </div>
                        {source.url && (
                          <p className="text-xs text-neutral-500 font-mono truncate max-w-md">{source.url}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-6 text-sm text-neutral-500">
                      <div className="text-right">
                        <p className="text-xs text-neutral-600">Collection</p>
                        <p className="font-mono text-neutral-400">{source.collection}</p>
                      </div>
                      {source.chunksCreated !== undefined && (
                        <div className="text-right">
                          <p className="text-xs text-neutral-600">Chunks</p>
                          <p className="font-mono text-emerald-400">{source.chunksCreated}</p>
                        </div>
                      )}
                      <div className="text-right">
                        <p className="text-xs text-neutral-600">Added</p>
                        <p className="font-mono">{source.addedAt}</p>
                      </div>
                      <button className="p-2 text-neutral-600 hover:text-red-400 transition-colors">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>

                  {source.status === 'processing' && (
                    <div className="mt-3 pt-3 border-t border-neutral-800">
                      <div className="flex items-center gap-2 text-xs text-amber-400">
                        <Loader2 size={12} className="animate-spin" />
                        <span>Processing... Extracting and embedding content</span>
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>

            {sources.length === 0 && (
              <Card className="p-8 text-center text-neutral-500">
                <Upload size={32} className="mx-auto mb-2 opacity-50" />
                <p>No sources ingested yet</p>
                <p className="text-xs mt-1">Add URLs, files, or start a web crawl</p>
              </Card>
            )}
          </div>
        )}

        {activeTab === 'SEARCH' && (
          <div className="max-w-4xl mx-auto space-y-8 mt-4">
            <div className="relative">
              <input
                type="text"
                placeholder="Search across all knowledge bases (semantic & keyword)..."
                className="w-full bg-surface-raised border border-neutral-700 rounded-xl px-5 py-4 pl-12 text-neutral-200 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
              />
              <Search className="absolute left-4 top-4.5 text-neutral-500" size={20} />
              <div className="absolute right-4 top-4 flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleSearch}
                  disabled={isSearching || !searchQuery.trim()}
                >
                  {isSearching ? <Loader2 size={14} className="animate-spin" /> : 'Search'}
                </Button>
              </div>
            </div>

            {searchResults.length > 0 ? (
              <div className="space-y-4">
                <p className="text-sm text-neutral-500">{searchResults.length} results found</p>
                {searchResults.map((result, i) => (
                  <Card key={result.id || i} className="border-neutral-800">
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-mono text-neutral-500">Score: {result.score.toFixed(3)}</span>
                    </div>
                    <p className="text-sm text-neutral-300 line-clamp-4">{result.content}</p>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="space-y-4 opacity-50 text-center py-12">
                <Database size={48} className="mx-auto text-neutral-800 mb-4" />
                <p className="text-neutral-500">Enter a query to retrieve semantically relevant chunks from the vector store.</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
};
