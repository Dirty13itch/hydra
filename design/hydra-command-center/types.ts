export type ViewState = 'MISSION' | 'AGENTS' | 'PROJECTS' | 'STUDIO' | 'KNOWLEDGE' | 'LAB' | 'INFRA' | 'HOME';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  duration?: number;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  message: string;
}

export interface SystemPromptVersion {
  version: number;
  timestamp: string;
  content: string;
  author: string;
}

export interface AgentConfig {
  temperature: number;
  topP: number;
  topK: number;
  maxOutputTokens: number;
  systemInstruction: string;
  promptHistory?: SystemPromptVersion[];
}

export interface Agent {
  id: string;
  name: string;
  type: 'research' | 'coding' | 'creative' | 'coordinator';
  status: 'active' | 'idle' | 'thinking' | 'paused' | 'error';
  model: string;
  task: string;
  progress: number;
  uptime: string;
  logs?: LogEntry[];
  config?: AgentConfig;
  tools?: string[];
  dependencies?: string[]; // IDs of other agents
}

export interface Project {
  id: string;
  name: string;
  status: 'active' | 'paused' | 'complete' | 'blocked';
  agentCount: number;
  agentIds?: string[];
  progress: number;
  description: string;
  lastUpdated: string;
}

export interface Artifact {
  id: string;
  type: 'image' | 'code' | 'document';
  name: string;
  timestamp: string;
  url: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isThinking?: boolean;
  attachment?: {
    type: 'image';
    data: string; // base64
    mimeType: string;
  };
}

export interface Queen {
  id: string;
  name: string;
  title: string;
  kingdom: string;
  archetype: string;
  status: {
    dialogue: boolean;
    sprites: boolean;
    relationships: boolean;
  };
  image: string;
}

export interface GPU {
  name: string;
  util: number;
  vram: number;
  totalVram: number;
  temp: number;
  power: number;
}

export interface Node {
  id: string;
  name: string;
  ip: string;
  cpu: number;
  ram: { used: number; total: number };
  gpus: GPU[];
  status: 'online' | 'offline';
  uptime: string;
}

export interface Service {
  id: string;
  name: string;
  node: string;
  port: number;
  status: 'running' | 'stopped' | 'error' | 'starting';
  uptime: string;
}

export interface KnowledgeCollection {
  id: string;
  name: string;
  docCount: number;
  chunkCount: number;
  lastIngested: string;
  topics: string[];
  status: 'ready' | 'indexing' | 'error';
}

export interface AIModel {
  id: string;
  name: string;
  paramSize: string; // e.g., "70B"
  quantization: string; // e.g., "Q4_K_M"
  vramUsage: number; // GB
  contextLength: string; // e.g., "32K"
  status: 'loaded' | 'unloaded' | 'loading';
  provider: 'local' | 'api';
}