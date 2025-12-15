'use client';

import { useEffect, useRef, useState } from 'react';
import { StatusIndicator } from './StatusIndicator';
import { UptimeSparkline } from './Sparkline';
import { ServiceDetailed } from '@/lib/api';

const MAX_HISTORY = 20; // Keep last 20 data points (~100 seconds at 5s intervals)

// Service descriptions for tooltips
const serviceDescriptions: Record<string, { description: string; category: string; url?: string }> = {
  prometheus: {
    description: 'Metrics collection and alerting system. Scrapes metrics from all cluster nodes and services.',
    category: 'Monitoring',
    url: 'http://192.168.1.244:9090',
  },
  alertmanager: {
    description: 'Handles alerts from Prometheus. Routes notifications to Discord and other channels.',
    category: 'Monitoring',
    url: 'http://192.168.1.244:9093',
  },
  grafana: {
    description: 'Visualization and dashboards for Prometheus metrics. GPU, CPU, memory, and storage monitoring.',
    category: 'Monitoring',
    url: 'http://192.168.1.244:3003',
  },
  letta: {
    description: 'AI agent framework powering the hydra-steward. Provides conversational control and automation.',
    category: 'AI',
    url: 'http://192.168.1.244:8283',
  },
  ollama: {
    description: 'Local LLM inference server. Hosts AI models like Qwen, Llama, and Mistral on cluster GPUs.',
    category: 'AI',
    url: 'http://192.168.1.203:11434',
  },
  litellm: {
    description: 'OpenAI-compatible API proxy. Unified interface for all AI models in the cluster.',
    category: 'AI',
    url: 'http://192.168.1.244:4000',
  },
  qdrant: {
    description: 'Vector database for AI embeddings. Stores semantic search indices and agent memory.',
    category: 'AI',
    url: 'http://192.168.1.244:6333',
  },
  'open-webui': {
    description: 'Web interface for interacting with Ollama models. Chat UI with model selection.',
    category: 'AI',
    url: 'http://192.168.1.250:3000',
  },
  openwebui: {
    description: 'Web interface for interacting with Ollama models. Chat UI with model selection.',
    category: 'AI',
    url: 'http://192.168.1.250:3000',
  },
  n8n: {
    description: 'Workflow automation platform. Connects services and triggers automated tasks.',
    category: 'Automation',
    url: 'http://192.168.1.244:5678',
  },
  'uptime-kuma': {
    description: 'Uptime monitoring dashboard. Tracks availability of all services and sends alerts.',
    category: 'Monitoring',
    url: 'http://192.168.1.244:3001',
  },
  watchtower: {
    description: 'Automatic container updates. Monitors Docker Hub for new images and updates containers.',
    category: 'Infrastructure',
  },
  traefik: {
    description: 'Reverse proxy and load balancer. Routes traffic to containers with automatic SSL.',
    category: 'Infrastructure',
    url: 'http://192.168.1.244:8080',
  },
  'hydra-mcp': {
    description: 'Hydra Master Control Program. Central API for cluster management and orchestration.',
    category: 'Core',
    url: 'http://192.168.1.244:8600',
  },
  comfyui: {
    description: 'Stable Diffusion workflow UI. Node-based image generation with custom pipelines.',
    category: 'AI',
    url: 'http://192.168.1.203:8188',
  },
  'a1111': {
    description: 'AUTOMATIC1111 Stable Diffusion WebUI. Feature-rich image generation interface.',
    category: 'AI',
    url: 'http://192.168.1.250:7860',
  },
  invokeai: {
    description: 'InvokeAI image generation. Professional Stable Diffusion interface with unified canvas.',
    category: 'AI',
    url: 'http://192.168.1.250:9090',
  },
  whisper: {
    description: 'OpenAI Whisper speech-to-text. Transcribes audio with high accuracy.',
    category: 'AI',
  },
  plex: {
    description: 'Media server for movies, TV, and music. Streams content to any device.',
    category: 'Media',
    url: 'http://192.168.1.244:32400',
  },
  tautulli: {
    description: 'Plex monitoring and statistics. Tracks viewing history and server performance.',
    category: 'Media',
    url: 'http://192.168.1.244:8181',
  },
};

interface ServiceListProps {
  services: Record<string, string>;
  detailed?: ServiceDetailed;
}

function formatUptime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
}

export function ServiceList({ services, detailed }: ServiceListProps) {
  // Store history for each service
  const historyRef = useRef<Record<string, boolean[]>>({});
  const [hoveredService, setHoveredService] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const getStatus = (value: string): 'online' | 'offline' | 'warning' => {
    if (value === 'up') return 'online';
    if (value === 'down') return 'offline';
    if (value.includes('status:')) return 'warning';
    return 'offline';
  };

  const isUp = (value: string): boolean => {
    return value === 'up';
  };

  const getServiceInfo = (name: string) => {
    // Try exact match first, then lowercase
    return serviceDescriptions[name] || serviceDescriptions[name.toLowerCase()] || null;
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'AI': return 'text-hydra-magenta';
      case 'Monitoring': return 'text-hydra-cyan';
      case 'Automation': return 'text-hydra-yellow';
      case 'Infrastructure': return 'text-hydra-green';
      case 'Core': return 'text-hydra-cyan';
      case 'Media': return 'text-purple-400';
      default: return 'text-gray-400';
    }
  };

  // Update history whenever services change
  useEffect(() => {
    Object.entries(services).forEach(([name, status]) => {
      if (!historyRef.current[name]) {
        historyRef.current[name] = [];
      }
      const history = historyRef.current[name];
      history.push(isUp(status));
      // Keep only the last MAX_HISTORY entries
      if (history.length > MAX_HISTORY) {
        history.shift();
      }
    });
  }, [services]);

  // Get unique categories
  const categories = Array.from(new Set(
    Object.keys(services)
      .map(name => getServiceInfo(name)?.category)
      .filter((c): c is string => c !== null && c !== undefined)
  )).sort();

  // Filter services
  const filteredServices = Object.entries(services).filter(([name, status]) => {
    // Search filter
    if (searchQuery) {
      const info = getServiceInfo(name);
      const searchLower = searchQuery.toLowerCase();
      const matchesName = name.toLowerCase().includes(searchLower);
      const matchesCategory = info?.category?.toLowerCase().includes(searchLower);
      const matchesDesc = info?.description?.toLowerCase().includes(searchLower);
      if (!matchesName && !matchesCategory && !matchesDesc) {
        return false;
      }
    }
    // Category filter
    if (categoryFilter) {
      const info = getServiceInfo(name);
      if (info?.category !== categoryFilter) {
        return false;
      }
    }
    return true;
  });

  const onlineCount = Object.values(services).filter(s => s === 'up').length;
  const totalCount = Object.keys(services).length;

  return (
    <div className="panel">
      <div className="panel-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-hydra-cyan">&#9632;</span>
          Services ({onlineCount}/{totalCount} online)
        </div>
      </div>

      {/* Search and Filter */}
      <div className="px-3 py-2 border-b border-hydra-gray/30 space-y-2">
        <div className="relative">
          <input
            type="text"
            placeholder="Search services..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-hydra-darker border border-hydra-gray/30 rounded px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:border-hydra-cyan/50 focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => setCategoryFilter(null)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              categoryFilter === null
                ? 'bg-hydra-cyan/30 text-hydra-cyan border border-hydra-cyan/50'
                : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
            }`}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                categoryFilter === cat
                  ? `${getCategoryColor(cat).replace('text-', 'bg-').replace('hydra-', 'hydra-').replace('-400', '')}/30 ${getCategoryColor(cat)} border border-current/50`
                  : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 space-y-2 max-h-[400px] overflow-y-auto">
        {filteredServices.length === 0 && (
          <div className="text-center py-4 text-gray-500 text-sm">
            No services match filters
          </div>
        )}
        {filteredServices.map(([name, status]) => {
          const uptimeSeconds = detailed?.[name]?.uptime_seconds;
          const uptimeStr = formatUptime(uptimeSeconds);
          const serviceInfo = getServiceInfo(name);
          const isHovered = hoveredService === name;
          return (
            <div
              key={name}
              className="relative"
              onMouseEnter={() => setHoveredService(name)}
              onMouseLeave={() => setHoveredService(null)}
            >
              <div className="flex justify-between items-center py-1.5 border-b border-hydra-gray/30 last:border-0 cursor-pointer hover:bg-hydra-gray/10 -mx-2 px-2 rounded transition-colors">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-sm text-gray-300 font-mono truncate">{name}</span>
                  {serviceInfo && (
                    <span className={`text-[10px] uppercase tracking-wider ${getCategoryColor(serviceInfo.category)}`}>
                      {serviceInfo.category}
                    </span>
                  )}
                  <UptimeSparkline
                    history={historyRef.current[name] || []}
                    width={50}
                    height={10}
                  />
                  {uptimeStr && (
                    <span className="text-xs text-gray-500" title={`Uptime: ${uptimeSeconds}s`}>
                      {uptimeStr}
                    </span>
                  )}
                </div>
                <StatusIndicator status={getStatus(status)} label={status} pulse={false} />
              </div>

              {/* Tooltip */}
              {isHovered && serviceInfo && (
                <div className="absolute left-0 right-0 z-10 mt-1 p-3 bg-hydra-darker border border-hydra-gray/50 rounded-lg shadow-xl animate-in fade-in duration-150">
                  <p className="text-xs text-gray-300 mb-2">{serviceInfo.description}</p>
                  {serviceInfo.url && (
                    <a
                      href={serviceInfo.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-hydra-cyan hover:underline flex items-center gap-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      Open {serviceInfo.url}
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
