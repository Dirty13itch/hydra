'use client';

import { DomainView } from '../DomainTabs';
import { WorkflowStatusPanel, WorkflowTriggerButton } from '../embedded';
import { AlertsPanel } from '../AlertsPanel';
import { CrewStatusPanel } from '../CrewStatusPanel';
import { SelfImprovementPanel } from '../SelfImprovementPanel';
import type { Alert } from '@/lib/api';

interface AutomationViewProps {
  alerts: Alert[];
  onRefresh: () => void;
}

export function AutomationView({ alerts, onRefresh }: AutomationViewProps) {
  return (
    <DomainView
      title="Automation"
      icon="⚙️"
      description="Workflows, agents, scheduled tasks, and alerting"
      actions={
        <div className="flex items-center gap-2">
          <a
            href="http://192.168.1.244:5678"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              color: 'var(--hydra-green)',
              border: '1px solid var(--hydra-green)',
            }}
          >
            n8n →
          </a>
          <a
            href="http://192.168.1.244:9090"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(234, 179, 8, 0.1)',
              color: 'var(--hydra-yellow)',
              border: '1px solid var(--hydra-yellow)',
            }}
          >
            Prometheus →
          </a>
          <a
            href="http://192.168.1.244:9093"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-3 py-1.5 rounded transition-colors"
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              color: 'var(--hydra-red)',
              border: '1px solid var(--hydra-red)',
            }}
          >
            Alertmanager →
          </a>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Quick Actions Row */}
        <div>
          <div className="text-xs uppercase tracking-wider mb-3" style={{ color: 'var(--hydra-text-muted)' }}>
            Quick Triggers
          </div>
          <div className="flex flex-wrap gap-2">
            <WorkflowTriggerButton workflow="healthDigest" />
            <WorkflowTriggerButton workflow="containerRestart" />
            <WorkflowTriggerButton workflow="diskCleanup" />
            <WorkflowTriggerButton workflow="backupDatabases" />
            <WorkflowTriggerButton workflow="modelSwitch" />
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-2 gap-6">
          {/* Workflows Panel */}
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <WorkflowStatusPanel
              category="all"
              height={400}
              showHeader={true}
            />
          </div>

          {/* Alerts Panel */}
          <div className="space-y-4">
            <AlertsPanel alerts={alerts} onRefresh={onRefresh} />

            {/* CrewAI Agent Status */}
            <CrewStatusPanel />

            {/* Self-Improvement (Layer 8) */}
            <SelfImprovementPanel />

            {/* Scheduled Tasks */}
            <div
              className="rounded-lg border p-4"
              style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
            >
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--hydra-text)' }}>
                Scheduled Tasks
              </div>
              <div className="space-y-2 text-sm">
                {[
                  { name: 'Health Digest', schedule: '6:00 AM', next: '14h 23m' },
                  { name: 'DB Backup', schedule: '2:00 AM', next: '10h 23m' },
                  { name: 'Log Rotation', schedule: '12:00 AM', next: '8h 23m' },
                  { name: 'Model Preload', schedule: '5:30 AM', next: '13h 53m' },
                ].map((task) => (
                  <div key={task.name} className="flex items-center justify-between">
                    <span style={{ color: 'var(--hydra-text)' }}>{task.name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
                        {task.schedule}
                      </span>
                      <span
                        className="text-xs px-1.5 py-0.5 rounded"
                        style={{
                          backgroundColor: 'rgba(6, 182, 212, 0.1)',
                          color: 'var(--hydra-cyan)',
                        }}
                      >
                        in {task.next}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Workflow Categories */}
        <div className="grid grid-cols-3 gap-4">
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--hydra-border)' }}>
              <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                📊 Monitoring
              </span>
            </div>
            <WorkflowStatusPanel category="monitoring" compact={false} height={200} showHeader={false} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--hydra-border)' }}>
              <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                🔧 Maintenance
              </span>
            </div>
            <WorkflowStatusPanel category="maintenance" compact={false} height={200} showHeader={false} />
          </div>
          <div
            className="rounded-lg border overflow-hidden"
            style={{ backgroundColor: 'var(--hydra-bg)', borderColor: 'var(--hydra-border)' }}
          >
            <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--hydra-border)' }}>
              <span className="text-sm font-medium" style={{ color: 'var(--hydra-text)' }}>
                🤖 Automation
              </span>
            </div>
            <WorkflowStatusPanel category="automation" compact={false} height={200} showHeader={false} />
          </div>
        </div>
      </div>
    </DomainView>
  );
}
