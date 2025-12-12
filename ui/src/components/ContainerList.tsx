'use client';

import { useState, useMemo } from 'react';
import { StatusIndicator } from './StatusIndicator';
import { LogViewer } from './LogViewer';
import api, { Container, RestartResponse } from '@/lib/api';

interface ContainerListProps {
  containers: Container[];
  onRefresh?: () => void;
}

type StatusFilter = 'all' | 'running' | 'stopped';

export function ContainerList({ containers, onRefresh }: ContainerListProps) {
  const [restartingContainers, setRestartingContainers] = useState<Set<string>>(new Set());
  const [startingContainers, setStartingContainers] = useState<Set<string>>(new Set());
  const [stoppingContainers, setStoppingContainers] = useState<Set<string>>(new Set());
  const [pendingConfirmation, setPendingConfirmation] = useState<{
    container: string;
    token: string;
    warning: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedLogs, setSelectedLogs] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const getStatus = (container: Container): 'online' | 'offline' | 'warning' => {
    if (container.state === 'running') return 'online';
    if (container.state === 'exited' || container.state === 'dead') return 'offline';
    return 'warning';
  };

  const handleRestart = async (containerName: string, confirmationToken?: string) => {
    setError(null);
    setRestartingContainers(prev => new Set(prev).add(containerName));

    try {
      const response: RestartResponse = await api.restartContainer(containerName, confirmationToken);

      if (response.status === 'confirmation_required') {
        setPendingConfirmation({
          container: containerName,
          token: response.confirmation_token!,
          warning: response.warning || 'This will restart a protected service!'
        });
        setRestartingContainers(prev => {
          const next = new Set(prev);
          next.delete(containerName);
          return next;
        });
      } else if (response.status === 'success') {
        setPendingConfirmation(null);
        setTimeout(() => {
          setRestartingContainers(prev => {
            const next = new Set(prev);
            next.delete(containerName);
            return next;
          });
          onRefresh?.();
        }, 2000);
      } else {
        setError(response.message || 'Restart failed');
        setRestartingContainers(prev => {
          const next = new Set(prev);
          next.delete(containerName);
          return next;
        });
      }
    } catch (err) {
      setError(`Failed to restart ${containerName}`);
      setRestartingContainers(prev => {
        const next = new Set(prev);
        next.delete(containerName);
        return next;
      });
    }
  };

  const confirmRestart = () => {
    if (pendingConfirmation) {
      handleRestart(pendingConfirmation.container, pendingConfirmation.token);
    }
  };

  const cancelConfirmation = () => {
    setPendingConfirmation(null);
  };

  const handleStart = async (containerName: string) => {
    setError(null);
    setStartingContainers(prev => new Set(prev).add(containerName));
    try {
      const response = await api.startContainer(containerName);
      if (response.status === 'success') {
        setTimeout(() => {
          setStartingContainers(prev => {
            const next = new Set(prev);
            next.delete(containerName);
            return next;
          });
          onRefresh?.();
        }, 2000);
      } else {
        setError(response.message || 'Start failed');
        setStartingContainers(prev => {
          const next = new Set(prev);
          next.delete(containerName);
          return next;
        });
      }
    } catch (err) {
      setError(`Failed to start ${containerName}`);
      setStartingContainers(prev => {
        const next = new Set(prev);
        next.delete(containerName);
        return next;
      });
    }
  };

  const handleStop = async (containerName: string) => {
    setError(null);
    setStoppingContainers(prev => new Set(prev).add(containerName));
    try {
      const response = await api.stopContainer(containerName);
      if (response.status === 'success') {
        setTimeout(() => {
          setStoppingContainers(prev => {
            const next = new Set(prev);
            next.delete(containerName);
            return next;
          });
          onRefresh?.();
        }, 2000);
      } else {
        setError(response.message || 'Stop failed');
        setStoppingContainers(prev => {
          const next = new Set(prev);
          next.delete(containerName);
          return next;
        });
      }
    } catch (err) {
      setError(`Failed to stop ${containerName}`);
      setStoppingContainers(prev => {
        const next = new Set(prev);
        next.delete(containerName);
        return next;
      });
    }
  };

  // Filter and sort containers
  const filteredContainers = useMemo(() => {
    return containers
      .filter(container => {
        // Search filter
        if (searchQuery && !container.name.toLowerCase().includes(searchQuery.toLowerCase())) {
          return false;
        }
        // Status filter
        if (statusFilter === 'running' && container.state !== 'running') {
          return false;
        }
        if (statusFilter === 'stopped' && container.state === 'running') {
          return false;
        }
        return true;
      })
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [containers, searchQuery, statusFilter]);

  const runningCount = containers.filter(c => c.state === 'running').length;
  const stoppedCount = containers.length - runningCount;

  return (
    <div className="panel h-full overflow-hidden flex flex-col">
      <div className="panel-header flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-hydra-cyan">&#9632;</span>
          Containers ({filteredContainers.length}/{containers.length})
        </div>
      </div>

      {/* Search and Filter Bar */}
      <div className="px-3 py-2 border-b border-hydra-gray/30 space-y-2">
        <div className="relative">
          <input
            type="text"
            placeholder="Search containers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-hydra-darker border border-hydra-gray/30 rounded px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:border-hydra-cyan/50 focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              statusFilter === 'all'
                ? 'bg-hydra-cyan/30 text-hydra-cyan border border-hydra-cyan/50'
                : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
            }`}
          >
            All ({containers.length})
          </button>
          <button
            onClick={() => setStatusFilter('running')}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              statusFilter === 'running'
                ? 'bg-hydra-green/30 text-hydra-green border border-hydra-green/50'
                : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
            }`}
          >
            Running ({runningCount})
          </button>
          <button
            onClick={() => setStatusFilter('stopped')}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              statusFilter === 'stopped'
                ? 'bg-hydra-red/30 text-hydra-red border border-hydra-red/50'
                : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
            }`}
          >
            Stopped ({stoppedCount})
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-2 p-2 bg-hydra-red/20 border border-hydra-red rounded text-xs text-hydra-red">
          {error}
        </div>
      )}

      {pendingConfirmation && (
        <div className="mx-4 mt-2 p-3 bg-hydra-yellow/20 border border-hydra-yellow rounded">
          <div className="text-sm text-hydra-yellow font-medium mb-2">Confirm Restart</div>
          <div className="text-xs text-gray-300 mb-3">{pendingConfirmation.warning}</div>
          <div className="flex gap-2">
            <button
              onClick={confirmRestart}
              className="px-3 py-1 bg-hydra-red/30 hover:bg-hydra-red/50 border border-hydra-red text-hydra-red rounded text-xs transition-colors"
            >
              Confirm Restart
            </button>
            <button
              onClick={cancelConfirmation}
              className="px-3 py-1 bg-hydra-gray/30 hover:bg-hydra-gray/50 border border-hydra-gray text-gray-300 rounded text-xs transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {filteredContainers.length === 0 && (
          <div className="text-center py-8 text-gray-500 text-sm">
            {searchQuery || statusFilter !== 'all' ? 'No containers match filters' : 'No containers found'}
          </div>
        )}
        {filteredContainers.map((container) => (
          <div
            key={container.name}
            className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-hydra-gray/20 group"
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <StatusIndicator status={getStatus(container)} pulse={false} />
              <span className="text-sm text-gray-300 font-mono truncate">{container.name}</span>
              {container.protected && (
                <span className="text-[10px] px-1.5 py-0.5 bg-hydra-yellow/20 text-hydra-yellow rounded">
                  protected
                </span>
              )}
            </div>

            <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-xs text-gray-500 mr-1">{container.status}</span>
              <button
                onClick={() => setSelectedLogs(container.name)}
                className="px-2 py-1 text-xs rounded transition-colors bg-hydra-magenta/20 hover:bg-hydra-magenta/40 text-hydra-magenta"
                title="View logs"
              >
                Logs
              </button>
              {container.state === 'running' ? (
                <button
                  onClick={() => handleStop(container.name)}
                  disabled={stoppingContainers.has(container.name)}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    stoppingContainers.has(container.name)
                      ? 'bg-hydra-yellow/20 text-hydra-yellow cursor-wait'
                      : 'bg-hydra-red/20 hover:bg-hydra-red/40 text-hydra-red'
                  }`}
                  title="Stop container"
                >
                  {stoppingContainers.has(container.name) ? 'Stopping...' : 'Stop'}
                </button>
              ) : (
                <button
                  onClick={() => handleStart(container.name)}
                  disabled={startingContainers.has(container.name)}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    startingContainers.has(container.name)
                      ? 'bg-hydra-yellow/20 text-hydra-yellow cursor-wait'
                      : 'bg-hydra-green/20 hover:bg-hydra-green/40 text-hydra-green'
                  }`}
                  title="Start container"
                >
                  {startingContainers.has(container.name) ? 'Starting...' : 'Start'}
                </button>
              )}
              <button
                onClick={() => handleRestart(container.name)}
                disabled={restartingContainers.has(container.name) || container.state !== 'running'}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  restartingContainers.has(container.name)
                    ? 'bg-hydra-yellow/20 text-hydra-yellow cursor-wait'
                    : container.state !== 'running'
                    ? 'bg-hydra-gray/20 text-gray-500 cursor-not-allowed'
                    : 'bg-hydra-cyan/20 hover:bg-hydra-cyan/40 text-hydra-cyan'
                }`}
                title="Restart container"
              >
                {restartingContainers.has(container.name) ? 'Restarting...' : 'Restart'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Log viewer modal */}
      {selectedLogs && (
        <LogViewer
          containerName={selectedLogs}
          onClose={() => setSelectedLogs(null)}
        />
      )}
    </div>
  );
}
