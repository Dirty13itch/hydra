'use client';

import { useState, useEffect, useCallback } from 'react';

interface Feedback {
  id: string;
  timestamp: string;
  type: 'positive' | 'negative' | 'correction';
  source: 'explicit' | 'implicit' | 'system';
  context: string;
  processed: boolean;
}

interface LearningItem {
  id: string;
  category: string;
  description: string;
  confidence: number;
  createdAt: string;
  applications: number;
}

interface DiagnosticIssue {
  id: string;
  severity: 'low' | 'medium' | 'high';
  category: string;
  description: string;
  suggestedFix: string;
  autoFixable: boolean;
  status: 'detected' | 'in_progress' | 'resolved';
}

interface SelfImprovementStatus {
  feedbackQueue: Feedback[];
  recentLearnings: LearningItem[];
  diagnosticIssues: DiagnosticIssue[];
  stats: {
    totalFeedback: number;
    totalLearnings: number;
    successRate: number;
    lastAnalysis: string;
    improvementsApplied: number;
  };
}

const MOCK_STATUS: SelfImprovementStatus = {
  feedbackQueue: [
    {
      id: 'f1',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      type: 'positive',
      source: 'explicit',
      context: 'Model recommendation was accurate',
      processed: true,
    },
    {
      id: 'f2',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      type: 'correction',
      source: 'explicit',
      context: 'Adjusted alert threshold preference',
      processed: false,
    },
  ],
  recentLearnings: [
    {
      id: 'l1',
      category: 'preferences',
      description: 'User prefers 70B models for complex tasks',
      confidence: 0.92,
      createdAt: new Date(Date.now() - 86400000).toISOString(),
      applications: 5,
    },
    {
      id: 'l2',
      category: 'workflows',
      description: 'Health digest should include GPU temps',
      confidence: 0.85,
      createdAt: new Date(Date.now() - 172800000).toISOString(),
      applications: 3,
    },
    {
      id: 'l3',
      category: 'system',
      description: 'Container restarts cluster better at 2AM CST',
      confidence: 0.78,
      createdAt: new Date(Date.now() - 259200000).toISOString(),
      applications: 2,
    },
  ],
  diagnosticIssues: [
    {
      id: 'd1',
      severity: 'low',
      category: 'efficiency',
      description: 'Duplicate API calls in health check',
      suggestedFix: 'Batch requests to reduce latency',
      autoFixable: true,
      status: 'detected',
    },
  ],
  stats: {
    totalFeedback: 47,
    totalLearnings: 23,
    successRate: 0.89,
    lastAnalysis: new Date(Date.now() - 3600000).toISOString(),
    improvementsApplied: 12,
  },
};

interface SelfImprovementPanelProps {
  compact?: boolean;
}

export function SelfImprovementPanel({ compact = false }: SelfImprovementPanelProps) {
  const [status, setStatus] = useState<SelfImprovementStatus>(MOCK_STATUS);
  const [activeTab, setActiveTab] = useState<'learnings' | 'feedback' | 'diagnostics'>('learnings');
  const [isLoading, setIsLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      // In production, fetch from /api/self-improvement/status
      // For now, use mock data
      setStatus(MOCK_STATUS);
    } catch (err) {
      console.error('Failed to fetch self-improvement status:', err);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const getSeverityColor = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high':
        return 'var(--hydra-red)';
      case 'medium':
        return 'var(--hydra-yellow)';
      case 'low':
        return 'var(--hydra-cyan)';
    }
  };

  const getTypeIcon = (type: 'positive' | 'negative' | 'correction') => {
    switch (type) {
      case 'positive':
        return '👍';
      case 'negative':
        return '👎';
      case 'correction':
        return '✏️';
    }
  };

  const formatRelativeTime = (timestamp: string) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-2 px-2 py-1 rounded text-xs"
          style={{
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            border: '1px solid var(--hydra-purple)',
          }}
        >
          <span>🧠</span>
          <span style={{ color: 'var(--hydra-purple)' }}>
            {status.stats.totalLearnings} learnings
          </span>
        </div>
        <span
          className="text-xs"
          style={{ color: 'var(--hydra-green)' }}
        >
          {Math.round(status.stats.successRate * 100)}% success
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
          <span className="text-lg">🧠</span>
          <span className="font-medium" style={{ color: 'var(--hydra-text)' }}>
            Self-Improvement
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              backgroundColor: 'rgba(139, 92, 246, 0.1)',
              color: 'var(--hydra-purple)',
            }}
          >
            Layer 8
          </span>
        </div>
        <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
          Last analysis: {formatRelativeTime(status.stats.lastAnalysis)}
        </div>
      </div>

      {/* Stats Row */}
      <div
        className="grid grid-cols-4 gap-2 p-3 border-b"
        style={{ borderColor: 'var(--hydra-border)', backgroundColor: 'rgba(0, 0, 0, 0.2)' }}
      >
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-cyan)' }}>
            {status.stats.totalFeedback}
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Feedback
          </div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-purple)' }}>
            {status.stats.totalLearnings}
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Learnings
          </div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-green)' }}>
            {Math.round(status.stats.successRate * 100)}%
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Success Rate
          </div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold" style={{ color: 'var(--hydra-yellow)' }}>
            {status.stats.improvementsApplied}
          </div>
          <div className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Applied
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b" style={{ borderColor: 'var(--hydra-border)' }}>
        {(['learnings', 'feedback', 'diagnostics'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="flex-1 px-3 py-2 text-xs font-medium transition-colors"
            style={{
              backgroundColor: activeTab === tab ? 'rgba(139, 92, 246, 0.1)' : 'transparent',
              color: activeTab === tab ? 'var(--hydra-purple)' : 'var(--hydra-text-muted)',
              borderBottom: activeTab === tab ? '2px solid var(--hydra-purple)' : 'none',
            }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === 'feedback' && status.feedbackQueue.filter((f) => !f.processed).length > 0 && (
              <span
                className="ml-1 px-1 rounded text-[10px]"
                style={{ backgroundColor: 'var(--hydra-yellow)', color: 'var(--hydra-bg)' }}
              >
                {status.feedbackQueue.filter((f) => !f.processed).length}
              </span>
            )}
            {tab === 'diagnostics' && status.diagnosticIssues.length > 0 && (
              <span
                className="ml-1 px-1 rounded text-[10px]"
                style={{ backgroundColor: 'var(--hydra-red)', color: 'white' }}
              >
                {status.diagnosticIssues.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-3 space-y-2 max-h-64 overflow-y-auto">
        {activeTab === 'learnings' && (
          <>
            {status.recentLearnings.map((learning) => (
              <div
                key={learning.id}
                className="p-2 rounded border"
                style={{
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderColor: 'var(--hydra-border)',
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: 'rgba(139, 92, 246, 0.1)',
                          color: 'var(--hydra-purple)',
                        }}
                      >
                        {learning.category}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                        {formatRelativeTime(learning.createdAt)}
                      </span>
                    </div>
                    <p className="text-sm mt-1" style={{ color: 'var(--hydra-text)' }}>
                      {learning.description}
                    </p>
                  </div>
                  <div className="text-right">
                    <div
                      className="text-xs font-medium"
                      style={{
                        color:
                          learning.confidence > 0.8
                            ? 'var(--hydra-green)'
                            : learning.confidence > 0.6
                            ? 'var(--hydra-yellow)'
                            : 'var(--hydra-text-muted)',
                      }}
                    >
                      {Math.round(learning.confidence * 100)}%
                    </div>
                    <div className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>
                      {learning.applications} uses
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {activeTab === 'feedback' && (
          <>
            {status.feedbackQueue.map((feedback) => (
              <div
                key={feedback.id}
                className="flex items-center gap-2 p-2 rounded"
                style={{
                  backgroundColor: feedback.processed ? 'rgba(0, 0, 0, 0.1)' : 'rgba(0, 0, 0, 0.2)',
                  opacity: feedback.processed ? 0.7 : 1,
                }}
              >
                <span className="text-lg">{getTypeIcon(feedback.type)}</span>
                <div className="flex-1">
                  <p className="text-sm" style={{ color: 'var(--hydra-text)' }}>
                    {feedback.context}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>
                      {feedback.source}
                    </span>
                    <span className="text-[10px]" style={{ color: 'var(--hydra-text-muted)' }}>
                      {formatRelativeTime(feedback.timestamp)}
                    </span>
                  </div>
                </div>
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: feedback.processed
                      ? 'rgba(0, 255, 136, 0.1)'
                      : 'rgba(255, 204, 0, 0.1)',
                    color: feedback.processed ? 'var(--hydra-green)' : 'var(--hydra-yellow)',
                  }}
                >
                  {feedback.processed ? 'Processed' : 'Pending'}
                </span>
              </div>
            ))}
          </>
        )}

        {activeTab === 'diagnostics' && (
          <>
            {status.diagnosticIssues.length === 0 ? (
              <div className="text-center py-4">
                <span className="text-2xl">✅</span>
                <p className="text-sm mt-2" style={{ color: 'var(--hydra-green)' }}>
                  No issues detected
                </p>
              </div>
            ) : (
              status.diagnosticIssues.map((issue) => (
                <div
                  key={issue.id}
                  className="p-2 rounded border"
                  style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.2)',
                    borderColor: getSeverityColor(issue.severity),
                    borderLeftWidth: '3px',
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className="text-xs px-1.5 py-0.5 rounded uppercase"
                          style={{
                            backgroundColor: `${getSeverityColor(issue.severity)}20`,
                            color: getSeverityColor(issue.severity),
                          }}
                        >
                          {issue.severity}
                        </span>
                        <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                          {issue.category}
                        </span>
                      </div>
                      <p className="text-sm mt-1" style={{ color: 'var(--hydra-text)' }}>
                        {issue.description}
                      </p>
                      <p className="text-xs mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
                        Fix: {issue.suggestedFix}
                      </p>
                    </div>
                    {issue.autoFixable && issue.status === 'detected' && (
                      <button
                        className="text-xs px-2 py-1 rounded"
                        style={{
                          backgroundColor: 'rgba(0, 255, 136, 0.1)',
                          color: 'var(--hydra-green)',
                          border: '1px solid var(--hydra-green)',
                        }}
                      >
                        Auto-Fix
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}
