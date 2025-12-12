'use client';

import { useState, useEffect } from 'react';

interface GlossaryEntry {
  name: string;
  category: 'infrastructure' | 'monitoring' | 'ai' | 'storage' | 'automation';
  description: string;
  port?: number;
  url?: string;
}

interface HelpGlossaryProps {
  externalOpen?: boolean;
  onClose?: () => void;
}

const glossary: GlossaryEntry[] = [
  // Infrastructure
  { name: 'MCP Server', category: 'infrastructure', description: 'Master Control Program - REST API that orchestrates all cluster operations. Provides endpoints for container management, metrics aggregation, and service health checks.', port: 8600 },
  { name: 'hydra-ai', category: 'infrastructure', description: 'Primary inference node with RTX 5090 + RTX 4090 GPUs. Runs TabbyAPI for high-performance LLM inference.' },
  { name: 'hydra-compute', category: 'infrastructure', description: 'Secondary compute node with RTX 5070 Ti + RTX 3060 GPUs. Runs ComfyUI for image generation and Ollama for local models.' },
  { name: 'hydra-storage', category: 'infrastructure', description: 'Storage and orchestration node running Unraid. Hosts Docker containers, 180TB storage array, and the MCP server.' },

  // Monitoring
  { name: 'Prometheus', category: 'monitoring', description: 'Time-series metrics database. Collects and stores metrics from all nodes via node_exporter. Powers Grafana dashboards and alerting.', port: 9090 },
  { name: 'Grafana', category: 'monitoring', description: 'Visualization platform for metrics. Contains dashboards for cluster health, GPU status, and container metrics.', port: 3003, url: 'http://192.168.1.244:3003' },
  { name: 'Alertmanager', category: 'monitoring', description: 'Alert routing and notification service. Receives alerts from Prometheus and forwards to Discord/MCP.', port: 9093 },
  { name: 'Loki', category: 'monitoring', description: 'Log aggregation system. Collects logs from all containers for centralized viewing in Grafana.', port: 3100 },
  { name: 'Uptime Kuma', category: 'monitoring', description: 'Service uptime monitoring with historical status tracking. Shows availability percentages and response times.', port: 3004, url: 'http://192.168.1.244:3004' },

  // AI Services
  { name: 'LiteLLM', category: 'ai', description: 'Unified LLM API gateway. Routes requests to local (Ollama/TabbyAPI) or cloud models through a single OpenAI-compatible interface.', port: 4000 },
  { name: 'Ollama', category: 'ai', description: 'Local LLM inference server running on hydra-compute. Hosts models like Mistral, Qwen, and embedding models.', port: 11434 },
  { name: 'TabbyAPI', category: 'ai', description: 'High-performance inference server on hydra-ai. Optimized for large models using ExLlama2 quantization.', port: 5000 },
  { name: 'Letta', category: 'ai', description: 'Stateful AI agent framework (formerly MemGPT). Provides persistent memory and tool use for the hydra-steward agent.', port: 8283 },
  { name: 'Open WebUI', category: 'ai', description: 'Web-based chat interface for AI models. Connects to LiteLLM/Ollama backends for interactive conversations.', port: 3001, url: 'http://192.168.1.244:3001' },
  { name: 'Qdrant', category: 'ai', description: 'Vector database for semantic search. Stores embeddings for RAG (retrieval-augmented generation) workflows.', port: 6333 },

  // Storage
  { name: 'Storage Pools', category: 'storage', description: 'Unraid storage arrays. Main array uses parity protection, cache pool provides fast SSD storage for containers and active workloads.' },
  { name: 'PostgreSQL', category: 'storage', description: 'Relational database used by Letta, n8n, and other services for persistent data storage.', port: 5432 },
  { name: 'Redis', category: 'storage', description: 'In-memory data store used for caching, session storage, and message queuing.', port: 6379 },

  // Automation
  { name: 'n8n', category: 'automation', description: 'Workflow automation platform. Creates automated pipelines connecting services, APIs, and AI models.', port: 5678, url: 'http://192.168.1.244:5678' },
  { name: 'Watchtower', category: 'automation', description: 'Automatic container updater. Monitors Docker images for updates and applies them automatically.' },
];

const categoryColors: Record<string, { bg: string; text: string; label: string }> = {
  infrastructure: { bg: 'bg-hydra-cyan/20', text: 'text-hydra-cyan', label: 'Infrastructure' },
  monitoring: { bg: 'bg-hydra-green/20', text: 'text-hydra-green', label: 'Monitoring' },
  ai: { bg: 'bg-hydra-magenta/20', text: 'text-hydra-magenta', label: 'AI Services' },
  storage: { bg: 'bg-hydra-yellow/20', text: 'text-hydra-yellow', label: 'Storage' },
  automation: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'Automation' },
};

export function HelpGlossary({ externalOpen, onClose }: HelpGlossaryProps = {}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);

  // Support both controlled and uncontrolled modes
  const isOpen = externalOpen !== undefined ? externalOpen : internalOpen;
  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      setInternalOpen(false);
    }
  };
  const handleOpen = () => setInternalOpen(true);

  const filteredGlossary = filter
    ? glossary.filter(entry => entry.category === filter)
    : glossary;

  return (
    <>
      {/* Help Button - only show if uncontrolled mode */}
      {externalOpen === undefined && (
        <button
          onClick={handleOpen}
          className="fixed bottom-4 left-4 w-12 h-12 bg-hydra-darker border border-hydra-cyan/50 rounded-full flex items-center justify-center hover:bg-hydra-cyan/20 transition-colors shadow-lg z-40"
          title="Help / Glossary (Press ?)"
        >
          <svg className="w-5 h-5 text-hydra-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      )}

      {/* Modal */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-hydra-darker border border-hydra-cyan/30 rounded-lg w-full max-w-4xl max-h-[80vh] flex flex-col shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-hydra-gray/30">
              <h2 className="text-xl font-bold text-hydra-cyan">Help / Service Glossary</h2>
              <button
                onClick={handleClose}
                className="text-gray-400 hover:text-white p-1"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Category Filters */}
            <div className="flex gap-2 p-4 border-b border-hydra-gray/30 flex-wrap">
              <button
                onClick={() => setFilter(null)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  filter === null ? 'bg-hydra-cyan text-black' : 'bg-hydra-gray/30 text-gray-400 hover:text-white'
                }`}
              >
                All
              </button>
              {Object.entries(categoryColors).map(([key, { bg, text, label }]) => (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    filter === key ? `${bg} ${text}` : 'bg-hydra-gray/30 text-gray-400 hover:text-white'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-3">
                {filteredGlossary.map((entry) => {
                  const cat = categoryColors[entry.category];
                  return (
                    <div key={entry.name} className="bg-hydra-dark/50 border border-hydra-gray/30 rounded-lg p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-bold text-white">{entry.name}</span>
                            <span className={`px-2 py-0.5 rounded text-xs ${cat.bg} ${cat.text}`}>
                              {cat.label}
                            </span>
                            {entry.port && (
                              <span className="px-2 py-0.5 rounded text-xs bg-hydra-gray/30 text-gray-400 font-mono">
                                :{entry.port}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-400">{entry.description}</p>
                        </div>
                        {entry.url && (
                          <a
                            href={entry.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1 bg-hydra-cyan/20 text-hydra-cyan rounded text-xs hover:bg-hydra-cyan/30 transition-colors flex items-center gap-1"
                          >
                            Open
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Footer with Quick Links */}
            <div className="border-t border-hydra-gray/30 p-4">
              <div className="text-xs text-gray-500 mb-2">Quick Links to Dashboards:</div>
              <div className="flex gap-2 flex-wrap">
                <a href="http://192.168.1.244:3003" target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 bg-hydra-green/20 text-hydra-green rounded text-xs hover:bg-hydra-green/30 transition-colors">Grafana</a>
                <a href="http://192.168.1.244:3004" target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 bg-hydra-cyan/20 text-hydra-cyan rounded text-xs hover:bg-hydra-cyan/30 transition-colors">Uptime Kuma</a>
                <a href="http://192.168.1.244:3001" target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 bg-hydra-magenta/20 text-hydra-magenta rounded text-xs hover:bg-hydra-magenta/30 transition-colors">Open WebUI</a>
                <a href="http://192.168.1.244:5678" target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 bg-blue-500/20 text-blue-400 rounded text-xs hover:bg-blue-500/30 transition-colors">n8n</a>
                <a href="http://192.168.1.244:9090" target="_blank" rel="noopener noreferrer" className="px-3 py-1.5 bg-hydra-yellow/20 text-hydra-yellow rounded text-xs hover:bg-hydra-yellow/30 transition-colors">Prometheus</a>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// Export service descriptions for use in other components
export const serviceDescriptions: Record<string, string> = {
  'prometheus': 'Metrics collection and storage',
  'grafana': 'Metrics visualization dashboards',
  'alertmanager': 'Alert routing and notifications',
  'loki': 'Log aggregation system',
  'postgres': 'Relational database',
  'postgresql': 'Relational database',
  'redis': 'In-memory cache and message broker',
  'qdrant': 'Vector database for embeddings',
  'litellm': 'Unified LLM API gateway',
  'ollama': 'Local LLM inference server',
  'tabby': 'High-performance inference (ExLlama2)',
  'letta': 'Stateful AI agent framework',
  'open-webui': 'Web chat interface for AI',
  'n8n': 'Workflow automation platform',
  'watchtower': 'Auto container updates',
  'uptime-kuma': 'Service uptime monitoring',
  'adguard': 'DNS filtering and ad blocking',
  'miniflux': 'RSS feed reader',
  'homepage': 'Dashboard aggregator',
  'mcp': 'Master Control Program API',
};
