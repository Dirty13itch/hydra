export type ViewState = 'MISSION' | 'AGENTS' | 'PROJECTS' | 'STUDIO' | 'KNOWLEDGE' | 'LAB' | 'INFRA' | 'HOME' | 'CHAT' | 'RESEARCH' | 'FEEDBACK' | 'BRIEFING' | 'SETTINGS' | 'AUTONOMY' | 'GAMES';

// Credential and User Data types
export interface ServiceCredentialStatus {
  configured: boolean;
  valid: boolean | null;
  lastValidated: string | null;
  type: 'oauth' | 'api_key' | 'account';
  featuresUnlocked: string[];
  setupUrl?: string;
  error?: string;
}

export interface CredentialStatus {
  services: Record<string, ServiceCredentialStatus>;
  summary: {
    configured: number;
    total: number;
    valid: number;
    featuresEnabled: string[];
    featuresDisabled: string[];
  };
}

export interface UserPreferences {
  notifications: {
    enabled: boolean;
    types: string[];
    quietHoursStart?: string;
    quietHoursEnd?: string;
  };
  dashboard: {
    defaultView: ViewState;
    refreshInterval: number;
  };
  ai: {
    preferredModel: string;
    temperature: number;
    maxTokens: number;
  };
}

export interface PriorityContact {
  id: string;
  name: string;
  email: string;
  priority: 'high' | 'medium' | 'low';
}

export interface UserLocation {
  id: string;
  name: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  type: 'home' | 'work' | 'other';
}

export interface UserSchedule {
  id: string;
  name: string;
  type: 'work' | 'quiet' | 'focus' | 'custom';
  days: number[];
  startTime: string;
  endTime: string;
}

export interface UserProfile {
  userId: string;
  displayName: string;
  timezone: string;
  theme: 'dark' | 'light' | 'system';
  preferences: UserPreferences;
  contacts: PriorityContact[];
  locations: UserLocation[];
  schedules: UserSchedule[];
  createdAt?: string;
  updatedAt?: string;
}

// Feedback types for human feedback UI
export interface FeedbackAsset {
  asset_id: string;
  asset_type: 'character_portrait' | 'scene_background' | 'emotion_variant' | 'voice_audio' | 'other';
  character_name?: string;
  prompt_used?: string;
  model_used?: string;
  quality_score?: number;
  consistency_score?: number;
  style_score?: number;
  image_url?: string;
  created_at?: string;
}

export interface FeedbackStats {
  total_feedback: number;
  asset_feedback: number;
  generation_feedback: number;
  comparison_feedback: number;
  avg_asset_rating: number;
  avg_generation_rating: number;
  top_issues: Array<{ issue: string; count: number }>;
  feedback_by_day: Array<{ date: string; count: number }>;
  needs_regeneration: number;
}

export interface QualityReport {
  asset_id: string;
  asset_path: string;
  overall_score: number;
  tier: 'excellent' | 'good' | 'acceptable' | 'poor' | 'reject';
  passed: boolean;
  action: 'approve' | 'review' | 'reject';
  dimensions?: {
    technical: { score: number; issues: string[] };
    composition: { score: number; issues: string[] };
    style: { score: number; issues: string[] };
    character: { score: number; issues: string[] };
  };
}

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

export interface ActionHistoryEntry {
  id: string;
  action: string;
  description: string;
  timestamp: string;
  duration: string;
  status: 'success' | 'failed' | 'partial' | 'cancelled';
  tokensUsed?: number;
  toolsUsed?: string[];
  output?: string;
}

export interface Agent {
  id: string;
  name: string;
  type: 'research' | 'coding' | 'creative' | 'coordinator';
  status: 'active' | 'idle' | 'thinking' | 'paused' | 'error' | 'stopped';
  model: string;
  task: string;
  progress: number;
  uptime: string;
  logs?: LogEntry[];
  config?: AgentConfig;
  tools?: string[];
  dependencies?: string[]; // IDs of other agents
  actionHistory?: ActionHistoryEntry[];
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