'use client';

import { useState, useEffect } from 'react';

interface ScheduledTask {
  name: string;
  enabled: boolean;
  frequency: string;
  schedule: string;
  day_of_week: number | null;
  last_run: string | null;
  next_run: string | null;
}

interface Activity {
  id: number;
  timestamp: string;
  source: string;
  action: string;
  action_type: string;
  target?: string;
  result?: string;
  decision_reason?: string;
}

interface SchedulerStatus {
  running: boolean;
  timezone: string;
  current_time: string;
  schedules: Record<string, ScheduledTask>;
  recent_runs: Array<{
    crew: string;
    timestamp: string;
    status: string;
    topic?: string;
  }>;
}

const HYDRA_TOOLS_URL = process.env.NEXT_PUBLIC_HYDRA_TOOLS_URL || 'http://192.168.1.244:8700';

export function TaskQueuePanel() {
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [recentActivity, setRecentActivity] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [schedulerRes, activityRes] = await Promise.all([
          fetch(`${HYDRA_TOOLS_URL}/scheduler/status`).then(r => r.json()),
          fetch(`${HYDRA_TOOLS_URL}/activity?limit=10`).then(r => r.json()),
        ]);
        setSchedulerStatus(schedulerRes);
        setRecentActivity(activityRes.activities || []);
        setError(null);
      } catch (e) {
        setError('Failed to load task data');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const formatRelativeTime = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffMins = Math.round(diffMs / 60000);
    const diffHours = Math.round(diffMs / 3600000);
    const diffDays = Math.round(diffMs / 86400000);

    if (diffMs < 0) {
      // Past
      const absMins = Math.abs(diffMins);
      const absHours = Math.abs(diffHours);
      if (absMins < 60) return `${absMins}m ago`;
      if (absHours < 24) return `${absHours}h ago`;
      return `${Math.abs(diffDays)}d ago`;
    } else {
      // Future
      if (diffMins < 60) return `in ${diffMins}m`;
      if (diffHours < 24) return `in ${diffHours}h`;
      return `in ${diffDays}d`;
    }
  };

  const getResultColor = (result?: string) => {
    switch (result) {
      case 'success': return 'var(--hydra-green)';
      case 'error': return 'var(--hydra-red)';
      case 'pending': return 'var(--hydra-yellow)';
      case 'confirmation_required': return 'var(--hydra-yellow)';
      default: return 'var(--hydra-text-muted)';
    }
  };

  const getDayName = (day: number | null) => {
    if (day === null) return '';
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return days[day] || '';
  };

  if (loading) {
    return (
      <div className="panel p-4">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-1/3 mb-4"></div>
          <div className="space-y-2">
            <div className="h-3 bg-gray-700 rounded"></div>
            <div className="h-3 bg-gray-700 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Scheduled Tasks */}
      <div className="panel p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--hydra-text-muted)' }}>
            Scheduled Tasks
          </h3>
          {schedulerStatus?.running && (
            <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: 'var(--hydra-green)', color: 'black' }}>
              Active
            </span>
          )}
        </div>

        {error ? (
          <div className="text-sm" style={{ color: 'var(--hydra-red)' }}>{error}</div>
        ) : (
          <div className="space-y-2">
            {schedulerStatus && Object.entries(schedulerStatus.schedules).map(([name, task]) => (
              <div
                key={name}
                className="flex items-center justify-between p-2 rounded"
                style={{ backgroundColor: 'var(--hydra-bg-secondary)' }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: task.enabled ? 'var(--hydra-green)' : 'var(--hydra-text-muted)' }}
                  />
                  <span className="text-sm font-medium capitalize">{name}</span>
                  <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                    {task.frequency === 'weekly' ? `${getDayName(task.day_of_week)} ` : ''}{task.schedule}
                  </span>
                </div>
                <div className="text-xs" style={{ color: 'var(--hydra-cyan)' }}>
                  {formatRelativeTime(task.next_run)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="panel p-4">
        <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
          Recent Autonomous Activity
        </h3>

        <div className="space-y-2 max-h-64 overflow-y-auto">
          {recentActivity.length === 0 ? (
            <div className="text-sm" style={{ color: 'var(--hydra-text-muted)' }}>No recent activity</div>
          ) : (
            recentActivity.map((activity) => (
              <div
                key={activity.id}
                className="p-2 rounded text-sm"
                style={{ backgroundColor: 'var(--hydra-bg-secondary)' }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: getResultColor(activity.result) }}
                    />
                    <span className="font-medium">{activity.action}</span>
                    {activity.target && (
                      <span style={{ color: 'var(--hydra-cyan)' }}>{activity.target}</span>
                    )}
                  </div>
                  <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                    {formatRelativeTime(activity.timestamp)}
                  </span>
                </div>
                <div className="text-xs mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
                  {activity.source} - {activity.action_type}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Recent Crew Runs */}
      {schedulerStatus?.recent_runs && schedulerStatus.recent_runs.length > 0 && (
        <div className="panel p-4">
          <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
            Recent Crew Runs
          </h3>

          <div className="space-y-2">
            {schedulerStatus.recent_runs.map((run, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 rounded"
                style={{ backgroundColor: 'var(--hydra-bg-secondary)' }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: run.status === 'success' ? 'var(--hydra-green)' : 'var(--hydra-red)' }}
                  />
                  <span className="text-sm font-medium capitalize">{run.crew}</span>
                </div>
                <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  {formatRelativeTime(run.timestamp)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
