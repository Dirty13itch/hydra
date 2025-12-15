'use client';

import { useState, useEffect, useCallback } from 'react';

const N8N_URL = 'http://192.168.1.244:5678';

// Known workflows in the Hydra cluster
const WORKFLOWS = {
  healthDigest: {
    id: 'daily-health-digest',
    name: 'Daily Health Digest',
    description: 'Morning cluster status report',
    icon: '📊',
    category: 'monitoring',
  },
  containerRestart: {
    id: 'container-auto-restart',
    name: 'Container Auto-Restart',
    description: 'Restart failed containers with rate limiting',
    icon: '🔄',
    category: 'monitoring',
  },
  diskCleanup: {
    id: 'disk-cleanup',
    name: 'Disk Space Cleanup',
    description: 'Clean temp files when disk > 90%',
    icon: '🧹',
    category: 'maintenance',
  },
  modelSwitch: {
    id: 'model-switch',
    name: 'Model Switch',
    description: 'Switch active LLM model',
    icon: '🧠',
    category: 'inference',
  },
  researchIngest: {
    id: 'research-ingest',
    name: 'Research Ingest',
    description: 'Process RSS feeds into Qdrant',
    icon: '📚',
    category: 'automation',
  },
  backupDatabases: {
    id: 'backup-databases',
    name: 'Database Backup',
    description: 'pg_dump all databases to MinIO',
    icon: '💾',
    category: 'maintenance',
  },
  alertHandler: {
    id: 'alert-handler',
    name: 'Alert Handler',
    description: 'Process Prometheus alerts',
    icon: '🚨',
    category: 'monitoring',
  },
};

type WorkflowKey = keyof typeof WORKFLOWS;

interface WorkflowExecution {
  id: string;
  workflowId: string;
  status: 'success' | 'error' | 'running' | 'waiting';
  startedAt: string;
  stoppedAt?: string;
  mode: 'manual' | 'trigger' | 'webhook';
}

interface WorkflowStatusPanelProps {
  // Filter workflows by category
  category?: 'monitoring' | 'maintenance' | 'inference' | 'automation' | 'all';
  // Show compact view
  compact?: boolean;
  // Max workflows to show
  limit?: number;
  // Height of the panel
  height?: number;
  // Show header
  showHeader?: boolean;
}

export function WorkflowStatusPanel({
  category = 'all',
  compact = false,
  limit = 6,
  height = 300,
  showHeader = true,
}: WorkflowStatusPanelProps) {
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [workflowStatus, setWorkflowStatus] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isTriggering, setIsTriggering] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filter workflows by category
  const filteredWorkflows = Object.entries(WORKFLOWS).filter(
    ([, workflow]) => category === 'all' || workflow.category === category
  ).slice(0, limit);

  // Fetch workflow status and recent executions
  const fetchStatus = useCallback(async () => {
    try {
      // In production, this would call n8n API
      // For now, simulate with mock data
      const mockExecutions: WorkflowExecution[] = [
        {
          id: 'exec-1',
          workflowId: 'daily-health-digest',
          status: 'success',
          startedAt: new Date(Date.now() - 3600000).toISOString(),
          stoppedAt: new Date(Date.now() - 3595000).toISOString(),
          mode: 'trigger',
        },
        {
          id: 'exec-2',
          workflowId: 'container-auto-restart',
          status: 'success',
          startedAt: new Date(Date.now() - 7200000).toISOString(),
          stoppedAt: new Date(Date.now() - 7195000).toISOString(),
          mode: 'webhook',
        },
        {
          id: 'exec-3',
          workflowId: 'research-ingest',
          status: 'running',
          startedAt: new Date(Date.now() - 60000).toISOString(),
          mode: 'manual',
        },
      ];

      const mockStatus: Record<string, boolean> = {};
      Object.keys(WORKFLOWS).forEach((key) => {
        mockStatus[WORKFLOWS[key as WorkflowKey].id] = Math.random() > 0.2;
      });

      setExecutions(mockExecutions);
      setWorkflowStatus(mockStatus);
      setIsLoading(false);
      setError(null);
    } catch (err) {
      setError('Failed to fetch workflow status');
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Trigger a workflow manually
  const triggerWorkflow = async (workflowId: string) => {
    setIsTriggering(workflowId);
    try {
      // In production: POST to n8n webhook
      // const response = await fetch(`${N8N_URL}/webhook/${workflowId}`, { method: 'POST' });
      await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate
      fetchStatus();
    } catch (err) {
      setError(`Failed to trigger workflow: ${workflowId}`);
    } finally {
      setIsTriggering(null);
    }
  };

  // Get status color
  const getStatusColor = (status: WorkflowExecution['status']) => {
    switch (status) {
      case 'success':
        return 'var(--hydra-green)';
      case 'error':
        return 'var(--hydra-red)';
      case 'running':
        return 'var(--hydra-cyan)';
      case 'waiting':
        return 'var(--hydra-yellow)';
      default:
        return 'var(--hydra-text-muted)';
    }
  };

  // Format relative time
  const formatRelativeTime = (dateString: string) => {
    const diff = Date.now() - new Date(dateString).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  // Get recent execution for a workflow
  const getRecentExecution = (workflowId: string) => {
    return executions.find((e) => e.workflowId === workflowId);
  };

  if (compact) {
    return (
      <div className="workflow-status-compact">
        <div className="flex flex-wrap gap-2">
          {filteredWorkflows.map(([key, workflow]) => {
            const isActive = workflowStatus[workflow.id];
            const recentExec = getRecentExecution(workflow.id);
            return (
              <button
                key={key}
                onClick={() => triggerWorkflow(workflow.id)}
                disabled={isTriggering === workflow.id}
                className="flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all hover:scale-105"
                style={{
                  backgroundColor: isActive ? 'rgba(34, 197, 94, 0.1)' : 'rgba(107, 114, 128, 0.1)',
                  borderColor: isActive ? 'var(--hydra-green)' : 'var(--hydra-border)',
                  border: '1px solid',
                }}
                title={workflow.description}
              >
                <span>{workflow.icon}</span>
                <span style={{ color: 'var(--hydra-text)' }}>{workflow.name}</span>
                {recentExec?.status === 'running' && (
                  <span
                    className="w-2 h-2 rounded-full animate-pulse"
                    style={{ backgroundColor: 'var(--hydra-cyan)' }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="workflow-status-panel flex flex-col" style={{ height }}>
      {showHeader && (
        <div
          className="flex items-center justify-between px-3 py-2 border-b"
          style={{ borderColor: 'var(--hydra-border)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
              Workflows
            </span>
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                color: 'var(--hydra-green)',
              }}
            >
              {Object.values(workflowStatus).filter(Boolean).length} active
            </span>
          </div>
          <a
            href={N8N_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 rounded transition-colors hover:bg-white/10"
            style={{ color: 'var(--hydra-cyan)' }}
          >
            Open n8n →
          </a>
        </div>
      )}

      <div className="flex-1 overflow-auto p-3">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div
              className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--hydra-cyan)', borderTopColor: 'transparent' }}
            />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <span style={{ color: 'var(--hydra-red)' }}>⚠️ {error}</span>
            <button
              onClick={fetchStatus}
              className="text-xs px-2 py-1 rounded"
              style={{ backgroundColor: 'var(--hydra-cyan)', color: 'var(--hydra-bg)' }}
            >
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredWorkflows.map(([key, workflow]) => {
              const isActive = workflowStatus[workflow.id];
              const recentExec = getRecentExecution(workflow.id);
              const isCurrentlyTriggering = isTriggering === workflow.id;

              return (
                <div
                  key={key}
                  className="flex items-center justify-between p-2 rounded border"
                  style={{
                    backgroundColor: 'var(--hydra-bg)',
                    borderColor: 'var(--hydra-border)',
                  }}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-lg">{workflow.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className="text-sm font-medium truncate"
                          style={{ color: 'var(--hydra-text)' }}
                        >
                          {workflow.name}
                        </span>
                        <span
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{
                            backgroundColor: isActive
                              ? 'var(--hydra-green)'
                              : 'var(--hydra-text-muted)',
                          }}
                        />
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span style={{ color: 'var(--hydra-text-muted)' }}>
                          {workflow.description}
                        </span>
                        {recentExec && (
                          <>
                            <span style={{ color: 'var(--hydra-border)' }}>•</span>
                            <span style={{ color: getStatusColor(recentExec.status) }}>
                              {recentExec.status === 'running'
                                ? 'Running...'
                                : `${recentExec.status} ${formatRelativeTime(recentExec.startedAt)}`}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => triggerWorkflow(workflow.id)}
                    disabled={isCurrentlyTriggering || recentExec?.status === 'running'}
                    className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors disabled:opacity-50"
                    style={{
                      backgroundColor: 'rgba(6, 182, 212, 0.1)',
                      color: 'var(--hydra-cyan)',
                    }}
                  >
                    {isCurrentlyTriggering ? (
                      <>
                        <span
                          className="w-3 h-3 border border-t-transparent rounded-full animate-spin"
                          style={{ borderColor: 'var(--hydra-cyan)', borderTopColor: 'transparent' }}
                        />
                        <span>Triggering...</span>
                      </>
                    ) : (
                      <>
                        <span>▶</span>
                        <span>Run</span>
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Executions Footer */}
      {executions.length > 0 && (
        <div
          className="px-3 py-2 border-t"
          style={{ borderColor: 'var(--hydra-border)', backgroundColor: 'rgba(0,0,0,0.2)' }}
        >
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Recent: {executions.slice(0, 3).map((exec, i) => (
              <span key={exec.id}>
                {i > 0 && ' • '}
                <span style={{ color: getStatusColor(exec.status) }}>
                  {WORKFLOWS[Object.keys(WORKFLOWS).find(
                    (k) => WORKFLOWS[k as WorkflowKey].id === exec.workflowId
                  ) as WorkflowKey]?.icon || '📋'}{' '}
                  {exec.status}
                </span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Quick trigger button for individual workflows
interface WorkflowTriggerButtonProps {
  workflow: WorkflowKey;
  showLabel?: boolean;
}

export function WorkflowTriggerButton({ workflow, showLabel = true }: WorkflowTriggerButtonProps) {
  const [isTriggering, setIsTriggering] = useState(false);
  const [lastResult, setLastResult] = useState<'success' | 'error' | null>(null);
  const config = WORKFLOWS[workflow];

  const trigger = async () => {
    setIsTriggering(true);
    setLastResult(null);
    try {
      // In production: POST to n8n webhook
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setLastResult('success');
    } catch {
      setLastResult('error');
    } finally {
      setIsTriggering(false);
      setTimeout(() => setLastResult(null), 3000);
    }
  };

  return (
    <button
      onClick={trigger}
      disabled={isTriggering}
      className="flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all hover:scale-105 disabled:opacity-50"
      style={{
        backgroundColor:
          lastResult === 'success'
            ? 'rgba(34, 197, 94, 0.2)'
            : lastResult === 'error'
            ? 'rgba(239, 68, 68, 0.2)'
            : 'rgba(6, 182, 212, 0.1)',
        borderColor:
          lastResult === 'success'
            ? 'var(--hydra-green)'
            : lastResult === 'error'
            ? 'var(--hydra-red)'
            : 'var(--hydra-cyan)',
        border: '1px solid',
        color:
          lastResult === 'success'
            ? 'var(--hydra-green)'
            : lastResult === 'error'
            ? 'var(--hydra-red)'
            : 'var(--hydra-cyan)',
      }}
      title={config.description}
    >
      {isTriggering ? (
        <span
          className="w-3 h-3 border border-t-transparent rounded-full animate-spin"
          style={{ borderColor: 'currentColor', borderTopColor: 'transparent' }}
        />
      ) : (
        <span>{config.icon}</span>
      )}
      {showLabel && <span>{config.name}</span>}
      {lastResult === 'success' && <span>✓</span>}
      {lastResult === 'error' && <span>✗</span>}
    </button>
  );
}
