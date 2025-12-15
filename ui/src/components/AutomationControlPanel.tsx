'use client';

import { useState, useCallback } from 'react';
import { SystemMode, PendingApproval } from '@/lib/api';

interface AutomationControlPanelProps {
  systemMode: SystemMode | null;
  pendingApprovals?: PendingApproval[];
  onModeChange?: (mode: string) => void;
  onEmergencyStop?: () => void;
  onApprove?: (id: number) => void;
  onReject?: (id: number) => void;
}

const MODE_INFO = {
  full_auto: {
    label: 'Full Auto',
    description: 'All automation active, self-healing enabled',
    color: 'hydra-green',
    icon: '&#129302;', // Robot
  },
  supervised: {
    label: 'Supervised',
    description: 'Protected actions require approval',
    color: 'hydra-yellow',
    icon: '&#128064;', // Eyes
  },
  notify_only: {
    label: 'Notify Only',
    description: 'Actions logged but not executed',
    color: 'hydra-cyan',
    icon: '&#128276;', // Bell
  },
  safe_mode: {
    label: 'Safe Mode',
    description: 'All automation disabled',
    color: 'hydra-red',
    icon: '&#128721;', // Stop
  },
};

export function AutomationControlPanel({
  systemMode,
  pendingApprovals = [],
  onModeChange,
  onEmergencyStop,
  onApprove,
  onReject,
}: AutomationControlPanelProps) {
  const [showModeConfirm, setShowModeConfirm] = useState<string | null>(null);

  const currentMode = systemMode?.mode || 'full_auto';
  const modeInfo = MODE_INFO[currentMode as keyof typeof MODE_INFO] || MODE_INFO.full_auto;

  const handleModeClick = useCallback((mode: string) => {
    if (mode === currentMode) return;
    if (mode === 'safe_mode') {
      setShowModeConfirm(mode);
    } else {
      onModeChange?.(mode);
    }
  }, [currentMode, onModeChange]);

  const confirmModeChange = useCallback(() => {
    if (showModeConfirm) {
      onModeChange?.(showModeConfirm);
      setShowModeConfirm(null);
    }
  }, [showModeConfirm, onModeChange]);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="panel h-full flex flex-col">
      <div className="panel-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-hydra-yellow">&#9654;</span>
          Automation Control
        </div>
        <div className={`flex items-center gap-1 text-${modeInfo.color}`}>
          <span
            className="animate-pulse"
            dangerouslySetInnerHTML={{ __html: modeInfo.icon }}
          />
          <span className="text-xs">{modeInfo.label}</span>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-4">
        {/* Emergency Stop */}
        <div className="bg-hydra-red/10 border border-hydra-red/30 rounded-lg p-3">
          <button
            onClick={onEmergencyStop}
            className="w-full py-2 bg-hydra-red text-white font-bold rounded hover:bg-hydra-red/80 transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-xl">&#9632;</span>
            EMERGENCY STOP
          </button>
          <p className="text-[10px] text-hydra-red/70 mt-2 text-center">
            Immediately disables all automation
          </p>
        </div>

        {/* Mode Selection */}
        <div className="space-y-2">
          <div className="text-xs text-gray-400 uppercase tracking-wider">System Mode</div>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(MODE_INFO).map(([mode, info]) => (
              <button
                key={mode}
                onClick={() => handleModeClick(mode)}
                className={`p-2 rounded border transition-all ${
                  currentMode === mode
                    ? `bg-${info.color}/20 border-${info.color}/50 text-${info.color}`
                    : 'bg-hydra-gray/10 border-hydra-gray/30 text-gray-400 hover:bg-hydra-gray/20'
                }`}
              >
                <div className="flex items-center gap-1 text-sm">
                  <span dangerouslySetInnerHTML={{ __html: info.icon }} />
                  <span>{info.label}</span>
                </div>
                <div className="text-[9px] mt-1 opacity-70">{info.description}</div>
              </button>
            ))}
          </div>
          {systemMode?.since && (
            <div className="text-[10px] text-gray-500 text-center">
              Since {formatTime(systemMode.since)}
            </div>
          )}
        </div>

        {/* Pending Approvals */}
        {pendingApprovals.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs text-gray-400 uppercase tracking-wider">
                Pending Approvals
              </div>
              <span className="bg-hydra-yellow/20 text-hydra-yellow px-2 py-0.5 rounded-full text-[10px]">
                {pendingApprovals.length}
              </span>
            </div>
            <div className="space-y-2">
              {pendingApprovals.map((approval) => (
                <div
                  key={approval.id}
                  className="bg-hydra-yellow/10 border border-hydra-yellow/30 rounded p-2"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-200">{approval.action}</span>
                    {approval.risk_level && (
                      <span className={`text-[9px] px-1 rounded ${
                        approval.risk_level === 'critical' ? 'bg-hydra-red/30 text-hydra-red' :
                        approval.risk_level === 'high' ? 'bg-orange-500/30 text-orange-400' :
                        approval.risk_level === 'medium' ? 'bg-hydra-yellow/30 text-hydra-yellow' :
                        'bg-gray-500/30 text-gray-400'
                      }`}>
                        {approval.risk_level}
                      </span>
                    )}
                  </div>
                  {approval.target && (
                    <div className="text-[10px] text-hydra-cyan mb-1">
                      Target: {approval.target}
                    </div>
                  )}
                  {approval.decision_reason && (
                    <div className="text-[10px] text-gray-400 mb-2">
                      {approval.decision_reason}
                    </div>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={() => onApprove?.(approval.id)}
                      className="flex-1 py-1 bg-hydra-green/20 text-hydra-green border border-hydra-green/50 rounded text-xs hover:bg-hydra-green/30 transition-colors"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => onReject?.(approval.id)}
                      className="flex-1 py-1 bg-hydra-red/20 text-hydra-red border border-hydra-red/50 rounded text-xs hover:bg-hydra-red/30 transition-colors"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Status Summary */}
        <div className="text-[10px] text-gray-500 text-center pt-2 border-t border-hydra-gray/20">
          <span dangerouslySetInnerHTML={{ __html: modeInfo.icon }} />
          {' '}
          {currentMode === 'full_auto' && 'Hydra is operating autonomously'}
          {currentMode === 'supervised' && 'Protected actions require your approval'}
          {currentMode === 'notify_only' && 'Actions are logged but not executed'}
          {currentMode === 'safe_mode' && 'All automation is disabled'}
        </div>
      </div>

      {/* Mode Confirmation Modal */}
      {showModeConfirm && (
        <div className="absolute inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="bg-hydra-dark border border-hydra-red/50 rounded-lg p-4 max-w-sm">
            <div className="text-hydra-red text-lg mb-2 flex items-center gap-2">
              <span>&#9888;</span>
              Confirm Mode Change
            </div>
            <p className="text-gray-300 text-sm mb-4">
              {showModeConfirm === 'safe_mode' && (
                'This will disable ALL automation including self-healing. The system will not automatically respond to alerts or issues.'
              )}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setShowModeConfirm(null)}
                className="flex-1 py-2 bg-hydra-gray/30 text-gray-300 rounded hover:bg-hydra-gray/40 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmModeChange}
                className="flex-1 py-2 bg-hydra-red text-white rounded hover:bg-hydra-red/80 transition-colors"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
