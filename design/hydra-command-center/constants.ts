import { Agent, Project, Artifact, Queen, Node, Service, KnowledgeCollection, AIModel } from './types';

export const MOCK_AGENTS: Agent[] = [
  {
    id: '1',
    name: 'Research-Alpha',
    type: 'research',
    status: 'active',
    model: 'gemini-2.5-flash',
    task: 'Analyzing quantum computing papers',
    progress: 67,
    uptime: '2h 34m',
    tools: ['Google Search', 'ArXiv API', 'Vector DB', 'Web Scraper'],
    dependencies: [],
    config: {
      temperature: 0.2,
      topP: 0.8,
      topK: 40,
      maxOutputTokens: 8192,
      systemInstruction: "You are a senior research analyst. Prioritize primary sources and peer-reviewed citations. Output data in structured JSON format when possible.",
      promptHistory: [
        { version: 1, timestamp: '2h ago', author: 'System', content: "You are a research bot. Find papers." },
        { version: 2, timestamp: '1h ago', author: 'Admin', content: "You are a senior research analyst. Prioritize primary sources." },
        { version: 3, timestamp: '15m ago', author: 'Admin', content: "You are a senior research analyst. Prioritize primary sources and peer-reviewed citations. Output data in structured JSON format when possible." }
      ]
    }
  },
  {
    id: '2',
    name: 'Code-Prime',
    type: 'coding',
    status: 'thinking',
    model: 'gemini-3-pro-preview',
    task: 'Refactoring auth module',
    progress: 34,
    uptime: '5h 12m',
    tools: ['FileSystem', 'Git Control', 'TypeScript Compiler', 'Linter'],
    dependencies: ['1'], // Depends on Research-Alpha
    config: {
      temperature: 0.1,
      topP: 0.95,
      topK: 64,
      maxOutputTokens: 16384,
      systemInstruction: "You are a 10x Full Stack Engineer. Write clean, SOLID, and performant code. Always include type definitions. Prefer functional patterns over class-based inheritance.",
      promptHistory: [
         { version: 1, timestamp: '5h ago', author: 'System', content: "You are a coding assistant." }
      ]
    }
  },
  {
    id: '3',
    name: 'Creative-Director',
    type: 'creative',
    status: 'idle',
    model: 'gemini-3-pro-image-preview',
    task: 'Waiting for prompt',
    progress: 0,
    uptime: '1d 4h',
    tools: ['Imagen 3', 'Color Palette Gen', 'Style Transfer'],
    dependencies: [],
    config: {
      temperature: 0.9,
      topP: 1.0,
      topK: 40,
      maxOutputTokens: 2048,
      systemInstruction: "You are a visionary art director. Focus on aesthetics, composition, and emotional impact. Be bold with color theory.",
      promptHistory: []
    }
  },
  {
    id: '4',
    name: 'System-Coord',
    type: 'coordinator',
    status: 'active',
    model: 'gemini-2.5-flash',
    task: 'Orchestrating resource allocation',
    progress: 92,
    uptime: '14d 2h',
    tools: ['Docker API', 'Kubernetes Control', 'System Monitor'],
    dependencies: ['1', '2', '3'],
    config: {
      temperature: 0.0,
      topP: 0.5,
      topK: 10,
      maxOutputTokens: 1024,
      systemInstruction: "You are the HYDRA system kernel. Manage agent lifecycles and resource distribution. Minimize latency and maximize throughput.",
      promptHistory: []
    }
  }
];

export const MOCK_PROJECTS: Project[] = [
  {
    id: '1',
    name: 'Hydra Self-Mod',
    status: 'active',
    agentCount: 2,
    agentIds: ['2', '4'],
    progress: 45,
    description: 'System capability expansion and UI self-generation.',
    lastUpdated: '5m ago'
  },
  {
    id: '2',
    name: 'Empire of Queens',
    status: 'active',
    agentCount: 1,
    agentIds: ['3'],
    progress: 23,
    description: 'Procedural visual novel asset generation and dialogue trees.',
    lastUpdated: '1h ago'
  },
  {
    id: '3',
    name: 'RAG Pipeline',
    status: 'paused',
    agentCount: 0,
    agentIds: [],
    progress: 78,
    description: 'Knowledge ingestion optimization for academic papers.',
    lastUpdated: '2d ago'
  },
  {
    id: '4',
    name: 'Home Automation',
    status: 'active',
    agentCount: 1,
    agentIds: ['4'],
    progress: 90,
    description: 'Smart home integration with Home Assistant and Node-RED.',
    lastUpdated: '3h ago'
  },
  {
    id: '5',
    name: 'Crypto Trader',
    status: 'blocked',
    agentCount: 0,
    agentIds: [],
    progress: 12,
    description: 'Autonomous trading bot (Pending regulatory review).',
    lastUpdated: '1w ago'
  }
];

export const MOCK_ARTIFACTS: Artifact[] = [
  {
    id: '1',
    type: 'image',
    name: 'Queen Seraphina Portrait',
    timestamp: '2m ago',
    url: 'https://picsum.photos/300/300'
  },
  {
    id: '2',
    type: 'document',
    name: 'Quantum Analysis Report',
    timestamp: '15m ago',
    url: ''
  },
  {
    id: '3',
    type: 'code',
    name: 'auth_middleware.ts',
    timestamp: '1h ago',
    url: ''
  }
];

export const MOCK_QUEENS: Queen[] = [
  {
    id: '1',
    name: 'Seraphina',
    title: 'The Radiant',
    kingdom: 'Solaria',
    archetype: 'Benevolent Ruler',
    status: { dialogue: true, sprites: true, relationships: false },
    image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Seraphina'
  },
  {
    id: '2',
    name: 'Morgana',
    title: 'The Shadow',
    kingdom: 'Umbra',
    archetype: 'Scheming Sorceress',
    status: { dialogue: true, sprites: true, relationships: true },
    image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Morgana'
  },
  {
    id: '3',
    name: 'Valentina',
    title: 'The Blade',
    kingdom: 'Ferrum',
    archetype: 'Warrior Queen',
    status: { dialogue: true, sprites: false, relationships: false },
    image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Valentina'
  },
  {
    id: '4',
    name: 'Celestine',
    title: 'The Divine',
    kingdom: 'Aethelgard',
    archetype: 'High Priestess',
    status: { dialogue: false, sprites: false, relationships: false },
    image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Celestine'
  },
  {
    id: '5',
    name: 'Isolde',
    title: 'The Frost Sovereign',
    kingdom: 'Borealis',
    archetype: 'Ice Queen',
    status: { dialogue: false, sprites: false, relationships: false },
    image: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Isolde'
  }
];

export const MOCK_NODES: Node[] = [
  {
    id: 'n1',
    name: 'hydra-ai',
    ip: '192.168.1.250',
    cpu: 24,
    ram: { used: 48, total: 128 },
    gpus: [
      { name: 'RTX 5090', util: 78, vram: 26, totalVram: 32, temp: 72, power: 320 },
      { name: 'RTX 4090', util: 45, vram: 18, totalVram: 24, temp: 65, power: 180 }
    ],
    status: 'online',
    uptime: '14d 3h'
  },
  {
    id: 'n2',
    name: 'hydra-compute',
    ip: '192.168.1.203',
    cpu: 8,
    ram: { used: 16, total: 64 },
    gpus: [
      { name: 'RTX 5070 Ti', util: 12, vram: 4, totalVram: 16, temp: 45, power: 100 }
    ],
    status: 'online',
    uptime: '5d 12h'
  },
  {
    id: 'n3',
    name: 'hydra-storage',
    ip: '192.168.1.244',
    cpu: 15,
    ram: { used: 89, total: 256 },
    gpus: [],
    status: 'online',
    uptime: '45d 2h'
  }
];

export const MOCK_SERVICES: Service[] = [
  { id: 's1', name: 'tabbyapi', node: 'hydra-ai', port: 5000, status: 'running', uptime: '14d' },
  { id: 's2', name: 'litellm', node: 'hydra-ai', port: 4000, status: 'running', uptime: '14d' },
  { id: 's3', name: 'comfyui', node: 'hydra-compute', port: 8188, status: 'running', uptime: '5d' },
  { id: 's4', name: 'postgresql', node: 'hydra-storage', port: 5432, status: 'running', uptime: '45d' },
  { id: 's5', name: 'qdrant', node: 'hydra-storage', port: 6333, status: 'running', uptime: '45d' },
  { id: 's6', name: 'homeassistant', node: 'hydra-storage', port: 8123, status: 'stopped', uptime: '0m' },
];

export const MOCK_COLLECTIONS: KnowledgeCollection[] = [
  { id: 'k1', name: 'Research Papers', docCount: 47, chunkCount: 3211, lastIngested: '2h ago', topics: ['AI', 'Quantum', 'ML'], status: 'ready' },
  { id: 'k2', name: 'Empire Lore', docCount: 21, chunkCount: 1847, lastIngested: '1d ago', topics: ['Queens', 'Kingdoms'], status: 'ready' },
  { id: 'k3', name: 'Technical Docs', docCount: 89, chunkCount: 5432, lastIngested: '3d ago', topics: ['NixOS', 'Docker', 'Hydra'], status: 'ready' },
  { id: 'k4', name: 'Project Plans', docCount: 12, chunkCount: 450, lastIngested: '5m ago', topics: ['Planning', 'Tasks'], status: 'indexing' },
];

export const MOCK_MODELS: AIModel[] = [
  { id: 'm1', name: 'Devstral-Small-2', paramSize: '24B', quantization: 'ExL2 Q6', vramUsage: 18, contextLength: '256K', status: 'loaded', provider: 'local' },
  { id: 'm2', name: 'Euryale-70B-v2.3', paramSize: '70B', quantization: 'ExL2 Q4', vramUsage: 41, contextLength: '32K', status: 'loaded', provider: 'local' },
  { id: 'm3', name: 'GPT-OSS-20B', paramSize: '20B', quantization: 'GGUF Q4', vramUsage: 0, contextLength: '8K', status: 'unloaded', provider: 'local' },
  { id: 'm4', name: 'gemini-2.5-flash', paramSize: 'Unknown', quantization: 'N/A', vramUsage: 0, contextLength: '1M', status: 'loaded', provider: 'api' },
];

export const THEME_COLORS = {
  emerald: '#10b981',
  cyan: '#06b6d4',
  amber: '#f59e0b',
  red: '#ef4444',
  neutral: '#737373',
  purple: '#a855f7'
};