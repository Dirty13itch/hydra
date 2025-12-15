'use client';

import { useState, useEffect, useCallback } from 'react';
import { DomainView } from '../DomainTabs';

interface ResearchTopic {
  id: string;
  topic: string;
  status: 'queued' | 'researching' | 'complete' | 'failed';
  sources: number;
  documentsIngested: number;
  createdAt: string;
  completedAt?: string;
}

interface KnowledgeCollection {
  name: string;
  vectors: number;
  size: string;
  lastUpdated: string;
}

interface FeedSource {
  id: string;
  title: string;
  unreadCount: number;
  category: string;
  lastFetched: string;
}

interface IntelligenceStats {
  totalDocuments: number;
  totalVectors: number;
  searchesLast24h: number;
  crawlsLast24h: number;
  feedsActive: number;
  unreadArticles: number;
}

const MOCK_STATS: IntelligenceStats = {
  totalDocuments: 2847,
  totalVectors: 15234,
  searchesLast24h: 127,
  crawlsLast24h: 34,
  feedsActive: 12,
  unreadArticles: 47,
};

const MOCK_RESEARCH: ResearchTopic[] = [
  {
    id: 'r1',
    topic: 'ExLlamaV3 tensor parallelism implementation',
    status: 'complete',
    sources: 8,
    documentsIngested: 15,
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    completedAt: new Date(Date.now() - 43200000).toISOString(),
  },
  {
    id: 'r2',
    topic: 'Home Assistant Lutron Caseta integration',
    status: 'researching',
    sources: 4,
    documentsIngested: 7,
    createdAt: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'r3',
    topic: 'NixOS flake best practices 2025',
    status: 'queued',
    sources: 0,
    documentsIngested: 0,
    createdAt: new Date(Date.now() - 1800000).toISOString(),
  },
];

const MOCK_COLLECTIONS: KnowledgeCollection[] = [
  { name: 'hydra_docs', vectors: 4521, size: '128 MB', lastUpdated: '2h ago' },
  { name: 'research_papers', vectors: 8934, size: '412 MB', lastUpdated: '6h ago' },
  { name: 'conversation_history', vectors: 1234, size: '45 MB', lastUpdated: '5m ago' },
  { name: 'code_snippets', vectors: 545, size: '18 MB', lastUpdated: '1d ago' },
];

const MOCK_FEEDS: FeedSource[] = [
  { id: 'f1', title: 'Hacker News', unreadCount: 23, category: 'Tech', lastFetched: '15m ago' },
  { id: 'f2', title: 'ArXiv ML', unreadCount: 8, category: 'Research', lastFetched: '1h ago' },
  { id: 'f3', title: 'NixOS Discourse', unreadCount: 5, category: 'NixOS', lastFetched: '30m ago' },
  { id: 'f4', title: 'LocalLLaMA Reddit', unreadCount: 11, category: 'AI', lastFetched: '45m ago' },
];

export function IntelligenceView() {
  const [stats, setStats] = useState<IntelligenceStats>(MOCK_STATS);
  const [research, setResearch] = useState<ResearchTopic[]>(MOCK_RESEARCH);
  const [collections, setCollections] = useState<KnowledgeCollection[]>(MOCK_COLLECTIONS);
  const [feeds, setFeeds] = useState<FeedSource[]>(MOCK_FEEDS);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const getStatusColor = (status: ResearchTopic['status']) => {
    switch (status) {
      case 'complete':
        return 'var(--hydra-green)';
      case 'researching':
        return 'var(--hydra-cyan)';
      case 'queued':
        return 'var(--hydra-yellow)';
      case 'failed':
        return 'var(--hydra-red)';
    }
  };

  const getStatusBg = (status: ResearchTopic['status']) => {
    switch (status) {
      case 'complete':
        return 'rgba(0, 255, 136, 0.1)';
      case 'researching':
        return 'rgba(0, 255, 255, 0.1)';
      case 'queued':
        return 'rgba(255, 204, 0, 0.1)';
      case 'failed':
        return 'rgba(255, 51, 102, 0.1)';
    }
  };

  const formatRelativeTime = (timestamp: string) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <DomainView
      title="Intelligence"
      icon="🔍"
      description="Research, knowledge management, and information gathering"
      actions={
        <div className="flex items-center gap-2">
          <a
            href="http://192.168.1.244:8888"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(6, 182, 212, 0.1)',
              color: 'var(--hydra-cyan)',
              border: '1px solid var(--hydra-cyan)',
            }}
          >
            SearXNG →
          </a>
          <a
            href="http://192.168.1.244:3030"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(139, 92, 246, 0.1)',
              color: 'var(--hydra-purple)',
              border: '1px solid var(--hydra-purple)',
            }}
          >
            Perplexica →
          </a>
          <a
            href="http://192.168.1.244:8180"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(234, 179, 8, 0.1)',
              color: 'var(--hydra-yellow)',
              border: '1px solid var(--hydra-yellow)',
            }}
          >
            Miniflux →
          </a>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Quick Stats Row */}
        <div className="grid grid-cols-6 gap-3">
          <div
            className="p-3 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
              {stats.totalDocuments.toLocaleString()}
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>Documents</div>
          </div>
          <div
            className="p-3 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-purple)' }}>
              {stats.totalVectors.toLocaleString()}
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>Vectors</div>
          </div>
          <div
            className="p-3 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-green)' }}>
              {stats.searchesLast24h}
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>Searches/24h</div>
          </div>
          <div
            className="p-3 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-magenta)' }}>
              {stats.crawlsLast24h}
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>Crawls/24h</div>
          </div>
          <div
            className="p-3 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-yellow)' }}>
              {stats.feedsActive}
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>Active Feeds</div>
          </div>
          <div
            className="p-3 rounded-lg border text-center"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="text-lg font-bold" style={{ color: 'var(--hydra-red)' }}>
              {stats.unreadArticles}
            </div>
            <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>Unread</div>
          </div>
        </div>

        {/* Search Bar */}
        <div
          className="p-4 rounded-lg border"
          style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
        >
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search knowledge base, web, or start research..."
              className="flex-1 px-4 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.3)',
                border: '1px solid var(--hydra-border)',
                color: 'var(--hydra-text)',
              }}
            />
            <button
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                backgroundColor: 'rgba(6, 182, 212, 0.2)',
                color: 'var(--hydra-cyan)',
                border: '1px solid var(--hydra-cyan)',
              }}
            >
              Search Knowledge
            </button>
            <button
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                backgroundColor: 'rgba(139, 92, 246, 0.2)',
                color: 'var(--hydra-purple)',
                border: '1px solid var(--hydra-purple)',
              }}
            >
              Web Search
            </button>
            <button
              className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              style={{
                backgroundColor: 'rgba(34, 197, 94, 0.2)',
                color: 'var(--hydra-green)',
                border: '1px solid var(--hydra-green)',
              }}
            >
              Start Research
            </button>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* Research Queue */}
          <div className="col-span-2 space-y-4">
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div
                className="px-4 py-3 border-b flex items-center justify-between"
                style={{ borderColor: 'var(--hydra-border)' }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">📚</span>
                  <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
                    Research Queue
                  </span>
                </div>
                <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  {research.filter((r) => r.status === 'researching').length} active
                </span>
              </div>
              <div className="p-4 space-y-3">
                {research.map((topic) => (
                  <div
                    key={topic.id}
                    className="p-3 rounded-lg border"
                    style={{
                      backgroundColor: 'rgba(0, 0, 0, 0.2)',
                      borderColor: 'var(--hydra-border)',
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span
                            className="text-xs px-2 py-0.5 rounded uppercase"
                            style={{
                              backgroundColor: getStatusBg(topic.status),
                              color: getStatusColor(topic.status),
                            }}
                          >
                            {topic.status}
                          </span>
                          <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                            {formatRelativeTime(topic.createdAt)}
                          </span>
                        </div>
                        <p className="text-sm mt-2" style={{ color: 'var(--hydra-text)' }}>
                          {topic.topic}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                          <span>{topic.sources} sources</span>
                          <span>{topic.documentsIngested} docs ingested</span>
                        </div>
                      </div>
                      {topic.status === 'researching' && (
                        <div
                          className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin"
                          style={{ borderColor: 'var(--hydra-cyan)', borderTopColor: 'transparent' }}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Knowledge Collections */}
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div
                className="px-4 py-3 border-b flex items-center justify-between"
                style={{ borderColor: 'var(--hydra-border)' }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">🗃️</span>
                  <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
                    Qdrant Collections
                  </span>
                </div>
                <a
                  href="http://192.168.1.244:6333/dashboard"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs"
                  style={{ color: 'var(--hydra-cyan)' }}
                >
                  Dashboard →
                </a>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-2 gap-3">
                  {collections.map((collection) => (
                    <div
                      key={collection.name}
                      className="p-3 rounded border"
                      style={{
                        backgroundColor: 'rgba(0, 0, 0, 0.2)',
                        borderColor: 'var(--hydra-border)',
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                          {collection.name}
                        </span>
                        <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                          {collection.lastUpdated}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs">
                        <span style={{ color: 'var(--hydra-purple)' }}>
                          {collection.vectors.toLocaleString()} vectors
                        </span>
                        <span style={{ color: 'var(--hydra-text-muted)' }}>{collection.size}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <div className="space-y-4">
            {/* RSS Feeds */}
            <div
              className="rounded-lg border overflow-hidden"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div
                className="px-4 py-3 border-b flex items-center justify-between"
                style={{ borderColor: 'var(--hydra-border)' }}
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">📰</span>
                  <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
                    RSS Feeds
                  </span>
                </div>
                <span
                  className="text-xs px-2 py-0.5 rounded"
                  style={{
                    backgroundColor: 'rgba(255, 51, 102, 0.1)',
                    color: 'var(--hydra-red)',
                  }}
                >
                  {feeds.reduce((sum, f) => sum + f.unreadCount, 0)} unread
                </span>
              </div>
              <div className="p-3 space-y-2 max-h-64 overflow-y-auto">
                {feeds.map((feed) => (
                  <div
                    key={feed.id}
                    className="flex items-center justify-between p-2 rounded"
                    style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
                  >
                    <div>
                      <div className="text-sm" style={{ color: 'var(--hydra-text)' }}>
                        {feed.title}
                      </div>
                      <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                        {feed.category} • {feed.lastFetched}
                      </div>
                    </div>
                    {feed.unreadCount > 0 && (
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: 'rgba(139, 92, 246, 0.2)',
                          color: 'var(--hydra-purple)',
                        }}
                      >
                        {feed.unreadCount}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Firecrawl Status */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🕷️</span>
                  <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
                    Firecrawl
                  </span>
                </div>
                <span
                  className="text-xs px-2 py-0.5 rounded"
                  style={{
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    color: 'var(--hydra-green)',
                  }}
                >
                  READY
                </span>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Crawls Today</span>
                  <span style={{ color: 'var(--hydra-cyan)' }}>{stats.crawlsLast24h}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Queue</span>
                  <span style={{ color: 'var(--hydra-yellow)' }}>3 pending</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Rate Limit</span>
                  <span style={{ color: 'var(--hydra-text)' }}>10 req/min</span>
                </div>
              </div>
            </div>

            {/* Docling Status */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">📄</span>
                  <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
                    Docling
                  </span>
                </div>
                <span
                  className="text-xs px-2 py-0.5 rounded"
                  style={{
                    backgroundColor: 'rgba(0, 255, 136, 0.1)',
                    color: 'var(--hydra-green)',
                  }}
                >
                  READY
                </span>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Processed Today</span>
                  <span style={{ color: 'var(--hydra-cyan)' }}>12 docs</span>
                </div>
                <div className="flex items-center justify-between">
                  <span style={{ color: 'var(--hydra-text-muted)' }}>Formats</span>
                  <span style={{ color: 'var(--hydra-text)' }}>PDF, DOCX, HTML</span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
                Quick Actions
              </div>
              <div className="space-y-2">
                <button
                  className="w-full px-3 py-2 rounded text-sm text-left transition-colors"
                  style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                    color: 'var(--hydra-text)',
                    border: '1px solid var(--hydra-border)',
                  }}
                >
                  Crawl URL...
                </button>
                <button
                  className="w-full px-3 py-2 rounded text-sm text-left transition-colors"
                  style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                    color: 'var(--hydra-text)',
                    border: '1px solid var(--hydra-border)',
                  }}
                >
                  Upload Document...
                </button>
                <button
                  className="w-full px-3 py-2 rounded text-sm text-left transition-colors"
                  style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                    color: 'var(--hydra-text)',
                    border: '1px solid var(--hydra-border)',
                  }}
                >
                  Add RSS Feed...
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DomainView>
  );
}
