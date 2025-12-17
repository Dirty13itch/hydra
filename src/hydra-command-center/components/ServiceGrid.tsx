import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, Badge, Button, StatusDot } from './UIComponents';
import { getUnifiedServices, getServicesHealthSummary, createServicesEventSource, UnifiedService, ServiceStatusUpdate } from '../services/hydraApi';
import {
  RefreshCw,
  Loader2,
  ExternalLink,
  Server,
  Cpu,
  HardDrive,
  Activity,
  Zap,
  Eye,
  Layers,
  Grid,
  List,
  Search,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Monitor,
} from 'lucide-react';

// Category icon mapping
const categoryIcons: Record<string, React.ReactNode> = {
  inference: <Cpu size={16} />,
  media: <Monitor size={16} />,
  downloads: <HardDrive size={16} />,
  automation: <Zap size={16} />,
  observability: <Activity size={16} />,
  infrastructure: <Server size={16} />,
};

// Category color mapping
const categoryColors: Record<string, string> = {
  inference: 'from-purple-500/20 to-purple-600/10 border-purple-500/30',
  media: 'from-blue-500/20 to-blue-600/10 border-blue-500/30',
  downloads: 'from-amber-500/20 to-amber-600/10 border-amber-500/30',
  automation: 'from-cyan-500/20 to-cyan-600/10 border-cyan-500/30',
  observability: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30',
  infrastructure: 'from-neutral-500/20 to-neutral-600/10 border-neutral-500/30',
};

// Status to color mapping
const statusToVariant = (status: string): 'emerald' | 'red' | 'neutral' => {
  switch (status) {
    case 'healthy':
      return 'emerald';
    case 'unhealthy':
      return 'red';
    default:
      return 'neutral';
  }
};

// Get status icon
const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  switch (status) {
    case 'healthy':
      return <CheckCircle2 size={14} className="text-emerald-500" />;
    case 'unhealthy':
      return <XCircle size={14} className="text-red-500" />;
    default:
      return <HelpCircle size={14} className="text-neutral-500" />;
  }
};

interface ServiceCardProps {
  service: UnifiedService;
}

const ServiceCard: React.FC<ServiceCardProps> = ({ service }) => {
  const handleClick = () => {
    window.open(service.url, '_blank', 'noopener,noreferrer');
  };

  return (
    <div
      onClick={handleClick}
      className="group relative bg-surface-raised border border-neutral-800 rounded-lg p-4 cursor-pointer hover:bg-surface-highlight hover:border-neutral-700 transition-all duration-200"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <StatusIcon status={service.status} />
          <span className="font-medium text-neutral-200 truncate">{service.name}</span>
        </div>
        <ExternalLink size={14} className="text-neutral-600 group-hover:text-neutral-400 transition-colors shrink-0" />
      </div>

      {service.description && (
        <p className="text-xs text-neutral-500 line-clamp-2 mb-3">{service.description}</p>
      )}

      <div className="flex items-center justify-between text-[10px] text-neutral-600">
        <span className="uppercase font-mono">{service.node}</span>
        {service.latency_ms !== undefined && service.latency_ms !== null && (
          <span className={service.latency_ms < 100 ? 'text-emerald-500' : service.latency_ms < 500 ? 'text-amber-500' : 'text-red-500'}>
            {service.latency_ms.toFixed(0)}ms
          </span>
        )}
        {service.source === 'hydra' && (
          <Badge variant="cyan">MONITORED</Badge>
        )}
      </div>
    </div>
  );
};

interface CategoryGroupProps {
  category: string;
  services: UnifiedService[];
}

const CategoryGroup: React.FC<CategoryGroupProps> = ({ category, services }) => {
  const healthyCount = services.filter(s => s.status === 'healthy').length;
  const totalCount = services.length;
  const categoryColor = categoryColors[category] || categoryColors.infrastructure;

  return (
    <div className={`rounded-xl border bg-gradient-to-br ${categoryColor} p-4`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-neutral-900/50 rounded-lg text-neutral-400">
            {categoryIcons[category] || <Layers size={16} />}
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-neutral-200 uppercase">
              {category.replace(/_/g, ' ')}
            </h3>
            <span className="text-[10px] text-neutral-500">
              {healthyCount}/{totalCount} healthy
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {services.map(service => (
          <ServiceCard key={service.id} service={service} />
        ))}
      </div>
    </div>
  );
};

interface HealthSummary {
  homepage_services: number;
  monitored_services: number;
  healthy: number;
  unhealthy: number;
  unmonitored: number;
  health_percentage: number;
  timestamp: string;
}

export const ServiceGrid: React.FC = () => {
  const [services, setServices] = useState<UnifiedService[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [summary, setSummary] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchFilter, setSearchFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [nodeFilter, setNodeFilter] = useState<string>('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isLive, setIsLive] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const eventSourceRef = useRef<EventSource | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [servicesResult, summaryResult] = await Promise.all([
        getUnifiedServices(),
        getServicesHealthSummary(),
      ]);

      if (servicesResult.data) {
        setServices(servicesResult.data.services);
        setCategories(servicesResult.data.categories);
      }
      if (summaryResult.data) {
        setSummary(summaryResult.data);
      }
    } catch (err) {
      console.error('Failed to fetch services:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // SSE for real-time updates
  useEffect(() => {
    // Connect to SSE stream
    const eventSource = createServicesEventSource(
      (update: ServiceStatusUpdate) => {
        if (update.type === 'status_update' && update.services) {
          // Update service statuses in place
          setServices(prevServices =>
            prevServices.map(svc => {
              const statusUpdate = update.services?.[svc.id];
              if (statusUpdate) {
                return {
                  ...svc,
                  status: statusUpdate.status as 'healthy' | 'unhealthy' | 'unknown',
                  latency_ms: statusUpdate.latency_ms ?? undefined,
                };
              }
              return svc;
            })
          );

          // Update summary
          if (update.summary) {
            setSummary(prev => ({
              homepage_services: update.summary?.total ?? prev?.homepage_services ?? 0,
              monitored_services: update.summary?.monitored ?? prev?.monitored_services ?? 0,
              healthy: update.summary?.healthy ?? prev?.healthy ?? 0,
              unhealthy: update.summary?.unhealthy ?? prev?.unhealthy ?? 0,
              unmonitored: (update.summary?.total ?? 0) - (update.summary?.monitored ?? 0),
              health_percentage: update.summary?.health_percentage ?? prev?.health_percentage ?? 0,
              timestamp: update.timestamp,
            }));
          }

          setLastUpdate(update.timestamp);
          setIsLive(true);
        }
      },
      (error) => {
        console.error('SSE error:', error);
        setIsLive(false);
      }
    );

    eventSourceRef.current = eventSource;

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      setIsLive(false);
    };
  }, []);

  // Fallback polling every 60 seconds if SSE fails
  useEffect(() => {
    if (!isLive) {
      const interval = setInterval(fetchData, 60000);
      return () => clearInterval(interval);
    }
  }, [fetchData, isLive]);

  // Filter services
  const filteredServices = services.filter(service => {
    if (searchFilter && !service.name.toLowerCase().includes(searchFilter.toLowerCase())) {
      return false;
    }
    if (categoryFilter && service.category !== categoryFilter) {
      return false;
    }
    if (nodeFilter && service.node !== nodeFilter) {
      return false;
    }
    return true;
  });

  // Group by category
  const servicesByCategory = categories.reduce((acc, cat) => {
    const catServices = filteredServices.filter(s => s.category === cat);
    if (catServices.length > 0) {
      acc[cat] = catServices;
    }
    return acc;
  }, {} as Record<string, UnifiedService[]>);

  // Get unique nodes
  const nodes = [...new Set(services.map(s => s.node))];

  if (loading && services.length === 0) {
    return (
      <div className="p-8 text-center">
        <Loader2 className="animate-spin mx-auto mb-2 text-neutral-500" />
        <p className="text-neutral-500">Loading services...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Card className="border-neutral-800">
            <div className="text-center">
              <div className="text-2xl font-bold text-neutral-200">{summary.homepage_services}</div>
              <div className="text-[10px] text-neutral-500 uppercase">Total Services</div>
            </div>
          </Card>
          <Card className="border-neutral-800">
            <div className="text-center">
              <div className="text-2xl font-bold text-emerald-400">{summary.healthy}</div>
              <div className="text-[10px] text-neutral-500 uppercase">Healthy</div>
            </div>
          </Card>
          <Card className="border-neutral-800">
            <div className="text-center">
              <div className="text-2xl font-bold text-red-400">{summary.unhealthy}</div>
              <div className="text-[10px] text-neutral-500 uppercase">Unhealthy</div>
            </div>
          </Card>
          <Card className="border-neutral-800">
            <div className="text-center">
              <div className="text-2xl font-bold text-cyan-400">{summary.monitored_services}</div>
              <div className="text-[10px] text-neutral-500 uppercase">Monitored</div>
            </div>
          </Card>
          <Card className="border-neutral-800">
            <div className="text-center">
              <div className="text-2xl font-bold text-amber-400">{summary.unmonitored}</div>
              <div className="text-[10px] text-neutral-500 uppercase">Unmonitored</div>
            </div>
          </Card>
          <Card className="border-neutral-800">
            <div className="text-center">
              <div className={`text-2xl font-bold ${summary.health_percentage >= 80 ? 'text-emerald-400' : summary.health_percentage >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                {summary.health_percentage}%
              </div>
              <div className="text-[10px] text-neutral-500 uppercase">Health Score</div>
            </div>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card className="border-neutral-800">
        <div className="flex flex-wrap items-center gap-4">
          {/* Search */}
          <div className="flex-1 min-w-[200px] relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input
              type="text"
              placeholder="Search services..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-neutral-900 border border-neutral-700 rounded pl-9 pr-3 py-1.5 text-sm text-neutral-300 outline-none focus:border-cyan-500"
            />
          </div>

          {/* Category Filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-neutral-900 border border-neutral-700 rounded px-3 py-1.5 text-sm text-neutral-300 outline-none focus:border-cyan-500"
          >
            <option value="">All Categories</option>
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat.replace(/_/g, ' ').toUpperCase()}</option>
            ))}
          </select>

          {/* Node Filter */}
          <select
            value={nodeFilter}
            onChange={(e) => setNodeFilter(e.target.value)}
            className="bg-neutral-900 border border-neutral-700 rounded px-3 py-1.5 text-sm text-neutral-300 outline-none focus:border-cyan-500"
          >
            <option value="">All Nodes</option>
            {nodes.map(node => (
              <option key={node} value={node}>{node}</option>
            ))}
          </select>

          {/* View Toggle */}
          <div className="flex items-center gap-1 border border-neutral-700 rounded p-0.5">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-neutral-700 text-white' : 'text-neutral-500 hover:text-neutral-300'}`}
            >
              <Grid size={16} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-neutral-700 text-white' : 'text-neutral-500 hover:text-neutral-300'}`}
            >
              <List size={16} />
            </button>
          </div>

          {/* Live Status Indicator */}
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono ${isLive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
            <span className={`h-2 w-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
            {isLive ? 'LIVE' : 'POLLING'}
          </div>

          {/* Refresh */}
          <Button
            variant="secondary"
            size="sm"
            icon={loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            onClick={fetchData}
          >
            Refresh
          </Button>
        </div>
      </Card>

      {/* Service Grid by Category */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {Object.entries(servicesByCategory).map(([category, catServices]) => (
            <CategoryGroup key={category} category={category} services={catServices} />
          ))}
        </div>
      ) : (
        /* List View */
        <Card className="border-neutral-800">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-xs font-mono text-neutral-500 border-b border-neutral-800">
                <th className="p-3 font-medium">STATUS</th>
                <th className="p-3 font-medium">SERVICE</th>
                <th className="p-3 font-medium">CATEGORY</th>
                <th className="p-3 font-medium">NODE</th>
                <th className="p-3 font-medium">LATENCY</th>
                <th className="p-3 font-medium">SOURCE</th>
                <th className="p-3 font-medium text-right">LINK</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {filteredServices.map(svc => (
                <tr key={svc.id} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors">
                  <td className="p-3">
                    <StatusIcon status={svc.status} />
                  </td>
                  <td className="p-3">
                    <div className="font-medium text-neutral-300">{svc.name}</div>
                    {svc.description && (
                      <div className="text-xs text-neutral-500 truncate max-w-[200px]">{svc.description}</div>
                    )}
                  </td>
                  <td className="p-3 text-neutral-400 text-xs uppercase">{svc.category}</td>
                  <td className="p-3 text-neutral-400 font-mono text-xs">{svc.node}</td>
                  <td className="p-3">
                    {svc.latency_ms !== undefined && svc.latency_ms !== null ? (
                      <span className={`text-xs font-mono ${svc.latency_ms < 100 ? 'text-emerald-400' : svc.latency_ms < 500 ? 'text-amber-400' : 'text-red-400'}`}>
                        {svc.latency_ms.toFixed(0)}ms
                      </span>
                    ) : (
                      <span className="text-neutral-600">-</span>
                    )}
                  </td>
                  <td className="p-3">
                    <Badge variant={svc.source === 'hydra' ? 'cyan' : 'neutral'}>
                      {svc.source.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="p-3 text-right">
                    <a
                      href={svc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-neutral-500 hover:text-cyan-400 transition-colors"
                    >
                      <ExternalLink size={14} />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredServices.length === 0 && (
            <div className="p-8 text-center text-neutral-500">
              No services match your filters
            </div>
          )}
        </Card>
      )}

      {Object.keys(servicesByCategory).length === 0 && viewMode === 'grid' && (
        <Card className="border-neutral-800">
          <div className="p-8 text-center text-neutral-500">
            No services match your filters
          </div>
        </Card>
      )}
    </div>
  );
};

export default ServiceGrid;
