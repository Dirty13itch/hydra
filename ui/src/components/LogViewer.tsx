'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import api from '@/lib/api';

interface LogViewerProps {
  containerName: string;
  onClose: () => void;
}

export function LogViewer({ containerName, onClose }: LogViewerProps) {
  const [logs, setLogs] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tailLines, setTailLines] = useState(100);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [logLevel, setLogLevel] = useState<'all' | 'error' | 'warn' | 'info'>('all');
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Clean Docker log output (remove stream headers)
  const cleanLogs = (rawLogs: string): string => {
    // Docker multiplexes stdout/stderr with 8-byte headers
    // Remove control characters and clean up the output
    return rawLogs
      .split('\n')
      .map(line => {
        // Remove Docker stream header bytes (first 8 chars if they contain control chars)
        if (line.charCodeAt(0) <= 2) {
          return line.substring(8);
        }
        return line;
      })
      .join('\n');
  };

  const fetchLogs = async () => {
    try {
      setError(null);
      const response = await api.containerLogs(containerName, tailLines);
      setLogs(cleanLogs(response.logs));
    } catch (err) {
      setError(`Failed to fetch logs for ${containerName}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [containerName, tailLines]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 3000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, containerName, tailLines]);

  useEffect(() => {
    // Auto-scroll to bottom when logs update
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Filter logs based on search and log level
  const filteredLogs = useMemo(() => {
    if (!logs) return '';
    let lines = logs.split('\n');

    // Filter by log level
    if (logLevel !== 'all') {
      lines = lines.filter(line => {
        const lineLower = line.toLowerCase();
        if (logLevel === 'error') {
          return lineLower.includes('error') || lineLower.includes('exception') || lineLower.includes('fatal') || lineLower.includes('critical');
        }
        if (logLevel === 'warn') {
          return lineLower.includes('warn') || lineLower.includes('error') || lineLower.includes('exception');
        }
        if (logLevel === 'info') {
          return lineLower.includes('info') || lineLower.includes('warn') || lineLower.includes('error');
        }
        return true;
      });
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      lines = lines.filter(line => line.toLowerCase().includes(query));
    }

    return lines.join('\n');
  }, [logs, searchQuery, logLevel]);

  // Count matches
  const matchCount = useMemo(() => {
    if (!searchQuery || !logs) return 0;
    const query = searchQuery.toLowerCase();
    return logs.split('\n').filter(line => line.toLowerCase().includes(query)).length;
  }, [logs, searchQuery]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-hydra-darker border border-hydra-cyan/30 rounded-lg w-full max-w-5xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-hydra-gray/30">
          <div className="flex items-center gap-3">
            <span className="text-hydra-cyan">&#9632;</span>
            <h2 className="text-lg font-bold text-hydra-cyan">{containerName}</h2>
            <span className="text-xs text-gray-500">LOGS</span>
          </div>
          <div className="flex items-center gap-4">
            {/* Tail lines selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Lines:</span>
              <select
                value={tailLines}
                onChange={(e) => setTailLines(Number(e.target.value))}
                className="bg-hydra-dark border border-hydra-gray/30 rounded px-2 py-1 text-xs text-gray-300"
              >
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </div>

            {/* Auto-refresh toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="form-checkbox h-3 w-3 text-hydra-cyan bg-hydra-dark border-hydra-gray/30 rounded"
              />
              <span className="text-xs text-gray-400">Auto-refresh</span>
            </label>

            {/* Refresh button */}
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="px-3 py-1 bg-hydra-cyan/20 hover:bg-hydra-cyan/40 text-hydra-cyan rounded text-xs transition-colors"
            >
              {loading ? 'Loading...' : 'Refresh'}
            </button>

            {/* Close button */}
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-300 text-xl leading-none"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Search and Filter Bar */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-hydra-gray/30 bg-hydra-dark/50">
          {/* Search input */}
          <div className="relative flex-1 max-w-md">
            <input
              type="text"
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-hydra-darker border border-hydra-gray/30 rounded px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:border-hydra-cyan/50 focus:outline-none"
            />
            {searchQuery && (
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
                <span className="text-xs text-hydra-cyan">{matchCount} matches</span>
                <button
                  onClick={() => setSearchQuery('')}
                  className="text-gray-500 hover:text-gray-300"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
          </div>

          {/* Log level filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500 mr-1">Level:</span>
            {(['all', 'info', 'warn', 'error'] as const).map(level => (
              <button
                key={level}
                onClick={() => setLogLevel(level)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  logLevel === level
                    ? level === 'error' ? 'bg-hydra-red/30 text-hydra-red border border-hydra-red/50'
                    : level === 'warn' ? 'bg-hydra-yellow/30 text-hydra-yellow border border-hydra-yellow/50'
                    : level === 'info' ? 'bg-hydra-cyan/30 text-hydra-cyan border border-hydra-cyan/50'
                    : 'bg-hydra-gray/30 text-gray-300 border border-hydra-gray/50'
                    : 'bg-hydra-gray/20 text-gray-400 border border-transparent hover:bg-hydra-gray/30'
                }`}
              >
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Logs content */}
        <div className="flex-1 overflow-auto p-4 font-mono text-xs bg-hydra-dark">
          {error ? (
            <div className="text-hydra-red">{error}</div>
          ) : loading && !logs ? (
            <div className="text-gray-500">Loading logs...</div>
          ) : (
            <pre className="whitespace-pre-wrap text-gray-300 leading-relaxed">
              {filteredLogs || (searchQuery || logLevel !== 'all' ? 'No matching logs' : 'No logs available')}
              <div ref={logsEndRef} />
            </pre>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-hydra-gray/30 flex items-center justify-between text-xs text-gray-500">
          <span>Press ESC to close</span>
          <span>{autoRefresh ? 'Refreshing every 3s' : 'Manual refresh'}</span>
        </div>
      </div>
    </div>
  );
}
