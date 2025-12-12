'use client';

import { useEffect, useState } from 'react';

const CREWAI_URL = 'http://192.168.1.244:8500';

interface CrewHealth {
  status: string;
  crews: string[];
  timestamp: string;
}

interface CrewRun {
  crew: string;
  status: 'idle' | 'running' | 'success' | 'error';
  lastRun?: string;
  result?: string;
  error?: string;
}

const CREW_DESCRIPTIONS: Record<string, { description: string; schedule: string; icon: string }> = {
  monitoring: {
    description: 'System health analysis and log review',
    schedule: 'Daily 6 AM',
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
  },
  research: {
    description: 'Web research and information synthesis',
    schedule: 'Monday 2 AM',
    icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'
  },
  maintenance: {
    description: 'Proactive maintenance planning',
    schedule: 'Sunday 3 AM',
    icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
  }
};

export function CrewStatusPanel() {
  const [health, setHealth] = useState<CrewHealth | null>(null);
  const [crewRuns, setCrewRuns] = useState<Record<string, CrewRun>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningCrew, setRunningCrew] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch(`${CREWAI_URL}/health`, { cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
          setError(null);

          // Initialize crew runs state
          const runs: Record<string, CrewRun> = {};
          data.crews.forEach((crew: string) => {
            if (!crewRuns[crew]) {
              runs[crew] = { crew, status: 'idle' };
            } else {
              runs[crew] = crewRuns[crew];
            }
          });
          setCrewRuns(runs);
        } else {
          setError('CrewAI service unavailable');
        }
      } catch (err) {
        setError('Failed to connect to CrewAI');
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRunCrew = async (crewName: string) => {
    setRunningCrew(crewName);
    setCrewRuns(prev => ({
      ...prev,
      [crewName]: { ...prev[crewName], status: 'running' }
    }));

    try {
      const res = await fetch(`${CREWAI_URL}/run/${crewName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: `Manual trigger from Control Plane UI at ${new Date().toISOString()}` })
      });

      if (res.ok) {
        const data = await res.json();
        setCrewRuns(prev => ({
          ...prev,
          [crewName]: {
            ...prev[crewName],
            status: 'success',
            lastRun: new Date().toISOString(),
            result: data.result || 'Completed successfully'
          }
        }));
      } else {
        const errorData = await res.json().catch(() => ({}));
        setCrewRuns(prev => ({
          ...prev,
          [crewName]: {
            ...prev[crewName],
            status: 'error',
            error: errorData.detail || 'Crew execution failed'
          }
        }));
      }
    } catch (err) {
      setCrewRuns(prev => ({
        ...prev,
        [crewName]: {
          ...prev[crewName],
          status: 'error',
          error: 'Connection failed'
        }
      }));
    } finally {
      setRunningCrew(null);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'var(--hydra-cyan)';
      case 'success': return 'var(--hydra-green)';
      case 'error': return 'var(--hydra-red)';
      default: return 'var(--hydra-text-muted)';
    }
  };

  return (
    <div className="panel p-4" style={{ backgroundColor: 'var(--hydra-bg-secondary)', borderColor: 'var(--hydra-border)' }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--hydra-text-muted)' }}>
          AI Crews
        </h3>
        {health && (
          <span
            className="text-xs px-2 py-0.5 rounded"
            style={{
              backgroundColor: health.status === 'ok' ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 0, 85, 0.1)',
              color: health.status === 'ok' ? 'var(--hydra-green)' : 'var(--hydra-red)'
            }}
          >
            {health.status === 'ok' ? 'ONLINE' : 'OFFLINE'}
          </span>
        )}
      </div>

      {loading && (
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 rounded" style={{ backgroundColor: 'var(--hydra-bg)' }} />
          ))}
        </div>
      )}

      {error && (
        <div className="p-3 rounded border" style={{ backgroundColor: 'rgba(255, 0, 85, 0.1)', borderColor: 'var(--hydra-red)' }}>
          <span className="text-sm" style={{ color: 'var(--hydra-red)' }}>{error}</span>
        </div>
      )}

      {!loading && !error && health && (
        <div className="space-y-2">
          {health.crews.map(crew => {
            const info = CREW_DESCRIPTIONS[crew] || { description: 'AI crew', schedule: 'Manual', icon: 'M13 10V3L4 14h7v7l9-11h-7z' };
            const run = crewRuns[crew] || { crew, status: 'idle' };
            const isRunning = runningCrew === crew;

            return (
              <div
                key={crew}
                className="p-3 rounded border transition-all hover:border-opacity-80"
                style={{
                  backgroundColor: 'var(--hydra-bg)',
                  borderColor: run.status === 'running' ? 'var(--hydra-cyan)' : 'var(--hydra-border)'
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div
                      className="p-2 rounded"
                      style={{ backgroundColor: 'var(--hydra-bg-secondary)' }}
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        style={{ color: 'var(--hydra-cyan)' }}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={info.icon} />
                      </svg>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium capitalize" style={{ color: 'var(--hydra-text)' }}>
                          {crew}
                        </span>
                        <span
                          className="text-xs px-1.5 py-0.5 rounded"
                          style={{
                            backgroundColor: 'var(--hydra-bg-secondary)',
                            color: getStatusColor(run.status)
                          }}
                        >
                          {run.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--hydra-text-muted)' }}>
                        {info.description}
                      </p>
                      <p className="text-xs mt-1" style={{ color: 'var(--hydra-text-muted)' }}>
                        Schedule: {info.schedule}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRunCrew(crew)}
                    disabled={isRunning}
                    className="px-3 py-1.5 text-xs font-medium rounded transition-all"
                    style={{
                      backgroundColor: isRunning ? 'var(--hydra-bg)' : 'var(--hydra-cyan)',
                      color: isRunning ? 'var(--hydra-text-muted)' : 'var(--hydra-bg)',
                      opacity: isRunning ? 0.5 : 1,
                      cursor: isRunning ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {isRunning ? (
                      <span className="flex items-center gap-1">
                        <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Running
                      </span>
                    ) : (
                      'Run Now'
                    )}
                  </button>
                </div>

                {run.status === 'success' && run.lastRun && (
                  <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--hydra-border)' }}>
                    <p className="text-xs" style={{ color: 'var(--hydra-green)' }}>
                      Last run: {new Date(run.lastRun).toLocaleTimeString()}
                    </p>
                  </div>
                )}

                {run.status === 'error' && run.error && (
                  <div className="mt-2 pt-2 border-t" style={{ borderColor: 'var(--hydra-border)' }}>
                    <p className="text-xs" style={{ color: 'var(--hydra-red)' }}>
                      Error: {run.error}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {health && (
        <div className="mt-3 pt-3 border-t text-center" style={{ borderColor: 'var(--hydra-border)' }}>
          <span className="text-xs" style={{ color: 'var(--hydra-text-muted)' }}>
            Last check: {new Date(health.timestamp).toLocaleTimeString()}
          </span>
        </div>
      )}
    </div>
  );
}
