'use client';

import { useState } from 'react';
import api from '@/lib/api';

interface ActionResult {
  success: boolean;
  message: string;
}

interface QuickAction {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  dangerous?: boolean;
  action: () => Promise<ActionResult>;
}

export function QuickActions() {
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<{ action: string; result: ActionResult } | null>(null);
  const [confirmAction, setConfirmAction] = useState<QuickAction | null>(null);

  const MCP_URL = process.env.NEXT_PUBLIC_HYDRA_MCP_URL || 'http://192.168.1.244:8600';

  const executeAction = async (action: QuickAction) => {
    if (action.dangerous && !confirmAction) {
      setConfirmAction(action);
      return;
    }
    setConfirmAction(null);
    setLoading(action.id);
    setResult(null);
    try {
      const res = await action.action();
      setResult({ action: action.name, result: res });
    } catch (err) {
      setResult({ action: action.name, result: { success: false, message: `Failed: ${err}` } });
    } finally {
      setLoading(null);
    }
  };

  const actions: QuickAction[] = [
    {
      id: 'clear-mcp-cache',
      name: 'Clear MCP Cache',
      description: 'Refresh cached service status and metrics',
      icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
      color: 'cyan',
      action: async () => {
        const res = await fetch(`${MCP_URL}/cache/clear`, { method: 'POST' });
        if (res.ok) {
          return { success: true, message: 'Cache cleared successfully' };
        }
        return { success: false, message: 'Failed to clear cache' };
      },
    },
    {
      id: 'docker-prune',
      name: 'Docker Cleanup',
      description: 'Remove unused containers, images, and build cache',
      icon: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
      color: 'yellow',
      dangerous: true,
      action: async () => {
        const res = await fetch(`${MCP_URL}/docker/prune`, { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
          return { success: true, message: `Cleaned up ${data.space_reclaimed || 'some'} space` };
        }
        return { success: false, message: data.error || 'Failed to prune Docker' };
      },
    },
    {
      id: 'reload-prometheus',
      name: 'Reload Prometheus',
      description: 'Hot-reload Prometheus configuration',
      icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z',
      color: 'green',
      action: async () => {
        try {
          const res = await fetch('http://192.168.1.244:9090/-/reload', { method: 'POST' });
          if (res.ok || res.status === 200) {
            return { success: true, message: 'Prometheus configuration reloaded' };
          }
          return { success: false, message: `HTTP ${res.status}` };
        } catch (err) {
          return { success: false, message: 'Could not connect to Prometheus' };
        }
      },
    },
    {
      id: 'check-updates',
      name: 'Check for Updates',
      description: 'Trigger Watchtower to check for container updates',
      icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4',
      color: 'magenta',
      action: async () => {
        const res = await fetch(`${MCP_URL}/watchtower/trigger`, { method: 'POST' });
        if (res.ok) {
          return { success: true, message: 'Watchtower check triggered' };
        }
        return { success: false, message: 'Failed to trigger Watchtower' };
      },
    },
    {
      id: 'refresh-gpu',
      name: 'Refresh GPU Status',
      description: 'Force refresh of GPU metrics from all nodes',
      icon: 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z',
      color: 'cyan',
      action: async () => {
        try {
          await api.gpuStatus();
          return { success: true, message: 'GPU metrics refreshed' };
        } catch (err) {
          return { success: false, message: 'Failed to refresh GPU metrics' };
        }
      },
    },
    {
      id: 'test-alerts',
      name: 'Test Alerting',
      description: 'Send a test alert to verify notification channels',
      icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9',
      color: 'yellow',
      action: async () => {
        const res = await fetch(`${MCP_URL}/alerts/test`, { method: 'POST' });
        if (res.ok) {
          return { success: true, message: 'Test alert sent to Discord' };
        }
        return { success: false, message: 'Failed to send test alert' };
      },
    },
  ];

  const getColorClasses = (color: string, isActive: boolean = false) => {
    const colors: Record<string, { bg: string; text: string; border: string; hover: string }> = {
      cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/30', hover: 'hover:bg-cyan-500/20' },
      green: { bg: 'bg-green-500/10', text: 'text-green-400', border: 'border-green-500/30', hover: 'hover:bg-green-500/20' },
      yellow: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/30', hover: 'hover:bg-yellow-500/20' },
      magenta: { bg: 'bg-pink-500/10', text: 'text-pink-400', border: 'border-pink-500/30', hover: 'hover:bg-pink-500/20' },
      red: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30', hover: 'hover:bg-red-500/20' },
    };
    const c = colors[color] || colors.cyan;
    return isActive ? `${c.bg} ${c.text} ${c.border}` : `${c.text} ${c.border} ${c.hover}`;
  };

  return (
    <div className="panel p-4" style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}>
      <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
        Quick Actions
      </h3>

      <div className="grid grid-cols-2 gap-2">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => executeAction(action)}
            disabled={loading !== null}
            className={`p-3 md:p-3 min-h-[56px] md:min-h-0 rounded border text-left transition-all ${
              loading === action.id
                ? 'opacity-50 cursor-wait'
                : getColorClasses(action.color)
            } ${action.dangerous ? 'border-dashed' : ''}`}
            style={{ backgroundColor: 'var(--hydra-bg)' }}
          >
            <div className="flex items-start gap-2">
              <svg className="w-5 h-5 md:w-4 md:h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={action.icon} />
              </svg>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium truncate">{action.name}</div>
                <div className="text-[10px] opacity-60 truncate hidden sm:block">{action.description}</div>
              </div>
              {loading === action.id && (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              )}
            </div>
          </button>
        ))}
      </div>

      {/* Confirmation Dialog */}
      {confirmAction && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-hydra-darker border border-hydra-gray/50 rounded-lg p-6 max-w-sm mx-4">
            <h4 className="text-lg font-medium text-yellow-400 mb-2">Confirm Action</h4>
            <p className="text-sm text-gray-300 mb-4">
              Are you sure you want to run "{confirmAction.name}"? {confirmAction.description}
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmAction(null)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => executeAction(confirmAction)}
                className="px-4 py-2 text-sm bg-yellow-500/20 text-yellow-400 border border-yellow-500/50 rounded hover:bg-yellow-500/30 transition-colors"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div
          className={`mt-3 p-3 rounded border text-xs ${
            result.result.success
              ? 'bg-green-500/10 border-green-500/30 text-green-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}
        >
          <div className="font-medium">{result.action}</div>
          <div className="opacity-80">{result.result.message}</div>
        </div>
      )}
    </div>
  );
}
