'use client';

import { useState, useMemo } from 'react';
import { AuditEntry } from '@/lib/api';

interface AuditLogProps {
  entries: AuditEntry[];
}

type TimeRange = '15m' | '1h' | '6h' | '24h' | 'all';
type ResultFilter = 'all' | 'success' | 'error' | 'pending';

export function AuditLog({ entries }: AuditLogProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [resultFilter, setResultFilter] = useState<ResultFilter>('all');
  const [actionFilter, setActionFilter] = useState<string | null>(null);

  const getResultColor = (result: string) => {
    if (result === 'success') return 'text-hydra-green';
    if (result === 'pending') return 'text-hydra-yellow';
    if (result.includes('error') || result.includes('failed')) return 'text-hydra-red';
    return 'text-gray-400';
  };

  // Get unique actions for filter dropdown
  const uniqueActions = useMemo(() => {
    return Array.from(new Set(entries.map(e => e.action))).sort();
  }, [entries]);

  // Filter entries based on all criteria
  const filteredEntries = useMemo(() => {
    const now = Date.now();
    const timeRangeMs: Record<TimeRange, number> = {
      '15m': 15 * 60 * 1000,
      '1h': 60 * 60 * 1000,
      '6h': 6 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
      'all': Infinity
    };

    return entries.filter(entry => {
      // Time range filter
      if (timeRange !== 'all') {
        const entryTime = new Date(entry.timestamp).getTime();
        if (now - entryTime > timeRangeMs[timeRange]) return false;
      }

      // Result filter
      if (resultFilter !== 'all') {
        if (resultFilter === 'success' && entry.result !== 'success') return false;
        if (resultFilter === 'error' && !entry.result.includes('error') && !entry.result.includes('failed')) return false;
        if (resultFilter === 'pending' && entry.result !== 'pending') return false;
      }

      // Action filter
      if (actionFilter && entry.action !== actionFilter) return false;

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesAction = entry.action.toLowerCase().includes(query);
        const matchesResult = entry.result.toLowerCase().includes(query);
        const matchesDetails = entry.details ? JSON.stringify(entry.details).toLowerCase().includes(query) : false;
        if (!matchesAction && !matchesResult && !matchesDetails) return false;
      }

      return true;
    });
  }, [entries, timeRange, resultFilter, actionFilter, searchQuery]);

  // Count by result type
  const successCount = entries.filter(e => e.result === 'success').length;
  const errorCount = entries.filter(e => e.result.includes('error') || e.result.includes('failed')).length;
  const pendingCount = entries.filter(e => e.result === 'pending').length;

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-hydra-magenta">&#9654;</span>
          Audit Log ({filteredEntries.length}/{entries.length})
        </div>
      </div>

      {/* Filter Bar */}
      <div className="px-2 py-2 border-b border-hydra-gray/30 space-y-2">
        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search audit log..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-hydra-darker border border-hydra-gray/30 rounded px-2 py-1 text-xs text-gray-200 placeholder-gray-500 focus:border-hydra-magenta/50 focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Time range buttons */}
        <div className="flex flex-wrap gap-1">
          {(['15m', '1h', '6h', '24h', 'all'] as const).map(range => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
                timeRange === range
                  ? 'bg-hydra-magenta/30 text-hydra-magenta border border-hydra-magenta/50'
                  : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
              }`}
            >
              {range === 'all' ? 'All' : range}
            </button>
          ))}
        </div>

        {/* Result and Action filters */}
        <div className="flex gap-2">
          {/* Result filter */}
          <div className="flex gap-1">
            <button
              onClick={() => setResultFilter('all')}
              className={`px-1.5 py-0.5 text-[10px] rounded ${
                resultFilter === 'all' ? 'bg-hydra-gray/30 text-gray-300' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setResultFilter('success')}
              className={`px-1.5 py-0.5 text-[10px] rounded ${
                resultFilter === 'success' ? 'bg-hydra-green/30 text-hydra-green' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {successCount}
            </button>
            <button
              onClick={() => setResultFilter('error')}
              className={`px-1.5 py-0.5 text-[10px] rounded ${
                resultFilter === 'error' ? 'bg-hydra-red/30 text-hydra-red' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {errorCount}
            </button>
            <button
              onClick={() => setResultFilter('pending')}
              className={`px-1.5 py-0.5 text-[10px] rounded ${
                resultFilter === 'pending' ? 'bg-hydra-yellow/30 text-hydra-yellow' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {pendingCount}
            </button>
          </div>

          {/* Action filter dropdown */}
          {uniqueActions.length > 0 && (
            <select
              value={actionFilter || ''}
              onChange={(e) => setActionFilter(e.target.value || null)}
              className="flex-1 bg-hydra-darker border border-hydra-gray/30 rounded px-1 py-0.5 text-[10px] text-gray-300"
            >
              <option value="">All Actions</option>
              {uniqueActions.map(action => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Entries */}
      <div className="flex-1 overflow-auto p-2">
        <div className="font-mono text-xs space-y-1">
          {filteredEntries.length === 0 ? (
            <div className="text-center py-4 text-gray-500 text-xs">
              No audit entries match filters
            </div>
          ) : (
            filteredEntries.map((entry, i) => (
              <div key={i} className="flex gap-2 py-1 border-b border-hydra-gray/20 last:border-0 hover:bg-hydra-gray/10 -mx-1 px-1 rounded">
                <span className="text-gray-600 shrink-0">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-hydra-cyan shrink-0">[{entry.action}]</span>
                <span className={`${getResultColor(entry.result)} truncate`} title={entry.result}>
                  {entry.result}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
