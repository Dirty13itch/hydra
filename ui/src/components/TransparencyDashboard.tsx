'use client';

import { useState, useEffect, useCallback } from 'react';

interface AuditLogEntry {
  id: string;
  timestamp: string;
  actor: 'steward' | 'user' | 'system' | 'agent';
  action: string;
  target: string;
  status: 'success' | 'failed' | 'pending' | 'blocked';
  details?: string;
  requiresApproval: boolean;
}

interface GovernanceRule {
  id: string;
  name: string;
  category: 'permission' | 'safety' | 'resource' | 'notification';
  description: string;
  enabled: boolean;
  triggerCount: number;
}

interface DecisionRecord {
  id: string;
  timestamp: string;
  context: string;
  options: string[];
  chosen: string;
  reasoning: string;
  confidence: number;
  humanOverride?: boolean;
}

interface TransparencyStatus {
  auditLog: AuditLogEntry[];
  governanceRules: GovernanceRule[];
  recentDecisions: DecisionRecord[];
  stats: {
    totalActions: number;
    blockedActions: number;
    humanOverrides: number;
    avgConfidence: number;
  };
}

const MOCK_STATUS: TransparencyStatus = {
  auditLog: [
    {
      id: 'al1',
      timestamp: new Date(Date.now() - 300000).toISOString(),
      actor: 'steward',
      action: 'restart_container',
      target: 'hydra-loki',
      status: 'success',
      requiresApproval: false,
    },
    {
      id: 'al2',
      timestamp: new Date(Date.now() - 600000).toISOString(),
      actor: 'user',
      action: 'model_switch',
      target: 'TabbyAPI',
      status: 'success',
      details: 'Switched to Llama-3.3-70B',
      requiresApproval: false,
    },
    {
      id: 'al3',
      timestamp: new Date(Date.now() - 900000).toISOString(),
      actor: 'system',
      action: 'alert_triggered',
      target: 'Prometheus',
      status: 'success',
      details: 'GPU temperature warning',
      requiresApproval: false,
    },
    {
      id: 'al4',
      timestamp: new Date(Date.now() - 1200000).toISOString(),
      actor: 'agent',
      action: 'research_complete',
      target: 'research-assistant',
      status: 'success',
      details: 'ExLlamaV3 TP research completed',
      requiresApproval: false,
    },
    {
      id: 'al5',
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      actor: 'steward',
      action: 'docker_prune',
      target: 'hydra-storage',
      status: 'blocked',
      details: 'Blocked: requires user approval',
      requiresApproval: true,
    },
  ],
  governanceRules: [
    {
      id: 'gr1',
      name: 'Destructive Actions Require Approval',
      category: 'permission',
      description: 'Actions that delete data or stop critical services require human approval',
      enabled: true,
      triggerCount: 12,
    },
    {
      id: 'gr2',
      name: 'GPU Power Limits',
      category: 'safety',
      description: 'Enforce power limits based on UPS capacity (2000W total)',
      enabled: true,
      triggerCount: 3,
    },
    {
      id: 'gr3',
      name: 'Model Memory Bounds',
      category: 'resource',
      description: 'Prevent loading models that exceed available VRAM',
      enabled: true,
      triggerCount: 7,
    },
    {
      id: 'gr4',
      name: 'Alert Escalation',
      category: 'notification',
      description: 'Escalate critical alerts after 5 minutes unacknowledged',
      enabled: true,
      triggerCount: 2,
    },
  ],
  recentDecisions: [
    {
      id: 'rd1',
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      context: 'Loki container health check failed',
      options: ['Restart container', 'Wait and monitor', 'Alert user'],
      chosen: 'Restart container',
      reasoning: 'Health check failed 3 consecutive times. Container restart is within autonomous authority.',
      confidence: 0.92,
    },
    {
      id: 'rd2',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      context: 'User requested model switch during active inference',
      options: ['Queue switch', 'Immediate switch', 'Reject'],
      chosen: 'Queue switch',
      reasoning: 'Active inference in progress. Queuing ensures no request interruption.',
      confidence: 0.88,
    },
  ],
  stats: {
    totalActions: 234,
    blockedActions: 8,
    humanOverrides: 3,
    avgConfidence: 0.89,
  },
};

interface TransparencyDashboardProps {
  compact?: boolean;
}

export function TransparencyDashboard({ compact = false }: TransparencyDashboardProps) {
  const [status, setStatus] = useState<TransparencyStatus>(MOCK_STATUS);
  const [activeTab, setActiveTab] = useState<'audit' | 'governance' | 'decisions'>('audit');

  const formatRelativeTime = (timestamp: string) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  const getStatusColor = (status: AuditLogEntry['status']) => {
    switch (status) {
      case 'success':
        return 'var(--hydra-green)';
      case 'pending':
        return 'var(--hydra-yellow)';
      case 'failed':
      case 'blocked':
        return 'var(--hydra-red)';
    }
  };

  const getActorIcon = (actor: AuditLogEntry['actor']) => {
    switch (actor) {
      case 'steward':
        return '🤖';
      case 'user':
        return '👤';
      case 'system':
        return '⚙️';
      case 'agent':
        return '🧠';
    }
  };

  const getCategoryColor = (category: GovernanceRule['category']) => {
    switch (category) {
      case 'permission':
        return 'var(--hydra-yellow)';
      case 'safety':
        return 'var(--hydra-red)';
      case 'resource':
        return 'var(--hydra-cyan)';
      case 'notification':
        return 'var(--hydra-purple)';
    }
  };

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-2 px-2 py-1 rounded text-xs"
          style={{
            backgroundColor: 'rgba(234, 179, 8, 0.1)',
            border: '1px solid var(--hydra-yellow)',
          }}
        >
          <span>📋</span>
          <span style={{ color: 'var(--hydra-yellow)' }}>
            {status.stats.totalActions} actions
          </span>
        </div>
        <span className="text-xs" style={{ color: 'var(--hydra-green)' }}>
          {Math.round(status.stats.avgConfidence * 100)}% avg confidence
        </span>
      </div>
    );
  }

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: 'var(--hydra-bg)',
        borderColor: 'var(--hydra-border)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: 'var(--hydra-border)' }}
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">📋</span>
          <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
            Transparency Dashboard
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              backgroundColor: 'rgba(234, 179, 8, 0.1)',
              color: 'var(--hydra-yellow)',
            }}
          >
            Layer 7
          </span>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span style={{ color: 'var(--hydra-text-muted)' }}>
            {status.stats.blockedActions} blocked
          </span>
          <span style={{ color: 'var(--hydra-cyan)' }}>
            {status.stats.humanOverrides} overrides
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div
        className="grid grid-cols-4 gap-2 p-3 border-b"
        style={{ borderColor: 'var(--hydra-border)', backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
      >
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
            {status.stats.totalActions}
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Total Actions
          </div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-red)' }}>
            {status.stats.blockedActions}
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Blocked
          </div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-yellow)' }}>
            {status.stats.humanOverrides}
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Overrides
          </div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-green)' }}>
            {Math.round(status.stats.avgConfidence * 100)}%
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Confidence
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b" style={{ borderColor: 'var(--hydra-border)' }}>
        {(['audit', 'governance', 'decisions'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="flex-1 px-3 py-2 text-xs font-medium transition-colors"
            style={{
              backgroundColor: activeTab === tab ? 'rgba(234, 179, 8, 0.1)' : 'transparent',
              color: activeTab === tab ? 'var(--hydra-yellow)' : 'var(--hydra-text-muted)',
              borderBottom: activeTab === tab ? '2px solid var(--hydra-yellow)' : 'none',
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-3 space-y-2 max-h-72 overflow-y-auto">
        {activeTab === 'audit' && (
          <>
            {status.auditLog.map((entry) => (
              <div
                key={entry.id}
                className="flex items-center gap-3 p-2 rounded"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderLeft: `3px solid ${getStatusColor(entry.status)}`,
                }}
              >
                <span className="text-lg">{getActorIcon(entry.actor)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                      {entry.action}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                      → {entry.target}
                    </span>
                  </div>
                  {entry.details && (
                    <div className="text-xs truncate" style={{ color: 'var(--hydra-text-muted)' }}>
                      {entry.details}
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <div
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor: `${getStatusColor(entry.status)}20`,
                      color: getStatusColor(entry.status),
                    }}
                  >
                    {entry.status}
                  </div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--hydra-text-muted)' }}>
                    {formatRelativeTime(entry.timestamp)}
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {activeTab === 'governance' && (
          <>
            {status.governanceRules.map((rule) => (
              <div
                key={rule.id}
                className="p-3 rounded border"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderColor: 'var(--hydra-border)',
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                        {rule.name}
                      </span>
                      <span
                        className="text-xs px-1.5 py-0.5 rounded uppercase"
                        style={{
                          backgroundColor: `${getCategoryColor(rule.category)}20`,
                          color: getCategoryColor(rule.category),
                        }}
                      >
                        {rule.category}
                      </span>
                    </div>
                    <p className="text-xs mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
                      {rule.description}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                      {rule.triggerCount}x
                    </span>
                    <div
                      className="w-8 h-4 rounded-full relative cursor-pointer transition-colors"
                      style={{
                        backgroundColor: rule.enabled ? 'var(--hydra-green)' : 'var(--hydra-border)',
                      }}
                    >
                      <div
                        className="absolute w-3 h-3 rounded-full bg-white top-0.5 transition-all"
                        style={{ left: rule.enabled ? '1rem' : '0.125rem' }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {activeTab === 'decisions' && (
          <>
            {status.recentDecisions.map((decision) => (
              <div
                key={decision.id}
                className="p-3 rounded border"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderColor: 'var(--hydra-border)',
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                    {formatRelativeTime(decision.timestamp)}
                  </span>
                  <span
                    className="text-xs font-medium"
                    style={{
                      color:
                        decision.confidence > 0.9
                          ? 'var(--hydra-green)'
                          : decision.confidence > 0.7
                          ? 'var(--hydra-yellow)'
                          : 'var(--hydra-red)',
                    }}
                  >
                    {Math.round(decision.confidence * 100)}% confident
                  </span>
                </div>
                <div className="text-sm mb-2" style={{ color: 'var(--hydra-text)' }}>
                  {decision.context}
                </div>
                <div className="flex items-center gap-2 mb-2">
                  {decision.options.map((option) => (
                    <span
                      key={option}
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        backgroundColor:
                          option === decision.chosen
                            ? 'rgba(6, 182, 212, 0.2)'
                            : 'rgba(0, 0, 0, 0.2)',
                        color:
                          option === decision.chosen
                            ? 'var(--hydra-cyan)'
                            : 'var(--hydra-text-muted)',
                        border:
                          option === decision.chosen
                            ? '1px solid var(--hydra-cyan)'
                            : '1px solid transparent',
                      }}
                    >
                      {option}
                    </span>
                  ))}
                </div>
                <div
                  className="text-xs p-2 rounded"
                  style={{ backgroundColor: 'rgba(0, 0, 0, 0.2)', color: 'var(--hydra-text-muted)' }}
                >
                  <strong style={{ color: 'var(--hydra-text)' }}>Reasoning:</strong>{' '}
                  {decision.reasoning}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
