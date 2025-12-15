'use client';

import { useState, useEffect, useMemo } from 'react';
import api, { SystemMode, Activity, PendingApproval } from '@/lib/api';

interface StatusBarProps {
  healthScore?: number;
  onModeClick?: () => void;
  onPendingClick?: () => void;
  onActivityClick?: () => void;
}

const MODE_CONFIG = {
  full_auto: { label: 'Full Auto', color: 'var(--hydra-green)', icon: '🤖' },
  supervised: { label: 'Supervised', color: 'var(--hydra-yellow)', icon: '👁️' },
  notify_only: { label: 'Notify Only', color: 'var(--hydra-cyan)', icon: '🔔' },
  safe_mode: { label: 'Safe Mode', color: 'var(--hydra-red)', icon: '🛑' },
};

export function StatusBar({ healthScore: propHealthScore, onModeClick, onPendingClick, onActivityClick }: StatusBarProps) {
  const [systemMode, setSystemMode] = useState<SystemMode | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [recentActivities, setRecentActivities] = useState<Activity[]>([]);
  const [healthScore, setHealthScore] = useState<number | null>(propHealthScore ?? null);
  const [error, setError] = useState(false);

  // Fetch status data
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [modeData, pendingData, activityData] = await Promise.all([
          api.systemMode().catch(() => null),
          api.pendingApprovals().catch(() => ({ pending: [], count: 0 })),
          api.activities({ limit: 20 }).catch(() => ({ activities: [], count: 0 })),
        ]);

        if (modeData) setSystemMode(modeData);
        setPendingCount(pendingData.count);
        setRecentActivities(activityData.activities);
        setError(false);

        // Fetch health score if not provided as prop
        if (propHealthScore === undefined) {
          try {
            const healthData = await fetch('http://192.168.1.244:8700/aggregate/health').then(r => r.json());
            setHealthScore(healthData?.overall_health?.score ?? null);
          } catch {
            // Health API might not be available
          }
        }
      } catch {
        setError(true);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [propHealthScore]);

  // Calculate health status color
  const healthColor = useMemo(() => {
    if (healthScore === null) return 'var(--hydra-text-muted)';
    if (healthScore >= 90) return 'var(--hydra-green)';
    if (healthScore >= 70) return 'var(--hydra-yellow)';
    return 'var(--hydra-red)';
  }, [healthScore]);

  // Generate activity sparkline data (last 20 activities mapped to mini bars)
  const activitySparkline = useMemo(() => {
    if (recentActivities.length === 0) return [];

    // Group activities by 5-minute buckets for the last 2 hours
    const now = Date.now();
    const buckets = new Array(24).fill(0); // 24 x 5min = 2 hours

    recentActivities.forEach(activity => {
      const activityTime = new Date(activity.timestamp).getTime();
      const minutesAgo = (now - activityTime) / (1000 * 60);
      const bucketIndex = Math.floor(minutesAgo / 5);
      if (bucketIndex >= 0 && bucketIndex < 24) {
        buckets[23 - bucketIndex]++; // Reverse so newest is on the right
      }
    });

    const maxCount = Math.max(...buckets, 1);
    return buckets.map(count => Math.round((count / maxCount) * 100));
  }, [recentActivities]);

  const modeConfig = systemMode ? MODE_CONFIG[systemMode.mode as keyof typeof MODE_CONFIG] : null;

  if (error) {
    return (
      <div
        className="border-b px-4 py-1.5 flex items-center justify-center gap-2 text-xs"
        style={{
          backgroundColor: 'rgba(255, 0, 0, 0.1)',
          borderColor: 'rgba(255, 0, 0, 0.3)',
          color: 'var(--hydra-red)'
        }}
      >
        <span>⚠️</span>
        <span>Activity API unavailable</span>
      </div>
    );
  }

  return (
    <div
      className="border-b px-4 py-1.5 flex items-center gap-4 text-xs overflow-x-auto"
      style={{
        backgroundColor: 'var(--hydra-bg)',
        borderColor: 'var(--hydra-border)'
      }}
    >
      {/* Health Indicator */}
      <button
        onClick={onModeClick}
        className="flex items-center gap-2 px-2 py-1 rounded hover:bg-white/5 transition-colors shrink-0"
        title="Cluster health score"
      >
        <div
          className="w-2.5 h-2.5 rounded-full animate-pulse"
          style={{
            backgroundColor: healthColor,
            boxShadow: `0 0 8px ${healthColor}`
          }}
        />
        <span className="font-bold" style={{ color: 'var(--hydra-cyan)' }}>TYPHON</span>
      </button>

      {/* Separator */}
      <div className="w-px h-4 shrink-0" style={{ backgroundColor: 'var(--hydra-border)' }} />

      {/* Health Score */}
      <button
        onClick={onModeClick}
        className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-white/5 transition-colors shrink-0"
        title={`Overall health: ${healthScore?.toFixed(1) ?? '--'}%`}
      >
        <span style={{ color: 'var(--hydra-text-muted)' }}>Health</span>
        <span className="font-medium" style={{ color: healthColor }}>
          {healthScore !== null ? `${Math.round(healthScore)}%` : '--'}
        </span>
      </button>

      {/* Separator */}
      <div className="w-px h-4 shrink-0" style={{ backgroundColor: 'var(--hydra-border)' }} />

      {/* System Mode */}
      {modeConfig && (
        <button
          onClick={onModeClick}
          className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-white/5 transition-colors shrink-0"
          title={`System mode: ${modeConfig.label}`}
        >
          <span>{modeConfig.icon}</span>
          <span style={{ color: modeConfig.color }}>{modeConfig.label}</span>
        </button>
      )}

      {/* Separator */}
      <div className="w-px h-4 shrink-0" style={{ backgroundColor: 'var(--hydra-border)' }} />

      {/* Pending Approvals */}
      <button
        onClick={onPendingClick}
        className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors shrink-0 ${
          pendingCount > 0 ? 'animate-pulse' : ''
        }`}
        style={{
          backgroundColor: pendingCount > 0 ? 'rgba(255, 200, 0, 0.15)' : 'transparent',
        }}
        title={`${pendingCount} pending approval${pendingCount !== 1 ? 's' : ''}`}
      >
        <span style={{ color: pendingCount > 0 ? 'var(--hydra-yellow)' : 'var(--hydra-text-muted)' }}>
          {pendingCount > 0 ? '⏳' : '✓'}
        </span>
        <span style={{ color: pendingCount > 0 ? 'var(--hydra-yellow)' : 'var(--hydra-text-muted)' }}>
          {pendingCount} pending
        </span>
      </button>

      {/* Flexible spacer */}
      <div className="flex-1 min-w-4" />

      {/* Activity Sparkline */}
      <button
        onClick={onActivityClick}
        className="flex items-center gap-2 px-2 py-1 rounded hover:bg-white/5 transition-colors shrink-0"
        title="Recent activity (2h)"
      >
        <span style={{ color: 'var(--hydra-text-muted)' }}>Activity</span>
        <div className="flex items-end gap-px h-4">
          {activitySparkline.length > 0 ? (
            activitySparkline.map((height, i) => (
              <div
                key={i}
                className="w-1 rounded-t transition-all"
                style={{
                  height: `${Math.max(height, 10)}%`,
                  backgroundColor: height > 0 ? 'var(--hydra-cyan)' : 'var(--hydra-border)',
                  opacity: height > 0 ? 0.8 : 0.3,
                }}
              />
            ))
          ) : (
            <span className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>
              No recent activity
            </span>
          )}
        </div>
        <span
          className="text-[10px]"
          style={{ color: 'var(--hydra-text-muted)' }}
        >
          {recentActivities.length > 0 ? `${recentActivities.length} events` : ''}
        </span>
      </button>
    </div>
  );
}
