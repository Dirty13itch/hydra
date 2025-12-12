'use client';

import { useState } from 'react';
import api, { Alert, AlertSilence } from '@/lib/api';

interface AlertsPanelProps {
  alerts: Alert[];
  onRefresh?: () => void;
}

const severityColors: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/50' },
  warning: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/50' },
  info: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/50' },
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

const SILENCE_DURATIONS = [
  { label: '30m', minutes: 30 },
  { label: '1h', minutes: 60 },
  { label: '4h', minutes: 240 },
  { label: '24h', minutes: 1440 },
];

export function AlertsPanel({ alerts, onRefresh }: AlertsPanelProps) {
  const [silencing, setSilencing] = useState<string | null>(null);
  const [showSilenceModal, setShowSilenceModal] = useState<Alert | null>(null);
  const [silenceError, setSilenceError] = useState<string | null>(null);

  const firingAlerts = alerts.filter(a => a.status === 'firing');
  const resolvedAlerts = alerts.filter(a => a.status === 'resolved').slice(0, 5);

  const handleSilence = async (alert: Alert, durationMinutes: number) => {
    setSilencing(alert.fingerprint);
    setSilenceError(null);
    try {
      const now = new Date();
      const endsAt = new Date(now.getTime() + durationMinutes * 60 * 1000);

      await api.createAlertSilence({
        matchers: [
          {
            name: 'alertname',
            value: alert.labels.alertname,
            isRegex: false,
            isEqual: true,
          },
          ...(alert.labels.instance ? [{
            name: 'instance',
            value: alert.labels.instance,
            isRegex: false,
            isEqual: true,
          }] : []),
        ],
        startsAt: now.toISOString(),
        endsAt: endsAt.toISOString(),
        createdBy: 'hydra-ui',
        comment: `Silenced from Control Plane UI`,
      });

      setShowSilenceModal(null);
      onRefresh?.();
    } catch (err) {
      setSilenceError(err instanceof Error ? err.message : 'Failed to silence alert');
    } finally {
      setSilencing(null);
    }
  };

  return (
    <div className="panel p-4 h-full flex flex-col" style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--hydra-text-muted)' }}>
          Alerts
        </h3>
        <div className="flex items-center gap-2">
          {firingAlerts.length > 0 ? (
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-500/20 text-red-400">
              {firingAlerts.length} firing
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-xs font-medium" style={{ backgroundColor: 'rgba(0, 255, 136, 0.15)', color: 'var(--hydra-green)' }}>
              All clear
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        {firingAlerts.length === 0 && resolvedAlerts.length === 0 ? (
          <div className="text-center py-8" style={{ color: 'var(--hydra-text-muted)' }}>
            <svg className="w-12 h-12 mx-auto mb-2 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm">No active alerts</p>
          </div>
        ) : (
          <>
            {/* Firing alerts */}
            {firingAlerts.map((alert) => {
              const severity = alert.labels.severity || 'warning';
              const colors = severityColors[severity] || severityColors.warning;
              return (
                <div
                  key={alert.fingerprint}
                  className={`p-3 rounded border ${colors.bg} ${colors.border}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-medium text-sm ${colors.text}`}>
                          {alert.labels.alertname}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-xs uppercase ${colors.bg} ${colors.text}`}>
                          {severity}
                        </span>
                      </div>
                      <p className="text-xs truncate" style={{ color: 'var(--hydra-text-secondary)' }}>
                        {alert.annotations.summary || alert.annotations.description || alert.labels.instance || 'No description'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs whitespace-nowrap" style={{ color: 'var(--hydra-text-muted)' }}>
                        {formatTimeAgo(alert.startsAt)}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowSilenceModal(alert);
                        }}
                        className="p-1 rounded hover:bg-white/10 transition-colors"
                        title="Silence this alert"
                      >
                        <svg className="w-4 h-4" style={{ color: 'var(--hydra-text-muted)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" clipRule="evenodd" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Recently resolved */}
            {resolvedAlerts.length > 0 && (
              <>
                <div className="text-xs uppercase tracking-wider pt-2" style={{ color: 'var(--hydra-text-muted)' }}>
                  Recently Resolved
                </div>
                {resolvedAlerts.map((alert) => (
                  <div
                    key={alert.fingerprint}
                    className="p-2 rounded border opacity-60"
                    style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs truncate" style={{ color: 'var(--hydra-text-secondary)' }}>
                        {alert.labels.alertname}
                      </span>
                      <span className="text-xs whitespace-nowrap" style={{ color: 'var(--hydra-green)' }}>
                        resolved
                      </span>
                    </div>
                  </div>
                ))}
              </>
            )}
          </>
        )}
      </div>

      {/* Link to Alertmanager */}
      <div className="pt-3 mt-auto border-t" style={{ borderColor: 'var(--hydra-border)' }}>
        <a
          href="http://192.168.1.244:9093"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs flex items-center gap-1 hover:opacity-80 transition-opacity"
          style={{ color: 'var(--hydra-cyan)' }}
        >
          Open Alertmanager
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      {/* Silence Modal */}
      {showSilenceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div
            className="rounded-lg p-6 w-full max-w-sm mx-4 shadow-xl border"
            style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold" style={{ color: 'var(--hydra-text)' }}>
                Silence Alert
              </h3>
              <button
                onClick={() => {
                  setShowSilenceModal(null);
                  setSilenceError(null);
                }}
                className="p-1 rounded hover:bg-white/10 transition-colors"
              >
                <svg className="w-5 h-5" style={{ color: 'var(--hydra-text-muted)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="mb-4">
              <p className="text-sm mb-1" style={{ color: 'var(--hydra-text-secondary)' }}>
                Alert: <span style={{ color: 'var(--hydra-text)' }}>{showSilenceModal.labels.alertname}</span>
              </p>
              {showSilenceModal.labels.instance && (
                <p className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                  Instance: {showSilenceModal.labels.instance}
                </p>
              )}
            </div>

            <p className="text-sm mb-3" style={{ color: 'var(--hydra-text-secondary)' }}>
              Select silence duration:
            </p>

            <div className="grid grid-cols-2 gap-2 mb-4">
              {SILENCE_DURATIONS.map(({ label, minutes }) => (
                <button
                  key={label}
                  onClick={() => handleSilence(showSilenceModal, minutes)}
                  disabled={silencing === showSilenceModal.fingerprint}
                  className="px-4 py-2 rounded text-sm font-medium transition-colors disabled:opacity-50"
                  style={{
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    color: 'var(--hydra-cyan)',
                    border: '1px solid rgba(0, 212, 255, 0.3)',
                  }}
                >
                  {silencing === showSilenceModal.fingerprint ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    </span>
                  ) : (
                    label
                  )}
                </button>
              ))}
            </div>

            {silenceError && (
              <p className="text-xs text-red-400 mb-3">
                {silenceError}
              </p>
            )}

            <p className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
              This will suppress notifications for this alert until the silence expires.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
