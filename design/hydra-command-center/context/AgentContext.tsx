import React, { createContext, useContext, useState, useCallback } from 'react';
import { Agent, AgentConfig, LogEntry } from '../types';
import { MOCK_AGENTS } from '../constants';
import { useNotifications } from './NotificationContext';

interface AgentContextType {
  agents: Agent[];
  getAgent: (id: string) => Agent | undefined;
  updateAgentStatus: (id: string, status: Agent['status']) => void;
  updateAgentTask: (id: string, task: string, progress: number) => void;
  updateAgentConfig: (id: string, updates: Partial<Agent> & { config?: Partial<AgentConfig> }) => void;
  stopAgent: (id: string) => void;
}

const AgentContext = createContext<AgentContextType | undefined>(undefined);

export const AgentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [agents, setAgents] = useState<Agent[]>(MOCK_AGENTS);
  const { addNotification } = useNotifications();

  const getAgent = useCallback((id: string) => {
    return agents.find(a => a.id === id);
  }, [agents]);

  const updateAgentStatus = useCallback((id: string, status: Agent['status']) => {
    setAgents(prev => prev.map(a => {
      if (a.id !== id) return a;
      // Side effect for notification
      if (status === 'paused' && a.status === 'active') {
         addNotification('warning', 'Agent Paused', `${a.name} execution suspended.`);
      } else if (status === 'active' && a.status === 'paused') {
         addNotification('success', 'Agent Resumed', `${a.name} execution resumed.`);
      }
      return { ...a, status };
    }));
  }, [addNotification]);

  const updateAgentTask = useCallback((id: string, task: string, progress: number) => {
    setAgents(prev => prev.map(a => a.id === id ? { ...a, task, progress } : a));
  }, []);

  const updateAgentConfig = useCallback((id: string, updates: any) => {
    setAgents(prev => prev.map(a => {
      if (a.id !== id) return a;
      
      let newConfig = { ...a.config! };
      
      // Explicit config object update
      if (updates.config) {
          newConfig = { ...newConfig, ...updates.config };
      }
      
      // Handle flat config props passed at root (legacy support)
      if (updates.temperature !== undefined) newConfig.temperature = updates.temperature;
      if (updates.topP !== undefined) newConfig.topP = updates.topP;
      if (updates.topK !== undefined) newConfig.topK = updates.topK;
      if (updates.maxOutputTokens !== undefined) newConfig.maxOutputTokens = updates.maxOutputTokens;
      if (updates.systemInstruction !== undefined) newConfig.systemInstruction = updates.systemInstruction;
      if (updates.promptHistory !== undefined) newConfig.promptHistory = updates.promptHistory;

      // Extract properties that belong to Agent root, excluding config-specific ones
      const { 
        config, 
        temperature, 
        topP, 
        topK, 
        maxOutputTokens, 
        systemInstruction, 
        promptHistory, 
        ...agentUpdates 
      } = updates;

      return { 
          ...a, 
          ...agentUpdates, 
          config: newConfig 
      };
    }));
    addNotification('info', 'Configuration Updated', 'Agent parameters re-calibrated.');
  }, [addNotification]);

  const stopAgent = useCallback((id: string) => {
    setAgents(prev => prev.map(a => {
      if (a.id !== id) return a;
      addNotification('error', 'Agent Stopped', `Connection to ${a.name} terminated.`);
      return { ...a, status: 'idle', progress: 0, task: 'Awaiting assignment' };
    }));
  }, [addNotification]);

  return (
    <AgentContext.Provider value={{ agents, getAgent, updateAgentStatus, updateAgentTask, updateAgentConfig, stopAgent }}>
      {children}
    </AgentContext.Provider>
  );
};

export const useAgents = () => {
  const context = useContext(AgentContext);
  if (context === undefined) {
    throw new Error('useAgents must be used within an AgentProvider');
  }
  return context;
};
