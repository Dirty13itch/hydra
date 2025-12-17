import React, { useState, useEffect, useCallback } from 'react';
import { Card, Badge, ProgressBar, StatusDot, Tabs, Button } from '../components/UIComponents';
import { useDashboardData } from '../context/DashboardDataContext';
import { queryLogs, getLogsServices, getLogsHealth, LogEntry } from '../services/hydraApi';
import { Server, Activity, RefreshCw, Power, Loader2, Search, Filter, AlertTriangle, Info, Bug, AlertCircle, Terminal, Clock } from 'lucide-react';

export const Infra: React.FC = () => {
  const { nodes, services, nodesLoading, servicesLoading, refreshNodes, refreshServices } = useDashboardData();
  const [activeTab, setActiveTab] = useState('NODES');

  // Logs state
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsServices, setLogsServices] = useState<string[]>([]);
  const [lokiHealthy, setLokiHealthy] = useState(false);
  const [logsTotal, setLogsTotal] = useState(0);

  // Logs filters
  const [serviceFilter, setServiceFilter] = useState<string>('');
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [hoursFilter, setHoursFilter] = useState<number>(1);

  const tabs = [
    { id: 'NODES', label: 'Nodes & Resources' },
    { id: 'SERVICES', label: 'Services & Containers' },
    { id: 'LOGS', label: 'Cluster Logs' }
  ];

  const fetchLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const result = await queryLogs({
        service: serviceFilter || undefined,
        level: levelFilter || undefined,
        search: searchFilter || undefined,
        hours: hoursFilter,
        limit: 200,
      });

      if (result.data) {
        setLogs(result.data.logs);
        setLogsTotal(result.data.total);
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    } finally {
      setLogsLoading(false);
    }
  }, [serviceFilter, levelFilter, searchFilter, hoursFilter]);

  const fetchLogsServices = useCallback(async () => {
    try {
      const [servicesResult, healthResult] = await Promise.all([
        getLogsServices(),
        getLogsHealth(),
      ]);

      if (servicesResult.data) {
        setLogsServices(servicesResult.data.services);
      }
      if (healthResult.data) {
        setLokiHealthy(healthResult.data.ready ?? false);
      }
    } catch (err) {
      console.error('Failed to fetch logs services:', err);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'LOGS') {
      fetchLogsServices();
      fetchLogs();
    }
  }, [activeTab, fetchLogs, fetchLogsServices]);

  const handleRefresh = async () => {
    if (activeTab === 'NODES') {
      await refreshNodes();
    } else if (activeTab === 'SERVICES') {
      await refreshServices();
    } else if (activeTab === 'LOGS') {
      await fetchLogs();
    }
  };

  const isLoading = activeTab === 'NODES' ? nodesLoading : activeTab === 'SERVICES' ? servicesLoading : logsLoading;

  const getLevelIcon = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return <AlertCircle size={12} className="text-red-500" />;
      case 'WARN':
        return <AlertTriangle size={12} className="text-amber-500" />;
      case 'DEBUG':
        return <Bug size={12} className="text-purple-500" />;
      default:
        return <Info size={12} className="text-cyan-500" />;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-400 bg-red-500/10';
      case 'WARN':
        return 'text-amber-400 bg-amber-500/10';
      case 'DEBUG':
        return 'text-purple-400 bg-purple-500/10';
      default:
        return 'text-cyan-400 bg-cyan-500/10';
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 pt-6 pb-2 flex justify-between items-end border-b border-neutral-800">
        <div>
          <h2 className="text-2xl font-mono font-bold text-neutral-200">INFRASTRUCTURE</h2>
          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} className="mt-4" />
        </div>
        <div className="pb-2 flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            icon={isLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            onClick={handleRefresh}
          >
            Refresh
          </Button>
        </div>
      </div>

      <div className="p-6 overflow-y-auto flex-1">

        {/* NODES TAB */}
        {activeTab === 'NODES' && (
          <div className="space-y-6">
            {nodesLoading && nodes.length === 0 ? (
              <div className="space-y-6">
                {[1, 2, 3].map(i => (
                  <Card key={i} className="border-neutral-800 animate-pulse">
                    <div className="h-8 bg-neutral-800 rounded w-1/3 mb-4" />
                    <div className="h-4 bg-neutral-800 rounded w-2/3 mb-2" />
                    <div className="h-20 bg-neutral-800 rounded" />
                  </Card>
                ))}
              </div>
            ) : (
              nodes.map(node => (
                <Card key={node.id} className="border-neutral-800">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 border-b border-neutral-800 pb-4">
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-neutral-800 rounded-lg text-neutral-400">
                        <Server size={24} />
                      </div>
                      <div>
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-bold font-mono text-neutral-200">{node.name}</h3>
                          <Badge variant={node.status === 'online' ? 'emerald' : 'neutral'}>{node.status.toUpperCase()}</Badge>
                        </div>
                        <p className="text-sm text-neutral-500 font-mono">{node.ip} • Uptime: {node.uptime}</p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" icon={<Power size={14} />}>Actions</Button>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="space-y-4">
                      <h4 className="text-xs font-mono text-neutral-500 uppercase">Compute Resources</h4>
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span>CPU Load</span>
                          <span className={node.cpu > 80 ? 'text-red-400' : 'text-emerald-400'}>{node.cpu}%</span>
                        </div>
                        <ProgressBar value={node.cpu} colorClass={node.cpu > 80 ? 'bg-red-500' : 'bg-emerald-500'} />
                      </div>
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span>RAM ({node.ram.used} / {node.ram.total} GB)</span>
                          <span className={(node.ram.used / node.ram.total) > 0.8 ? 'text-amber-400' : 'text-cyan-400'}>
                            {Math.round((node.ram.used / node.ram.total) * 100)}%
                          </span>
                        </div>
                        <ProgressBar
                          value={(node.ram.used / node.ram.total) * 100}
                          colorClass={(node.ram.used / node.ram.total) > 0.8 ? 'bg-amber-500' : 'bg-cyan-500'}
                        />
                      </div>
                    </div>

                    <div className="lg:col-span-2 space-y-4">
                      <h4 className="text-xs font-mono text-neutral-500 uppercase">GPU Acceleration</h4>
                      {node.gpus.length === 0 && <p className="text-sm text-neutral-600 italic">No GPUs detected on this node.</p>}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {node.gpus.map((gpu, idx) => (
                          <div key={idx} className="bg-neutral-900/50 rounded p-3 border border-neutral-800">
                            <div className="flex justify-between items-center mb-2">
                              <span className="font-semibold text-sm text-neutral-300">{gpu.name}</span>
                              <span className={`text-xs font-mono ${gpu.temp > 80 ? 'text-red-400' : 'text-neutral-500'}`}>
                                {gpu.temp}°C • {gpu.power}W
                              </span>
                            </div>
                            <div className="space-y-3">
                              <div className="space-y-1">
                                <div className="flex justify-between text-[10px] text-neutral-500 uppercase">
                                  <span>Core Load</span>
                                  <span>{gpu.util}%</span>
                                </div>
                                <div className="h-1 w-full bg-neutral-800 rounded-full overflow-hidden">
                                  <div className="h-full bg-purple-500 transition-all duration-500" style={{ width: `${gpu.util}%` }} />
                                </div>
                              </div>
                              <div className="space-y-1">
                                <div className="flex justify-between text-[10px] text-neutral-500 uppercase">
                                  <span>VRAM ({gpu.vram}/{gpu.totalVram}GB)</span>
                                  <span>{Math.round((gpu.vram / gpu.totalVram) * 100)}%</span>
                                </div>
                                <div className="h-1 w-full bg-neutral-800 rounded-full overflow-hidden">
                                  <div className="h-full bg-amber-500 transition-all duration-500" style={{ width: `${(gpu.vram / gpu.totalVram) * 100}%` }} />
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </Card>
              ))
            )}
          </div>
        )}

        {/* SERVICES TAB */}
        {activeTab === 'SERVICES' && (
          <Card className="border-neutral-800">
            {servicesLoading && services.length === 0 ? (
              <div className="p-8 text-center">
                <Loader2 className="animate-spin mx-auto mb-2 text-neutral-500" />
                <p className="text-neutral-500">Loading services...</p>
              </div>
            ) : services.length === 0 ? (
              <div className="p-8 text-center text-neutral-500">
                <p>No services found</p>
                <p className="text-xs mt-1">Services will appear when Docker containers are running</p>
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-xs font-mono text-neutral-500 border-b border-neutral-800">
                    <th className="p-3 font-medium">STATUS</th>
                    <th className="p-3 font-medium">SERVICE NAME</th>
                    <th className="p-3 font-medium">NODE</th>
                    <th className="p-3 font-medium">PORT</th>
                    <th className="p-3 font-medium">UPTIME</th>
                    <th className="p-3 font-medium text-right">ACTIONS</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {services.map(svc => (
                    <tr key={svc.id} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors">
                      <td className="p-3">
                        <StatusDot status={svc.status as any} />
                      </td>
                      <td className="p-3 font-medium text-neutral-300">{svc.name}</td>
                      <td className="p-3 text-neutral-400">{svc.node}</td>
                      <td className="p-3 font-mono text-neutral-500">{svc.port > 0 ? `:${svc.port}` : '-'}</td>
                      <td className="p-3 text-neutral-400">{svc.uptime}</td>
                      <td className="p-3 text-right">
                        <button className="text-neutral-500 hover:text-white">•••</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        )}

        {/* LOGS TAB */}
        {activeTab === 'LOGS' && (
          <div className="space-y-4">
            {/* Filters Row */}
            <Card className="border-neutral-800">
              <div className="flex flex-wrap items-center gap-4">
                {/* Loki Status */}
                <div className="flex items-center gap-2">
                  <Terminal size={16} className={lokiHealthy ? 'text-emerald-500' : 'text-red-500'} />
                  <span className={`text-xs font-mono ${lokiHealthy ? 'text-emerald-500' : 'text-red-500'}`}>
                    LOKI {lokiHealthy ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>

                <div className="h-6 w-px bg-neutral-700" />

                {/* Service Filter */}
                <div className="flex items-center gap-2">
                  <Filter size={14} className="text-neutral-500" />
                  <select
                    value={serviceFilter}
                    onChange={(e) => setServiceFilter(e.target.value)}
                    className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-neutral-300 outline-none focus:border-cyan-500"
                  >
                    <option value="">All Services</option>
                    {logsServices.map(svc => (
                      <option key={svc} value={svc}>{svc}</option>
                    ))}
                  </select>
                </div>

                {/* Level Filter */}
                <select
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value)}
                  className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-neutral-300 outline-none focus:border-cyan-500"
                >
                  <option value="">All Levels</option>
                  <option value="ERROR">ERROR</option>
                  <option value="WARN">WARN</option>
                  <option value="INFO">INFO</option>
                  <option value="DEBUG">DEBUG</option>
                </select>

                {/* Time Range */}
                <div className="flex items-center gap-2">
                  <Clock size={14} className="text-neutral-500" />
                  <select
                    value={hoursFilter}
                    onChange={(e) => setHoursFilter(parseInt(e.target.value))}
                    className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-neutral-300 outline-none focus:border-cyan-500"
                  >
                    <option value={1}>Last 1 hour</option>
                    <option value={6}>Last 6 hours</option>
                    <option value={24}>Last 24 hours</option>
                    <option value={72}>Last 3 days</option>
                    <option value={168}>Last 7 days</option>
                  </select>
                </div>

                {/* Search */}
                <div className="flex-1 min-w-[200px] relative">
                  <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-neutral-500" />
                  <input
                    type="text"
                    placeholder="Search logs..."
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && fetchLogs()}
                    className="w-full bg-neutral-900 border border-neutral-700 rounded pl-8 pr-3 py-1 text-sm text-neutral-300 outline-none focus:border-cyan-500"
                  />
                </div>

                <Button variant="primary" size="sm" icon={<Search size={14} />} onClick={fetchLogs}>
                  Search
                </Button>
              </div>
            </Card>

            {/* Logs Display */}
            <Card className="border-neutral-800 overflow-hidden">
              <div className="p-3 border-b border-neutral-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-neutral-400">
                  <Activity size={14} />
                  <span className="text-xs font-mono uppercase">Log Stream</span>
                </div>
                <Badge variant="neutral">{logsTotal} entries</Badge>
              </div>

              {logsLoading ? (
                <div className="p-8 text-center">
                  <Loader2 className="animate-spin mx-auto mb-2 text-neutral-500" />
                  <p className="text-neutral-500">Loading logs...</p>
                </div>
              ) : logs.length === 0 ? (
                <div className="p-8 text-center text-neutral-500">
                  <Activity size={32} className="mx-auto mb-2 opacity-50" />
                  <p>No logs found for the selected filters</p>
                  <p className="text-xs mt-1">Try adjusting the time range or filters</p>
                </div>
              ) : (
                <div className="max-h-[500px] overflow-y-auto font-mono text-xs">
                  {logs.map((log, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-2 border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors flex gap-3"
                    >
                      <span className="text-neutral-600 shrink-0 w-[140px]">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                      <span className={`shrink-0 w-16 px-1.5 py-0.5 rounded text-center ${getLevelColor(log.level)}`}>
                        {log.level}
                      </span>
                      <span className="text-cyan-500 shrink-0 w-[150px] truncate">{log.service}</span>
                      <span className="text-neutral-300 flex-1 break-all">{log.message}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        )}

      </div>
    </div>
  );
};
