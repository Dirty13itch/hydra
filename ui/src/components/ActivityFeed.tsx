'use client';

import { useState, useMemo, useCallback } from 'react';
import { Activity } from '@/lib/api';

interface ActivityFeedProps {
  activities: Activity[];
  onRefresh?: () => void;
  onApprove?: (id: number) => void;
  onReject?: (id: number) => void;
  onActivityClick?: (activity: Activity) => void;
}

type SourceFilter = 'all' | 'n8n' | 'alert' | 'route' | 'letta' | 'mcp' | 'user' | 'control';
type ActionTypeFilter = 'all' | 'autonomous' | 'triggered' | 'manual' | 'scheduled';

export function ActivityFeed({
  activities,
  onRefresh,
  onApprove,
  onReject,
  onActivityClick,
}: ActivityFeedProps) {
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');
  const [actionTypeFilter, setActionTypeFilter] = useState<ActionTypeFilter>('all');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const getResultIcon = (result?: string) => {
    switch (result) {
      case 'ok': return <span className="text-hydra-green">&#10003;</span>;
      case 'error': return <span className="text-hydra-red">&#10007;</span>;
      case 'pending': return <span className="text-hydra-yellow animate-pulse">&#9679;</span>;
      case 'approved': return <span className="text-hydra-green">&#10004;</span>;
      case 'rejected': return <span className="text-hydra-red">&#10006;</span>;
      default: return <span className="text-gray-500">&#9679;</span>;
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'n8n': return 'text-orange-400';
      case 'alert': return 'text-hydra-red';
      case 'route': return 'text-hydra-cyan';
      case 'letta': return 'text-hydra-magenta';
      case 'mcp': return 'text-hydra-green';
      case 'user': return 'text-blue-400';
      case 'control': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const getActionTypeIcon = (actionType: string) => {
    switch (actionType) {
      case 'autonomous': return '&#129302;'; // Robot
      case 'triggered': return '&#9889;'; // Lightning
      case 'manual': return '&#128100;'; // Person
      case 'scheduled': return '&#128337;'; // Clock
      default: return '&#9679;';
    }
  };

  const filteredActivities = useMemo(() => {
    return activities.filter(activity => {
      if (sourceFilter !== 'all' && activity.source !== sourceFilter) return false;
      if (actionTypeFilter !== 'all' && activity.action_type !== actionTypeFilter) return false;
      return true;
    });
  }, [activities, sourceFilter, actionTypeFilter]);

  // Count by source
  const sourceCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    activities.forEach(a => {
      counts[a.source] = (counts[a.source] || 0) + 1;
    });
    return counts;
  }, [activities]);

  const handleToggleExpand = useCallback((id: number) => {
    setExpandedId(prev => prev === id ? null : id);
  }, []);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatRelativeTime = (timestamp: string) => {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);

    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-hydra-cyan">&#9654;</span>
          Activity Feed ({filteredActivities.length}/{activities.length})
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-1 hover:bg-hydra-gray/30 rounded text-gray-400 hover:text-gray-200 transition-colors"
            title="Refresh"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="px-2 py-2 border-b border-hydra-gray/30 space-y-2">
        {/* Source filter */}
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => setSourceFilter('all')}
            className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
              sourceFilter === 'all'
                ? 'bg-hydra-cyan/30 text-hydra-cyan border border-hydra-cyan/50'
                : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
            }`}
          >
            All
          </button>
          {(['n8n', 'alert', 'route', 'mcp', 'letta', 'user', 'control'] as const).map(source => (
            <button
              key={source}
              onClick={() => setSourceFilter(source)}
              className={`px-2 py-0.5 text-[10px] rounded transition-colors ${
                sourceFilter === source
                  ? 'bg-hydra-cyan/30 text-hydra-cyan border border-hydra-cyan/50'
                  : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
              }`}
            >
              {source} {sourceCounts[source] ? `(${sourceCounts[source]})` : ''}
            </button>
          ))}
        </div>

        {/* Action type filter */}
        <div className="flex gap-1">
          {(['all', 'autonomous', 'triggered', 'manual', 'scheduled'] as const).map(type => (
            <button
              key={type}
              onClick={() => setActionTypeFilter(type)}
              className={`px-1.5 py-0.5 text-[10px] rounded ${
                actionTypeFilter === type
                  ? 'bg-hydra-gray/30 text-gray-300'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {type === 'all' ? 'All Types' : (
                <span dangerouslySetInnerHTML={{ __html: `${getActionTypeIcon(type)} ${type}` }} />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Activity List */}
      <div className="flex-1 overflow-auto p-2">
        <div className="font-mono text-xs space-y-1">
          {filteredActivities.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-2xl mb-2">&#128064;</div>
              <p>No activities match filters</p>
              <p className="text-[10px] mt-1">System is quiet or filters too restrictive</p>
            </div>
          ) : (
            filteredActivities.map((activity) => (
              <div
                key={activity.id}
                className="border border-hydra-gray/20 rounded hover:border-hydra-gray/40 transition-colors"
              >
                {/* Activity Header */}
                <div
                  className="flex items-center gap-2 p-2 cursor-pointer hover:bg-hydra-gray/10"
                  onClick={() => handleToggleExpand(activity.id)}
                >
                  {/* Result Icon */}
                  <span className="shrink-0 w-4 text-center">
                    {getResultIcon(activity.result)}
                  </span>

                  {/* Time */}
                  <span className="text-gray-600 shrink-0 w-16" title={activity.timestamp}>
                    {formatRelativeTime(activity.timestamp)}
                  </span>

                  {/* Source */}
                  <span className={`shrink-0 w-12 uppercase text-[10px] ${getSourceColor(activity.source)}`}>
                    {activity.source}
                  </span>

                  {/* Action */}
                  <span className="text-gray-200 truncate flex-1">
                    {activity.action}
                  </span>

                  {/* Target */}
                  {activity.target && (
                    <span className="text-hydra-cyan/70 truncate max-w-[120px]" title={activity.target}>
                      → {activity.target}
                    </span>
                  )}

                  {/* Action Type Badge */}
                  <span
                    className="text-[9px] text-gray-500"
                    dangerouslySetInnerHTML={{ __html: getActionTypeIcon(activity.action_type) }}
                    title={activity.action_type}
                  />

                  {/* Expand indicator */}
                  <span className={`text-gray-600 transition-transform ${expandedId === activity.id ? 'rotate-90' : ''}`}>
                    &#9656;
                  </span>
                </div>

                {/* Expanded Details */}
                {expandedId === activity.id && (
                  <div className="px-2 pb-2 pt-1 border-t border-hydra-gray/20 space-y-2">
                    {/* Decision Reason */}
                    {activity.decision_reason && (
                      <div className="bg-hydra-darker/50 rounded p-2">
                        <div className="text-[10px] text-hydra-cyan mb-1">Why this action?</div>
                        <div className="text-gray-300 text-[11px]">{activity.decision_reason}</div>
                      </div>
                    )}

                    {/* Params */}
                    {activity.params && Object.keys(activity.params).length > 0 && (
                      <div className="bg-hydra-darker/50 rounded p-2">
                        <div className="text-[10px] text-gray-500 mb-1">Parameters</div>
                        <pre className="text-[10px] text-gray-400 overflow-auto max-h-24">
                          {JSON.stringify(activity.params, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Result Details */}
                    {activity.result_details && Object.keys(activity.result_details).length > 0 && (
                      <div className="bg-hydra-darker/50 rounded p-2">
                        <div className="text-[10px] text-gray-500 mb-1">Result Details</div>
                        <pre className="text-[10px] text-gray-400 overflow-auto max-h-24">
                          {JSON.stringify(activity.result_details, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Timestamps */}
                    <div className="flex gap-4 text-[10px] text-gray-500">
                      <span>ID: {activity.id}</span>
                      <span>At: {formatTime(activity.timestamp)}</span>
                      {activity.source_id && <span>Source ID: {activity.source_id}</span>}
                    </div>

                    {/* Approval Actions */}
                    {activity.requires_approval && activity.result === 'pending' && (
                      <div className="flex gap-2 pt-2 border-t border-hydra-gray/20">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onApprove?.(activity.id);
                          }}
                          className="px-3 py-1 bg-hydra-green/20 text-hydra-green border border-hydra-green/50 rounded text-[10px] hover:bg-hydra-green/30 transition-colors"
                        >
                          &#10003; Approve
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onReject?.(activity.id);
                          }}
                          className="px-3 py-1 bg-hydra-red/20 text-hydra-red border border-hydra-red/50 rounded text-[10px] hover:bg-hydra-red/30 transition-colors"
                        >
                          &#10007; Reject
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
