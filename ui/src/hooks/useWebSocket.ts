'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

interface UseWebSocketOptions {
  url?: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enabled?: boolean;
}

interface UseWebSocketReturn {
  status: WebSocketStatus;
  lastMessage: WebSocketMessage | null;
  send: (data: any) => void;
  connect: () => void;
  disconnect: () => void;
  reconnectAttempts: number;
}

const MCP_WS_URL = process.env.NEXT_PUBLIC_HYDRA_MCP_WS_URL || 'ws://192.168.1.244:8600/ws';

export function useWebSocket({
  url = MCP_WS_URL,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnectInterval = 5000,
  maxReconnectAttempts = 10,
  enabled = true,
}: UseWebSocketOptions = {}): UseWebSocketReturn {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    clearReconnectTimeout();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
  }, [clearReconnectTimeout]);

  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    clearReconnectTimeout();
    setStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setStatus('connected');
        setReconnectAttempts(0);
        onConnect?.();
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (error) => {
        if (!mountedRef.current) return;
        setStatus('error');
        onError?.(error);
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setStatus('disconnected');
        onDisconnect?.();

        // Attempt reconnection if not at max attempts
        if (reconnectAttempts < maxReconnectAttempts && enabled) {
          setReconnectAttempts((prev) => prev + 1);
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current && enabled) {
              connect();
            }
          }, reconnectInterval);
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setStatus('error');
    }
  }, [url, enabled, onConnect, onMessage, onError, onDisconnect, reconnectAttempts, maxReconnectAttempts, reconnectInterval, clearReconnectTimeout]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  // Connect on mount if enabled
  useEffect(() => {
    mountedRef.current = true;

    if (enabled) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [enabled]); // Only re-run if enabled changes

  return {
    status,
    lastMessage,
    send,
    connect,
    disconnect,
    reconnectAttempts,
  };
}

// Hook for real-time data updates with fallback to polling
export function useRealTimeData<T>({
  fetchData,
  wsEnabled = false,
  pollingInterval = 5000,
  onUpdate,
}: {
  fetchData: () => Promise<T>;
  wsEnabled?: boolean;
  pollingInterval?: number;
  onUpdate?: (data: T) => void;
}) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [updateSource, setUpdateSource] = useState<'polling' | 'websocket'>('polling');

  // WebSocket connection
  const { status: wsStatus, lastMessage } = useWebSocket({
    enabled: wsEnabled,
    onMessage: (msg) => {
      if (msg.type === 'update' && msg.data) {
        setData(msg.data as T);
        setUpdateSource('websocket');
        onUpdate?.(msg.data as T);
      }
    },
  });

  // Polling fallback
  useEffect(() => {
    // Only poll if WebSocket is not connected
    if (wsEnabled && wsStatus === 'connected') {
      return;
    }

    const poll = async () => {
      try {
        const result = await fetchData();
        setData(result);
        setUpdateSource('polling');
        setError(null);
        onUpdate?.(result);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Fetch failed'));
      } finally {
        setIsLoading(false);
      }
    };

    poll(); // Initial fetch
    const interval = setInterval(poll, pollingInterval);

    return () => clearInterval(interval);
  }, [wsEnabled, wsStatus, pollingInterval, fetchData, onUpdate]);

  return {
    data,
    isLoading,
    error,
    updateSource,
    wsStatus,
    isRealTime: wsEnabled && wsStatus === 'connected',
  };
}
