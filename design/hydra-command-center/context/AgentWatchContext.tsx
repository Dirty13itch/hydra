import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { LogEntry } from '../types';
import { useAgents } from './AgentContext';
import { simulateAgentThought } from '../services/geminiService';

interface AgentWatchContextType {
  watchedAgentId: string | null;
  startWatching: (id: string) => void;
  stopWatching: () => void;
  streamLogs: LogEntry[];
  injectCommand: (command: string) => void;
}

const AgentWatchContext = createContext<AgentWatchContextType | undefined>(undefined);

export const AgentWatchProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [watchedAgentId, setWatchedAgentId] = useState<string | null>(null);
  const [streamLogs, setStreamLogs] = useState<LogEntry[]>([]);
  const { getAgent } = useAgents();
  
  // Refs to maintain state inside interval closures
  const watchedIdRef = useRef<string | null>(null);
  const isProcessingRef = useRef<boolean>(false);

  const startWatching = (id: string) => {
    setWatchedAgentId(id);
    watchedIdRef.current = id;
    setStreamLogs([{
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      level: 'INFO',
      message: `ESTABLISHING SECURE UPLINK TO AGENT_${id.substring(0,4)}...`
    }]);
  };

  const stopWatching = () => {
    setWatchedAgentId(null);
    watchedIdRef.current = null;
    setStreamLogs([]);
  };

  const injectCommand = (command: string) => {
    const newLog: LogEntry = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      level: 'WARN', // Warn color stands out as user input
      message: `[SYSTEM_OVERRIDE] Injecting command: "${command}"`
    };
    const ackLog: LogEntry = {
      id: (Date.now() + 1).toString(),
      timestamp: new Date().toLocaleTimeString(),
      level: 'DEBUG',
      message: `[ACK] Priority interrupt received. Re-calculating...`
    };
    setStreamLogs(prev => [...prev.slice(-98), newLog, ackLog]);
  };

  useEffect(() => {
    if (!watchedAgentId) return;

    // Use a robust polling mechanism that allows async API calls
    const interval = setInterval(async () => {
        const currentId = watchedIdRef.current;
        if (!currentId || isProcessingRef.current) return;

        const agent = getAgent(currentId);
        
        // If agent is missing or idle/error, stop generating 'thinking' logs
        if (!agent || agent.status === 'idle' || agent.status === 'error' || agent.status === 'stopped') {
           return;
        }

        // If paused, emit a heartbeat occasionally
        if (agent.status === 'paused') {
            if (Math.random() > 0.85) {
               setStreamLogs(prev => [...prev.slice(-99), {
                   id: Date.now().toString(),
                   timestamp: new Date().toLocaleTimeString(),
                   level: 'WARN',
                   message: `Process suspended. Waiting for resume signal...`
               }]);
            }
            return;
        }

        isProcessingRef.current = true;
        
        try {
          // Call the service to get a real thought based on the agent's persona
          const thought = await simulateAgentThought(agent);
          
          const newLog: LogEntry = {
              id: Date.now().toString(),
              timestamp: new Date().toLocaleTimeString(),
              level: thought.includes('Error') || thought.includes('Failed') ? 'ERROR' : 'DEBUG',
              message: thought
          };
          
          setStreamLogs(prev => [...prev.slice(-99), newLog]);
        } catch (e) {
          // Silent fail on log gen to not spam
        } finally {
          isProcessingRef.current = false;
        }

    }, 3000); // 3 seconds interval for API politeness

    return () => clearInterval(interval);
  }, [watchedAgentId, getAgent]);

  return (
    <AgentWatchContext.Provider value={{ watchedAgentId, startWatching, stopWatching, streamLogs, injectCommand }}>
      {children}
    </AgentWatchContext.Provider>
  );
};

export const useAgentWatch = () => {
  const context = useContext(AgentWatchContext);
  if (!context) throw new Error("useAgentWatch must be used within AgentWatchProvider");
  return context;
};