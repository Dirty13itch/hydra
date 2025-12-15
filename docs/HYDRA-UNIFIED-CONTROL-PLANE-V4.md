# HYDRA UNIFIED CONTROL PLANE - COMPREHENSIVE SYNTHESIS v4.0

## The Vision: Omniscient Access to Everything

This document synthesizes ALL interaction layers, dashboards, APIs, agents, and automation systems into a cohesive unified architecture. Every aspect of the Hydra cluster becomes accessible through appropriate interfaces matched to context, urgency, and depth of interaction.

---

## LAYER 0: THE FOUNDATION - TRUTH SOURCES

Before any interface can exist, we must establish authoritative truth sources:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           TRUTH SOURCES (Ground Reality)                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ PROMETHEUS (192.168.1.244:9090) - Metrics Truth                                 ││
│  │ • Every numeric fact about cluster state                                        ││
│  │ • 60s scrape interval, 30-day retention                                        ││
│  │ • Targets: node_exporter, nvidia-smi, cadvisor, service health                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ DOCKER API (192.168.1.244:2375) - Container Truth                               ││
│  │ • Actual container states, logs, resource usage                                ││
│  │ • Via Portainer proxy or direct Docker socket                                   ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ HARDWARE DISCOVERY (192.168.1.244:8700) - Hardware Truth                        ││
│  │ • Live GPU specs via nvidia-smi queries                                        ││
│  │ • CPU topology via lscpu                                                       ││
│  │ • Network interfaces via ip/ethtool                                            ││
│  │ • Storage arrays via Unraid API                                                ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ ACTIVITY API (192.168.1.244:8700) - Autonomous Action Truth                     ││
│  │ • Every action taken by agents/automations                                     ││
│  │ • Pending approvals, outcomes, feedback                                        ││
│  │ • Audit trail with full context                                                ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ LETTA MEMORY (192.168.1.244:8283) - Semantic Truth                              ││
│  │ • Long-term memory blocks per agent                                            ││
│  │ • User preferences, system learnings                                           ││
│  │ • Episodic memory of past interactions                                         ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 1: API SURFACES - UNIFIED ACCESS

Every interface ultimately talks to these APIs:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              API SURFACE LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    HYDRA MCP PROXY (192.168.1.244:8600)                         ││
│  │                    Primary API Gateway for ALL Interfaces                        ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  CLUSTER OPERATIONS                                                             ││
│  │  GET  /health                - Service health                                   ││
│  │  GET  /cluster/status        - Full cluster overview                            ││
│  │  GET  /services/status       - All service states                               ││
│  │  GET  /services/detailed     - Services with uptime                             ││
│  │                                                                                 ││
│  │  METRICS & MONITORING                                                           ││
│  │  GET  /metrics/summary       - CPU/RAM/Disk averages                            ││
│  │  GET  /metrics/nodes         - Per-node metrics                                 ││
│  │  GET  /gpu/status            - GPU temps, VRAM, power                           ││
│  │  GET  /storage/pools         - Unraid array status                              ││
│  │                                                                                 ││
│  │  CONTAINER MANAGEMENT                                                           ││
│  │  GET  /containers/list       - All containers                                   ││
│  │  POST /containers/restart    - Restart with confirmation                        ││
│  │  POST /containers/start      - Start container                                  ││
│  │  POST /containers/stop       - Stop container                                   ││
│  │  GET  /containers/{id}/logs  - Container logs                                   ││
│  │                                                                                 ││
│  │  SAFETY & AUDIT                                                                 ││
│  │  GET  /safety/protected      - Protected containers list                        ││
│  │  GET  /safety/pending        - Pending confirmations                            ││
│  │  GET  /audit/log             - Action audit trail                               ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    HYDRA TOOLS API (192.168.1.244:8700)                         ││
│  │                    Self-Improvement & Transparency Framework                     ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  HARDWARE DISCOVERY                                                             ││
│  │  GET  /hardware/summary      - Full cluster hardware specs                      ││
│  │  GET  /hardware/gpus         - Detailed GPU inventory                           ││
│  │  GET  /hardware/storage      - Storage topology                                 ││
│  │                                                                                 ││
│  │  ACTIVITY TRACKING (Transparency Framework)                                     ││
│  │  GET  /activity              - Recent activities                                ││
│  │  GET  /activity/{id}         - Single activity detail                           ││
│  │  GET  /activity/pending      - Awaiting approval                                ││
│  │  POST /activity/{id}/approve - Approve action                                   ││
│  │  POST /activity/{id}/reject  - Reject action                                    ││
│  │                                                                                 ││
│  │  AUTONOMOUS CONTROL                                                             ││
│  │  GET  /control/mode          - Current mode (auto/supervised/safe)              ││
│  │  POST /control/mode          - Change mode                                      ││
│  │  POST /control/emergency-stop - HALT all autonomous operations                  ││
│  │  POST /control/check-action  - Policy pre-check                                 ││
│  │                                                                                 ││
│  │  SELF-IMPROVEMENT                                                               ││
│  │  GET  /diagnosis             - System self-diagnosis                            ││
│  │  GET  /knowledge/gaps        - Identified capability gaps                       ││
│  │  POST /feedback              - Capture user feedback                            ││
│  │  GET  /preferences           - Learned user preferences                         ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    LiteLLM PROXY (192.168.1.244:4000)                           ││
│  │                    Unified AI/LLM Access Point                                   ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  OpenAI-Compatible API                                                          ││
│  │  POST /v1/chat/completions   - Chat inference (any model)                       ││
│  │  POST /v1/completions        - Text completion                                  ││
│  │  POST /v1/embeddings         - Generate embeddings                              ││
│  │  GET  /v1/models             - Available models                                 ││
│  │  GET  /health                - LiteLLM health                                   ││
│  │                                                                                 ││
│  │  Model Routing:                                                                 ││
│  │  • gpt-4, llama-70b         → TabbyAPI (192.168.1.250:5000)                     ││
│  │  • gpt-3.5-turbo, qwen2.5-7b → Ollama LB (192.168.1.203:11400)                  ││
│  │  • codestral, qwen-coder    → Ollama direct                                     ││
│  │  • text-embedding-*         → Ollama embeddings                                 ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    ALERTMANAGER (192.168.1.244:9093)                            ││
│  │                    Alert Management                                              ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │  GET  /api/v2/alerts         - Current alerts                                   ││
│  │  GET  /api/v2/silences       - Active silences                                  ││
│  │  POST /api/v2/silences       - Create silence                                   ││
│  │  DELETE /api/v2/silence/{id} - Delete silence                                   ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    LETTA API (192.168.1.244:8283)                               ││
│  │                    Agent Memory & Conversation                                   ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │  GET  /v1/agents/            - List agents                                      ││
│  │  GET  /v1/agents/{id}/messages - Agent message history                          ││
│  │  POST /v1/agents/{id}/messages - Send message to agent                          ││
│  │  GET  /v1/agents/{id}/memory  - Agent memory blocks                             ││
│  │  PUT  /v1/agents/{id}/memory  - Update memory                                   ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    OLLAMA API (192.168.1.203:11400 LB)                          ││
│  │                    Model Management & Direct Inference                           ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │  GET  /api/tags              - Available models                                 ││
│  │  GET  /api/ps                - Running models                                   ││
│  │  POST /api/generate          - Generate (load/unload via keep_alive)            ││
│  │  POST /api/chat              - Chat completion                                  ││
│  │  POST /api/embeddings        - Embeddings                                       ││
│  │  POST /api/pull              - Pull new model                                   ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 2: VISUAL INTERFACES - THE DASHBOARDS

Multiple views into the same truth, optimized for different purposes:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           VISUAL INTERFACE LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    TYPHON COMMAND (Custom React Dashboard)                       ││
│  │                    PRIMARY CONTROL INTERFACE                                     ││
│  │                    Deployed via hydra-storage container                          ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Unified cluster control optimized for Shaun's workflow                ││
│  │                                                                                 ││
│  │  FEATURES:                                                                      ││
│  │  • Real-time cluster health (5s refresh)                                        ││
│  │  • Node cards with GPU metrics (RTX 5090, 4090, 5070 Ti x2, Arc A380)           ││
│  │  • Container management (start/stop/restart with safety rails)                  ││
│  │  • Service dependency graph                                                     ││
│  │  • AI model panel (Ollama models, load/unload)                                  ││
│  │  • Letta chat widget (talk to hydra-steward)                                    ││
│  │  • Alert panel (from Alertmanager, with silence capability)                     ││
│  │  • Storage pools visualization (Unraid array status)                            ││
│  │  • Audit log (recent actions)                                                   ││
│  │  • Quick actions menu                                                           ││
│  │  • Keyboard shortcuts (?, r for refresh)                                        ││
│  │  • Pull-to-refresh on mobile                                                    ││
│  │  • Metrics sparklines with history                                              ││
│  │                                                                                 ││
│  │  DATA SOURCES:                                                                  ││
│  │  └── Hydra MCP Proxy (8600) - all endpoints                                     ││
│  │  └── Alertmanager (9093) - alerts                                               ││
│  │  └── Ollama API (11400) - model management                                      ││
│  │  └── Letta API (8283) - agent chat                                              ││
│  │  └── Hydra Tools API (8700) - transparency framework                            ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    HOMEPAGE (192.168.1.244:3333)                                ││
│  │                    SERVICE LAUNCHER & QUICK ACCESS                               ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Quick-launch portal for all services                                  ││
│  │                                                                                 ││
│  │  CATEGORIES:                                                                    ││
│  │  • AI & Inference: Open WebUI, TabbyAPI, Ollama, LiteLLM, ComfyUI              ││
│  │  • Monitoring: Grafana, Prometheus, Alertmanager, Uptime Kuma                  ││
│  │  • Databases: Qdrant, PostgreSQL (pgAdmin), Redis                              ││
│  │  • Automation: n8n, Home Assistant                                             ││
│  │  • Media: Plex, *Arr stack, Stash                                              ││
│  │  • Infrastructure: Portainer, AdGuard                                          ││
│  │                                                                                 ││
│  │  WIDGETS:                                                                       ││
│  │  • Service status indicators                                                    ││
│  │  • Quick system stats                                                           ││
│  │  • Bookmarks for external services                                              ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    GRAFANA (192.168.1.244:3003)                                 ││
│  │                    DEEP METRICS VISUALIZATION                                    ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Deep-dive metrics, historical analysis, alerting                      ││
│  │                                                                                 ││
│  │  DASHBOARDS:                                                                    ││
│  │  • Cluster Overview - All nodes, GPU temps, VRAM, power                         ││
│  │  • Node Deep-Dive - Per-node CPU, RAM, disk, network                            ││
│  │  • GPU Analytics - VRAM trends, utilization, thermal throttling                ││
│  │  • Container Metrics - Resource usage per container                             ││
│  │  • Inference Performance - Tokens/sec, latency percentiles                     ││
│  │  • Storage Analytics - Array health, disk temps, I/O                           ││
│  │                                                                                 ││
│  │  DATA SOURCE: Prometheus (9090)                                                 ││
│  │  ALERTING: Integrated with Alertmanager                                         ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    UPTIME KUMA (192.168.1.244:3001)                             ││
│  │                    AVAILABILITY MONITORING                                       ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Simple uptime tracking, status pages, alerting                        ││
│  │                                                                                 ││
│  │  MONITORS (40+ configured):                                                     ││
│  │  • Inference: TabbyAPI, Ollama (both instances), LiteLLM                        ││
│  │  • AI Services: Open WebUI, ComfyUI, Letta, SearXNG, Perplexica                ││
│  │  • Databases: PostgreSQL, Redis, Qdrant                                         ││
│  │  • Monitoring: Prometheus, Grafana, Alertmanager, Loki                          ││
│  │  • Automation: n8n, Home Assistant                                              ││
│  │  • Media: Plex, *Arr stack                                                      ││
│  │  • Infrastructure: Portainer, AdGuard, Hydra MCP, Hydra Tools                   ││
│  │  • Nodes: SSH on all 3 nodes                                                    ││
│  │                                                                                 ││
│  │  ALERTS: Webhook to n8n for automation, Discord for notifications              ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    PORTAINER (192.168.1.244:9000)                               ││
│  │                    CONTAINER MANAGEMENT                                          ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Direct container management, logs, exec, compose                      ││
│  │                                                                                 ││
│  │  FEATURES:                                                                      ││
│  │  • Container lifecycle (start/stop/restart/kill)                                ││
│  │  • Live logs streaming                                                          ││
│  │  • Container shell access                                                       ││
│  │  • Docker Compose stack management                                              ││
│  │  • Image management                                                             ││
│  │  • Network inspection                                                           ││
│  │  • Volume management                                                            ││
│  │                                                                                 ││
│  │  USE WHEN: Need direct container access Typhon doesn't provide                  ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 3: CONVERSATIONAL INTERFACES - AI CHAT

Natural language access to everything:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        CONVERSATIONAL INTERFACE LAYER                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    OPEN WEBUI (192.168.1.250:3000)                              ││
│  │                    PRIMARY CHAT INTERFACE                                        ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: General AI chat, model switching, document analysis                   ││
│  │                                                                                 ││
│  │  MODELS AVAILABLE (via LiteLLM):                                                ││
│  │  • 70B (quality): llama-70b, gpt-4, hydra-70b                                   ││
│  │  • 7B-14B (fast): qwen2.5-7b, qwen2.5-14b, gpt-3.5-turbo                        ││
│  │  • Code: qwen-coder, codestral                                                  ││
│  │  • CPU fallback: llama-7b-cpu, qwen-7b-cpu                                      ││
│  │                                                                                 ││
│  │  FEATURES:                                                                      ││
│  │  • Multi-model conversations                                                    ││
│  │  • Document upload & RAG                                                        ││
│  │  • Conversation history                                                         ││
│  │  • Custom system prompts                                                        ││
│  │  • Image generation (via ComfyUI)                                               ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    LETTA CHAT (Embedded in Typhon Command)                      ││
│  │                    HYDRA-STEWARD AGENT                                          ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Conversational cluster control via Hydra Steward agent                ││
│  │                                                                                 ││
│  │  CAPABILITIES:                                                                  ││
│  │  • "Check the health of hydra-ai"                                               ││
│  │  • "Restart the ollama container"                                               ││
│  │  • "What's using the most VRAM right now?"                                      ││
│  │  • "Switch to a faster model for quick tasks"                                   ││
│  │  • "Create an alert silence for maintenance"                                    ││
│  │                                                                                 ││
│  │  MEMORY BLOCKS:                                                                 ││
│  │  • cluster_state: Current infrastructure status                                 ││
│  │  • user_preferences: Shaun's preferences and patterns                           ││
│  │  • capabilities: What the agent can do                                          ││
│  │  • recent_actions: What's been done recently                                    ││
│  │  • system_learnings: Accumulated knowledge                                      ││
│  │                                                                                 ││
│  │  TOOLS (via MCP):                                                               ││
│  │  • check_service_health                                                         ││
│  │  • restart_container                                                            ││
│  │  • query_prometheus                                                             ││
│  │  • manage_alerts                                                                ││
│  │  • switch_model                                                                 ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    SILLYTAVERN (192.168.1.244:8000)                             ││
│  │                    CREATIVE & ROLEPLAY INTERFACE                                 ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Creative writing, character roleplay, storytelling                    ││
│  │                                                                                 ││
│  │  FEATURES:                                                                      ││
│  │  • Character cards with persistent memory                                       ││
│  │  • World info/lorebooks                                                         ││
│  │  • Multiple personas                                                            ││
│  │  • Advanced prompt formatting                                                   ││
│  │  • Chat export/import                                                           ││
│  │                                                                                 ││
│  │  BACKEND: TabbyAPI via LiteLLM (70B uncensored for creative freedom)            ││
│  │                                                                                 ││
│  │  USE FOR: Empire of Broken Queens, creative projects                            ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    CLAUDE CODE (via MCP)                                        ││
│  │                    DEVELOPMENT INTERFACE                                         ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Code development with cluster awareness                               ││
│  │                                                                                 ││
│  │  MCP SERVERS CONNECTED:                                                         ││
│  │  • hydra-mcp-proxy: Cluster control & status                                    ││
│  │  • filesystem: Project file access                                              ││
│  │  • fetch: Web research                                                          ││
│  │                                                                                 ││
│  │  CONTEXT: Full CLAUDE.md with cluster state, IPs, services                      ││
│  │                                                                                 ││
│  │  CAPABILITIES:                                                                  ││
│  │  • SSH to any node                                                              ││
│  │  • Docker operations                                                            ││
│  │  • Configuration updates                                                        ││
│  │  • Code generation with cluster context                                         ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    PERPLEXICA (192.168.1.244:3030)                              ││
│  │                    AI-POWERED RESEARCH                                          ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  PURPOSE: Research questions with web search + AI synthesis                     ││
│  │                                                                                 ││
│  │  BACKENDS:                                                                      ││
│  │  • Search: SearXNG (192.168.1.244:8888)                                         ││
│  │  • Crawling: Firecrawl (192.168.1.244:3005)                                     ││
│  │  • LLM: via LiteLLM                                                             ││
│  │                                                                                 ││
│  │  USE FOR: Technical research, documentation lookup, fact-checking              ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 4: AUTOMATION - SELF-OPERATING SYSTEMS

The cluster operates itself:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           AUTOMATION LAYER                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    N8N WORKFLOWS (192.168.1.244:5678)                           ││
│  │                    EVENT-DRIVEN AUTOMATION                                       ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  MONITORING WORKFLOWS:                                                          ││
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   ││
│  │  │ Daily Health Digest (8:00 AM CST)                                       │   ││
│  │  │ ├── Query Prometheus for cluster stats                                  │   ││
│  │  │ ├── Check all service health endpoints                                  │   ││
│  │  │ ├── Compile storage usage report                                        │   ││
│  │  │ ├── Generate summary via 7B model                                       │   ││
│  │  │ └── Send to Discord/notification channel                                │   ││
│  │  └─────────────────────────────────────────────────────────────────────────┘   ││
│  │                                                                                 ││
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   ││
│  │  │ Resource Monitor (Continuous)                                           │   ││
│  │  │ ├── Poll Prometheus every 5 minutes                                     │   ││
│  │  │ ├── Check GPU temp > 80°C → Alert + reduce power limit                  │   ││
│  │  │ ├── Check VRAM > 95% → Alert + suggest model switch                     │   ││
│  │  │ ├── Check disk > 90% → Trigger cleanup                                  │   ││
│  │  │ └── Log all events to Activity API                                      │   ││
│  │  └─────────────────────────────────────────────────────────────────────────┘   ││
│  │                                                                                 ││
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   ││
│  │  │ Container Auto-Recovery (On Failure)                                    │   ││
│  │  │ ├── Webhook from Uptime Kuma or Alertmanager                            │   ││
│  │  │ ├── Check failure count (max 3/hour per container)                      │   ││
│  │  │ ├── If under limit: attempt restart via MCP                             │   ││
│  │  │ ├── If over limit: alert human, enter safe mode                         │   ││
│  │  │ └── Log action + outcome to Activity API                                │   ││
│  │  └─────────────────────────────────────────────────────────────────────────┘   ││
│  │                                                                                 ││
│  │  INTELLIGENCE WORKFLOWS:                                                        ││
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   ││
│  │  │ Research Queue Processor (On Demand)                                    │   ││
│  │  │ ├── Pick topic from queue (Qdrant collection)                           │   ││
│  │  │ ├── Run SearXNG searches                                                │   ││
│  │  │ ├── Crawl top results via Firecrawl                                     │   ││
│  │  │ ├── Summarize via 70B model                                             │   ││
│  │  │ ├── Store in Qdrant for RAG                                             │   ││
│  │  │ └── Update Letta memory with learnings                                  │   ││
│  │  └─────────────────────────────────────────────────────────────────────────┘   ││
│  │                                                                                 ││
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   ││
│  │  │ Model Performance Tracker (Hourly)                                      │   ││
│  │  │ ├── Query TabbyAPI /metrics for tokens/sec                              │   ││
│  │  │ ├── Query Ollama instances for load                                     │   ││
│  │  │ ├── Calculate utilization percentages                                   │   ││
│  │  │ ├── Store in Prometheus via pushgateway                                 │   ││
│  │  │ └── Update Letta model_performance memory block                         │   ││
│  │  └─────────────────────────────────────────────────────────────────────────┘   ││
│  │                                                                                 ││
│  │  HOME AUTOMATION WORKFLOWS (via Home Assistant):                                ││
│  │  ┌─────────────────────────────────────────────────────────────────────────┐   ││
│  │  │ • Away Mode: Reduce GPU power limits, pause non-essential containers    │   ││
│  │  │ • Night Mode: Queue batch processing, quiet notifications               │   ││
│  │  │ • Work Mode: Full power, priority to inference                          │   ││
│  │  │ • Media Mode: Ensure Plex has transcoding resources                     │   ││
│  │  └─────────────────────────────────────────────────────────────────────────┘   ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                    PROMETHEUS ALERTING                                          ││
│  │                    METRIC-BASED AUTOMATION TRIGGERS                              ││
│  ├─────────────────────────────────────────────────────────────────────────────────┤│
│  │                                                                                 ││
│  │  CONFIGURED ALERTS (hydra-alerts.yml):                                          ││
│  │                                                                                 ││
│  │  CRITICAL:                                                                      ││
│  │  • NodeDown - Any node unreachable for 2 minutes                                ││
│  │  • GPUTemperatureCritical - GPU > 85°C for 1 minute                            ││
│  │  • VRAMCritical - VRAM > 95% for 5 minutes                                      ││
│  │  • DiskSpaceCritical - Disk > 95% for 5 minutes                                 ││
│  │                                                                                 ││
│  │  WARNING:                                                                       ││
│  │  • GPUTemperatureHigh - GPU > 80°C for 5 minutes                                ││
│  │  • VRAMHigh - VRAM > 90% for 10 minutes                                         ││
│  │  • CPUHigh - CPU > 90% for 10 minutes                                           ││
│  │  • MemoryHigh - RAM > 90% for 10 minutes                                        ││
│  │  • DiskSpaceWarning - Disk > 85% for 10 minutes                                 ││
│  │                                                                                 ││
│  │  SERVICE:                                                                       ││
│  │  • LokiDown - Loki unhealthy for 5 minutes                                      ││
│  │  • QdrantDown - Qdrant unhealthy for 2 minutes                                  ││
│  │  • InferenceDown - TabbyAPI/Ollama unhealthy for 1 minute                       ││
│  │                                                                                 ││
│  │  DESTINATIONS:                                                                  ││
│  │  └── Alertmanager → n8n webhook → Discord + Activity API                        ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 5: AGENT ORCHESTRATION - AUTONOMOUS INTELLIGENCE

Multi-agent systems that work together:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENT ORCHESTRATION LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│                          ┌─────────────────────────────┐                            │
│                          │     TYPHON ORCHESTRATOR     │                            │
│                          │     (EPYC 7663 + 180GB)     │                            │
│                          │                             │                            │
│                          │  Coordinates all agents     │                            │
│                          │  Resource allocation        │                            │
│                          │  Priority management        │                            │
│                          └──────────────┬──────────────┘                            │
│                                         │                                            │
│         ┌───────────────────────────────┼───────────────────────────────┐            │
│         │                               │                               │            │
│         ▼                               ▼                               ▼            │
│  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐     │
│  │  STEWARD AGENT   │         │  RESEARCH CREW   │         │ DEVELOPMENT CREW │     │
│  │     (Letta)      │         │    (CrewAI)      │         │   (LangGraph)    │     │
│  │                  │         │                  │         │                  │     │
│  │ Always-on       │         │ On-demand        │         │ On-demand        │     │
│  │ Cluster guardian │         │ Web research     │         │ Code generation  │     │
│  │ User interaction │         │ Analysis         │         │ Testing          │     │
│  │                  │         │                  │         │                  │     │
│  │ LLM: 7B (fast)  │         │ LLM: 7B          │         │ LLM: 70B         │     │
│  │ Memory: Letta   │         │ Tools: SearXNG,  │         │ Tools: Exec,     │     │
│  │ Tools: MCP      │         │   Firecrawl      │         │   FileSystem     │     │
│  └──────────────────┘         └──────────────────┘         └──────────────────┘     │
│                                                                                      │
│         ┌───────────────────────────────┬───────────────────────────────┐            │
│         │                               │                               │            │
│         ▼                               ▼                               ▼            │
│  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐     │
│  │  CREATIVE CREW   │         │  MAINTENANCE     │         │    QA AGENT      │     │
│  │    (CrewAI)      │         │     CREW         │         │   (Standalone)   │     │
│  │                  │         │                  │         │                  │     │
│  │ On-demand        │         │ Scheduled        │         │ Per-output       │     │
│  │ Image generation │         │ Cleanup tasks    │         │ Quality check    │     │
│  │ Character art    │         │ Optimization     │         │ Feedback capture │     │
│  │ Voice synthesis  │         │ Capacity plan    │         │                  │     │
│  │                  │         │                  │         │                  │     │
│  │ LLM: 70B        │         │ LLM: 7B          │         │ LLM: Different   │     │
│  │ Tools: ComfyUI, │         │ Tools: Docker,   │         │   model tier     │     │
│  │   Kokoro TTS    │         │   SSH, Bash      │         │                  │     │
│  └──────────────────┘         └──────────────────┘         └──────────────────┘     │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         SHARED MEMORY LAYER (Letta + Qdrant)                    ││
│  │                                                                                 ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           ││
│  │  │  Working    │  │  Episodic   │  │  Semantic   │  │   Model     │           ││
│  │  │  Memory     │  │  Memory     │  │  Memory     │  │ Performance │           ││
│  │  │             │  │             │  │             │  │             │           ││
│  │  │ Active      │  │ Task        │  │ RAG index   │  │ Benchmarks  │           ││
│  │  │ context     │  │ history     │  │ Knowledge   │  │ Latency     │           ││
│  │  │ Scratch     │  │ Outcomes    │  │ Preferences │  │ Routing     │           ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘           ││
│  │                                                                                 ││
│  │  Vector Store: Qdrant (192.168.1.244:6333)                                     ││
│  │  Collections: query_cache, documents, research, empire_of_broken_queens        ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  AGENT CONCURRENCY LIMITS:                                                          │
│  ├── Steward: 1 (always running)                                                    │
│  ├── Research: 4 concurrent                                                         │
│  ├── Development: 2 concurrent                                                      │
│  ├── Creative: 2 concurrent (GPU-bound)                                             │
│  ├── Maintenance: 4 concurrent                                                      │
│  └── Total burst: 12 parallel agents                                                │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 6: VOICE INTERFACE - HANDS-FREE CONTROL

Natural spoken interaction:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           VOICE INTERFACE LAYER                                      │
│                           Target: <500ms first word                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                              VOICE PIPELINE                                      ││
│  │                                                                                 ││
│  │  ┌──────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ ││
│  │  │  WAKE    │   │  STREAMING   │   │   ROUTELLM   │   │   STREAMING TTS      │ ││
│  │  │  WORD    │──▶│    STT       │──▶│   + LLM      │──▶│   (Kokoro)           │ ││
│  │  │          │   │              │   │              │   │                      │ ││
│  │  │"Hey      │   │ faster-      │   │ Simple→7B   │   │ Stream audio         │ ││
│  │  │ Hydra"   │   │ whisper      │   │ Complex→70B │   │ chunks as            │ ││
│  │  │          │   │              │   │              │   │ generated            │ ││
│  │  └──────────┘   └──────────────┘   └──────────────┘   └──────────────────────┘ ││
│  │       │                │                 │                      │              ││
│  │       │                │                 │                      │              ││
│  │       ▼                ▼                 ▼                      ▼              ││
│  │   Satellite        hydra-storage     hydra-ai or          hydra-storage       ││
│  │   (ESP32 or        (EPYC 7663)       hydra-compute         (Kokoro:8880)       ││
│  │    Raspberry Pi)                                                               ││
│  │                                                                                 ││
│  │  LATENCY BREAKDOWN:                                                            ││
│  │  ├── Wake word detection: ~50ms (local on satellite)                           ││
│  │  ├── Streaming STT: ~200ms (first words recognized)                            ││
│  │  ├── LLM first token: ~150ms (7B) or ~500ms (70B)                              ││
│  │  └── Streaming TTS first audio: ~100ms                                         ││
│  │                                                                                 ││
│  │  TOTAL (simple): ~500ms first word                                             ││
│  │  TOTAL (complex): ~850ms first word                                            ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         VOICE COMMAND CATEGORIES                                ││
│  │                                                                                 ││
│  │  CLUSTER CONTROL:                                                              ││
│  │  • "Hey Hydra, check the health of all services"                               ││
│  │  • "What's the GPU temperature on hydra-ai?"                                   ││
│  │  • "Restart the Ollama container"                                              ││
│  │  • "Switch to the faster model"                                                ││
│  │  • "Show me the current VRAM usage"                                            ││
│  │                                                                                 ││
│  │  HOME AUTOMATION:                                                              ││
│  │  • "Turn on movie mode" (dim lights, quiet notifications)                      ││
│  │  • "Set the office to work mode" (full power, optimal lighting)               ││
│  │  • "I'm leaving" (away mode, reduce power consumption)                         ││
│  │                                                                                 ││
│  │  INFORMATION:                                                                  ││
│  │  • "What's on my calendar today?"                                              ││
│  │  • "Summarize my unread emails"                                                ││
│  │  • "What's the weather forecast?"                                              ││
│  │  • "Research the latest on ExLlamaV3"                                          ││
│  │                                                                                 ││
│  │  CREATIVE:                                                                     ││
│  │  • "Generate a portrait of [character]"                                        ││
│  │  • "Continue the story from where we left off"                                 ││
│  │  • "Read me the latest chapter"                                                ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         HOME ASSISTANT INTEGRATION                              ││
│  │                         (192.168.1.244:8123)                                    ││
│  │                                                                                 ││
│  │  DEVICES (Planned):                                                            ││
│  │  • Lutron Caseta: Smart lighting                                               ││
│  │  • Bond Bridge: Ceiling fans, blinds                                           ││
│  │  • Nest: Thermostat, protect                                                   ││
│  │  • Ring: Doorbell, cameras                                                     ││
│  │  • Sonos: Multi-room audio                                                     ││
│  │                                                                                 ││
│  │  INTEGRATIONS:                                                                 ││
│  │  • Wyoming protocol for voice satellite                                        ││
│  │  • Custom sentences for Hydra commands                                         ││
│  │  • Automations triggered by LLM responses                                      ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 7: TRANSPARENCY & GOVERNANCE - TRUST FRAMEWORK

How autonomy is governed:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       TRANSPARENCY & GOVERNANCE LAYER                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         ACTIVITY TRACKING                                       ││
│  │                                                                                 ││
│  │  EVERY autonomous action is logged:                                            ││
│  │                                                                                 ││
│  │  {                                                                             ││
│  │    "id": 12345,                                                                ││
│  │    "timestamp": "2025-12-14T10:30:00Z",                                        ││
│  │    "source": "n8n",                                                            ││
│  │    "source_id": "workflow_health_digest",                                      ││
│  │    "action": "generate_health_report",                                         ││
│  │    "action_type": "scheduled",                                                 ││
│  │    "target": "cluster",                                                        ││
│  │    "params": {"scope": "all_nodes"},                                           ││
│  │    "result": "ok",                                                             ││
│  │    "result_details": {"services_checked": 40, "alerts_found": 0},              ││
│  │    "decision_reason": "Daily 8AM schedule",                                    ││
│  │    "requires_approval": false                                                  ││
│  │  }                                                                             ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         OPERATING MODES                                         ││
│  │                                                                                 ││
│  │  ┌───────────────────────────────────────────────────────────────────────────┐ ││
│  │  │ FULL_AUTO - Maximum autonomy                                              │ ││
│  │  │ • Execute all actions without approval                                    │ ││
│  │  │ • Container restarts, model switches, cleanup                             │ ││
│  │  │ • Only destructive actions still blocked                                  │ ││
│  │  └───────────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                                 ││
│  │  ┌───────────────────────────────────────────────────────────────────────────┐ ││
│  │  │ SUPERVISED - Approval for important actions                               │ ││
│  │  │ • Read operations: auto-approved                                          │ ││
│  │  │ • Container restarts: require approval                                    │ ││
│  │  │ • Config changes: require approval                                        │ ││
│  │  │ • Cleanup operations: require approval                                    │ ││
│  │  └───────────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                                 ││
│  │  ┌───────────────────────────────────────────────────────────────────────────┐ ││
│  │  │ NOTIFY_ONLY - No autonomous execution                                     │ ││
│  │  │ • Log all proposed actions                                                │ ││
│  │  │ • Send notifications                                                      │ ││
│  │  │ • Wait for explicit human execution                                       │ ││
│  │  └───────────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                                 ││
│  │  ┌───────────────────────────────────────────────────────────────────────────┐ ││
│  │  │ SAFE_MODE - Emergency lockdown                                            │ ││
│  │  │ • All autonomous operations suspended                                     │ ││
│  │  │ • Only manual operations via Portainer/SSH                                │ ││
│  │  │ • Activated by emergency-stop endpoint or 3+ failures                     │ ││
│  │  └───────────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         APPROVAL WORKFLOW                                       ││
│  │                                                                                 ││
│  │  1. Agent/automation proposes action                                           ││
│  │     └── POST /control/check-action → {requires_approval: true}                 ││
│  │                                                                                 ││
│  │  2. Action logged as "pending" in Activity API                                 ││
│  │     └── POST /activity with status="pending"                                   ││
│  │                                                                                 ││
│  │  3. User notified via:                                                         ││
│  │     ├── Typhon Command UI (pending approvals badge)                            ││
│  │     ├── Discord notification                                                   ││
│  │     └── Optional: Voice prompt "Action requires approval"                      ││
│  │                                                                                 ││
│  │  4. User reviews and decides:                                                  ││
│  │     ├── POST /activity/{id}/approve → Execute action                           ││
│  │     └── POST /activity/{id}/reject  → Log rejection, inform agent              ││
│  │                                                                                 ││
│  │  5. Outcome logged with full audit trail                                       ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         PROTECTED RESOURCES                                     ││
│  │                                                                                 ││
│  │  NEVER automatically modified/deleted:                                         ││
│  │  • hydra-postgres (database)                                                   ││
│  │  • hydra-redis (cache/state)                                                   ││
│  │  • hydra-qdrant (vectors)                                                      ││
│  │  • tabbyapi (primary inference)                                                ││
│  │  • prometheus, loki (observability)                                            ││
│  │  • vaultwarden (secrets)                                                       ││
│  │  • home-assistant (automation)                                                 ││
│  │                                                                                 ││
│  │  Restart allowed but requires confirmation:                                    ││
│  │  • All other containers                                                        ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## LAYER 8: SELF-IMPROVEMENT - CONTINUOUS EVOLUTION

The system that makes itself better:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         SELF-IMPROVEMENT LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         FEEDBACK CAPTURE                                        ││
│  │                                                                                 ││
│  │  EXPLICIT FEEDBACK:                                                            ││
│  │  • Thumbs up/down on LLM responses                                             ││
│  │  • Corrections ("Actually, I meant...")                                        ││
│  │  • Preference statements ("I prefer shorter answers")                          ││
│  │  • Task outcome ratings                                                        ││
│  │                                                                                 ││
│  │  IMPLICIT FEEDBACK:                                                            ││
│  │  • Follow-up questions (indicates incomplete answer)                           ││
│  │  • Repeated queries (indicates failure to understand)                          ││
│  │  • Manual overrides (indicates wrong autonomous decision)                      ││
│  │  • Time to approval (fast = trusted, slow = uncertain)                         ││
│  │                                                                                 ││
│  │  STORAGE:                                                                      ││
│  │  └── POST /feedback → Letta memory + Qdrant (searchable)                       ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         PREFERENCE LEARNING                                     ││
│  │                                                                                 ││
│  │  LEARNED PREFERENCES (auto-updated in Letta memory):                           ││
│  │                                                                                 ││
│  │  {                                                                             ││
│  │    "response_style": {                                                         ││
│  │      "verbosity": "concise",                                                   ││
│  │      "formatting": "markdown",                                                 ││
│  │      "emojis": "none",                                                         ││
│  │      "technical_depth": "high"                                                 ││
│  │    },                                                                          ││
│  │    "interaction_patterns": {                                                   ││
│  │      "approval_threshold": "medium_risk",                                      ││
│  │      "notification_frequency": "important_only",                               ││
│  │      "preferred_model_tier": "quality_over_speed"                              ││
│  │    },                                                                          ││
│  │    "domain_preferences": {                                                     ││
│  │      "code_style": "typescript",                                               ││
│  │      "infrastructure": "nixos_preferred",                                      ││
│  │      "documentation": "minimal"                                                ││
│  │    },                                                                          ││
│  │    "timing": {                                                                 ││
│  │      "active_hours": "9am-11pm_cst",                                           ││
│  │      "batch_processing": "overnight"                                           ││
│  │    }                                                                           ││
│  │  }                                                                             ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         SELF-DIAGNOSIS ENGINE                                   ││
│  │                                                                                 ││
│  │  ANALYZES:                                                                     ││
│  │  • Failed tasks (why did they fail?)                                           ││
│  │  • Slow responses (bottleneck identification)                                  ││
│  │  • Rejected approvals (what made user reject?)                                 ││
│  │  • Resource contention (GPU/CPU/memory patterns)                               ││
│  │                                                                                 ││
│  │  OUTPUTS:                                                                      ││
│  │  • GET /diagnosis → Current system issues + recommendations                    ││
│  │  • GET /knowledge/gaps → Capability gaps identified                            ││
│  │                                                                                 ││
│  │  EXAMPLE OUTPUT:                                                               ││
│  │  {                                                                             ││
│  │    "diagnosis": [                                                              ││
│  │      {                                                                         ││
│  │        "issue": "70B model response time increasing",                          ││
│  │        "probable_cause": "context length growth",                              ││
│  │        "recommendation": "implement context pruning",                          ││
│  │        "confidence": 0.85                                                      ││
│  │      }                                                                         ││
│  │    ],                                                                          ││
│  │    "gaps": [                                                                   ││
│  │      {                                                                         ││
│  │        "capability": "calendar integration",                                   ││
│  │        "frequency_requested": 12,                                              ││
│  │        "implementation_status": "not_started"                                  ││
│  │      }                                                                         ││
│  │    ]                                                                           ││
│  │  }                                                                             ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │                         IMPROVEMENT LOOPS                                       ││
│  │                                                                                 ││
│  │  PER-TASK LOOP (Immediate):                                                    ││
│  │  ├── Execute task                                                              ││
│  │  ├── Capture outcome + feedback                                                ││
│  │  ├── Update working memory                                                     ││
│  │  └── Adjust next response based on feedback                                    ││
│  │                                                                                 ││
│  │  DAILY LOOP (8 AM):                                                            ││
│  │  ├── Aggregate yesterday's activities                                          ││
│  │  ├── Run self-diagnosis                                                        ││
│  │  ├── Update preference weights                                                 ││
│  │  ├── Consolidate episodic → semantic memory                                    ││
│  │  └── Generate improvement suggestions                                          ││
│  │                                                                                 ││
│  │  WEEKLY LOOP (Sunday):                                                         ││
│  │  ├── Comprehensive performance analysis                                        ││
│  │  ├── Prompt template refinement                                                ││
│  │  ├── Model routing rule updates                                                ││
│  │  ├── Tool effectiveness review                                                 ││
│  │  └── Propose configuration changes                                             ││
│  │                                                                                 ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## THE COMPLETE PICTURE - HOW IT ALL CONNECTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                    HYDRA UNIFIED CONTROL PLANE - COMPLETE ARCHITECTURE                                          │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                                                  │
│      USER TOUCHPOINTS                                                                                                                           │
│      ═══════════════                                                                                                                            │
│                                                                                                                                                  │
│      ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐                              │
│      │ Typhon   │    │   Open   │    │  Sillly  │    │  Claude  │    │  Voice   │    │  Home    │    │ Mobile   │                              │
│      │ Command  │    │  WebUI   │    │  Tavern  │    │   Code   │    │Assistant │    │Assistant │    │  App     │                              │
│      │ (custom) │    │ (chat)   │    │(creative)│    │  (dev)   │    │ (voice)  │    │ (home)   │    │ (future) │                              │
│      └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘                              │
│           │               │               │               │               │               │               │                                     │
│           └───────────────┴───────────────┴───────────────┴───────────────┴───────────────┴───────────────┘                                     │
│                                                           │                                                                                      │
│                                                           ▼                                                                                      │
│      API GATEWAY LAYER                               ┌─────────────────────────────────────────────────┐                                        │
│      ═════════════════                               │               UNIFIED API SURFACE               │                                        │
│                                                      │                                                 │                                        │
│      ┌───────────────────────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────────────────┐   │
│      │                                               │                                                 │                                   │   │
│      │  ┌─────────────────┐  ┌─────────────────┐    │    ┌─────────────────┐  ┌─────────────────┐    │  ┌─────────────────┐              │   │
│      │  │   Hydra MCP     │  │  Hydra Tools    │    │    │    LiteLLM      │  │   Alertmanager  │    │  │    Letta API    │              │   │
│      │  │   (8600)        │  │   API (8700)    │    │    │    (4000)       │  │    (9093)       │    │  │    (8283)       │              │   │
│      │  │                 │  │                 │    │    │                 │  │                 │    │  │                 │              │   │
│      │  │ Cluster ops     │  │ Transparency    │    │    │ Model routing   │  │ Alert mgmt      │    │  │ Agent memory    │              │   │
│      │  │ Containers      │  │ Hardware        │    │    │ OpenAI compat   │  │ Silencing       │    │  │ Conversation    │              │   │
│      │  │ Metrics         │  │ Autonomy ctrl   │    │    │ Fallbacks       │  │                 │    │  │                 │              │   │
│      │  └────────┬────────┘  └────────┬────────┘    │    └────────┬────────┘  └────────┬────────┘    │  └────────┬────────┘              │   │
│      │           │                    │             │             │                    │             │           │                        │   │
│      └───────────┼────────────────────┼─────────────┼─────────────┼────────────────────┼─────────────┼───────────┼────────────────────────┘   │
│                  │                    │             │             │                    │             │           │                             │
│                  └────────────────────┴─────────────┴─────────────┴────────────────────┴─────────────┴───────────┘                             │
│                                                           │                                                                                      │
│                                                           ▼                                                                                      │
│      INTELLIGENCE LAYER                             ┌─────────────────────────────────────────────────┐                                        │
│      ══════════════════                             │              INFERENCE BACKENDS                 │                                        │
│                                                     │                                                 │                                        │
│      ┌──────────────────────────────────────────────┼─────────────────────────────────────────────────┼──────────────────────────────────────┐│
│      │                                              │                                                 │                                      ││
│      │  hydra-ai (192.168.1.250)                   │     hydra-compute (192.168.1.203)              │    hydra-storage (192.168.1.244)     ││
│      │  RTX 5090 32GB + RTX 4090 24GB              │     2x RTX 5070 Ti 16GB                        │    EPYC 7663 + 180GB RAM             ││
│      │                                              │                                                 │                                      ││
│      │  ┌───────────────────────────────────────┐  │     ┌───────────────────────────────────────┐  │    ┌───────────────────────────────┐ ││
│      │  │           TabbyAPI (:5000)            │  │     │   Ollama GPU0 (:11434)                │  │    │    CPU Inference Fallback     │ ││
│      │  │                                       │  │     │   Ollama GPU1 (:11435)                │  │    │    (when GPUs saturated)      │ ││
│      │  │   ExLlamaV2 Tensor Parallel           │  │     │   Nginx LB (:11400)                   │  │    │                               │ ││
│      │  │   70B models @ 56GB combined          │  │     │                                       │  │    │    Also: KV cache tier        │ ││
│      │  │                                       │  │     │   7B-14B models @ 32GB combined       │  │    │    Semantic cache             │ ││
│      │  └───────────────────────────────────────┘  │     └───────────────────────────────────────┘  │    └───────────────────────────────┘ ││
│      │                                              │                                                 │                                      ││
│      └──────────────────────────────────────────────┼─────────────────────────────────────────────────┼──────────────────────────────────────┘│
│                                                     │                                                 │                                        │
│                                                     └─────────────────────────────────────────────────┘                                        │
│                                                                     │                                                                            │
│                                                                     ▼                                                                            │
│      AUTOMATION LAYER                                   ┌─────────────────────────────────────────────────┐                                    │
│      ════════════════                                   │              AUTONOMOUS OPERATIONS              │                                    │
│                                                         │                                                 │                                    │
│      ┌──────────────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────────────────────────┐│
│      │                                                  │                                                 │                                    ││
│      │  ┌───────────────────┐  ┌───────────────────┐   │   ┌───────────────────┐  ┌───────────────────┐  │  ┌───────────────────┐            ││
│      │  │   n8n Workflows   │  │  Prometheus       │   │   │   Agent Crews     │  │   Home Assistant  │  │  │  Self-Improvement │            ││
│      │  │   (:5678)         │  │  Alerting         │   │   │   (CrewAI/        │  │   (:8123)         │  │  │  Loop             │            ││
│      │  │                   │  │                   │   │   │    LangGraph)     │  │                   │  │  │                   │            ││
│      │  │ • Health digest   │  │ • GPU temp        │   │   │                   │  │ • Presence        │  │  │ • Feedback capture│            ││
│      │  │ • Auto-recovery   │  │ • VRAM critical   │   │   │ • Research crew   │  │ • Lighting        │  │  │ • Preference learn│            ││
│      │  │ • Disk cleanup    │  │ • Service down    │   │   │ • Dev crew        │  │ • Climate         │  │  │ • Self-diagnosis  │            ││
│      │  │ • Model metrics   │  │ • Disk full       │   │   │ • Creative crew   │  │ • Scenes          │  │  │ • Prompt refine   │            ││
│      │  └───────────────────┘  └───────────────────┘   │   └───────────────────┘  └───────────────────┘  │  └───────────────────┘            ││
│      │                                                  │                                                 │                                    ││
│      └──────────────────────────────────────────────────┼─────────────────────────────────────────────────┼────────────────────────────────────┘│
│                                                         │                                                 │                                      │
│                                                         └─────────────────────────────────────────────────┘                                      │
│                                                                         │                                                                        │
│                                                                         ▼                                                                        │
│      DATA LAYER                                             ┌─────────────────────────────────────────────────┐                                │
│      ══════════                                             │                  TRUTH SOURCES                  │                                │
│                                                             │                                                 │                                │
│      ┌──────────────────────────────────────────────────────┼─────────────────────────────────────────────────┼──────────────────────────────────┐│
│      │                                                      │                                                 │                                  ││
│      │  ┌─────────────────┐  ┌─────────────────┐           │  ┌─────────────────┐  ┌─────────────────┐       │  ┌─────────────────┐            ││
│      │  │   Prometheus    │  │   PostgreSQL    │           │  │     Qdrant      │  │     Redis       │       │  │      Loki       │            ││
│      │  │   (:9090)       │  │   (:5432)       │           │  │    (:6333)      │  │    (:6379)      │       │  │    (:3100)      │            ││
│      │  │                 │  │                 │           │  │                 │  │                 │       │  │                 │            ││
│      │  │ Metrics truth   │  │ Relational      │           │  │ Vector search   │  │ Cache +         │       │  │ Log aggregation │            ││
│      │  │ 30-day history  │  │ 4 databases     │           │  │ RAG index       │  │ Pub/sub         │       │  │                 │            ││
│      │  └─────────────────┘  └─────────────────┘           │  └─────────────────┘  └─────────────────┘       │  └─────────────────┘            ││
│      │                                                      │                                                 │                                  ││
│      └──────────────────────────────────────────────────────┼─────────────────────────────────────────────────┼──────────────────────────────────┘│
│                                                             │                                                 │                                    │
│                                                             └─────────────────────────────────────────────────┘                                    │
│                                                                                                                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION STATUS

| Layer | Component | Status | Next Action |
|-------|-----------|--------|-------------|
| L0 | Prometheus | DEPLOYED | Add more custom metrics |
| L0 | Docker API | DEPLOYED | - |
| L0 | Hardware Discovery | DEPLOYED | Add network interface details |
| L0 | Activity API | DEPLOYED | Connect more sources |
| L0 | Letta Memory | DEPLOYED | Add more memory blocks |
| L1 | Hydra MCP | DEPLOYED | Add more endpoints |
| L1 | Hydra Tools | DEPLOYED | Complete self-improvement |
| L1 | LiteLLM | DEPLOYED | Update for LB endpoint |
| L1 | Alertmanager | DEPLOYED | - |
| L1 | Letta API | DEPLOYED | - |
| L1 | Ollama API | DEPLOYED | Deploy dual instance |
| L2 | Typhon Command | 85% | Complete StatusBar |
| L2 | Homepage | DEPLOYED | - |
| L2 | Grafana | DEPLOYED | Add inference dashboard |
| L2 | Uptime Kuma | DEPLOYED | Configure 40 monitors |
| L2 | Portainer | DEPLOYED | - |
| L3 | Open WebUI | DEPLOYED | - |
| L3 | Letta Chat | DEPLOYED | Enhance tools |
| L3 | SillyTavern | DEPLOYED | - |
| L3 | Claude Code MCP | DEPLOYED | - |
| L3 | Perplexica | DEPLOYED | - |
| L4 | n8n Workflows | 7 active | Create 13 more |
| L4 | Prometheus Alerts | DEPLOYED | - |
| L5 | Agent Crews | STUBBED | Implement fully |
| L5 | Shared Memory | DEPLOYED | Optimize collections |
| L6 | Voice Pipeline | NOT STARTED | Deploy wake word |
| L6 | Home Assistant | DEPLOYED | Add voice intents |
| L7 | Transparency | DEPLOYED | - |
| L7 | Governance | DEPLOYED | - |
| L8 | Self-Improvement | PARTIAL | Complete loops |

---

## USAGE SCENARIOS

### Scenario 1: Quick Status Check
```
User approaches Typhon Command dashboard
→ Glances at stats row (containers, CPU, RAM, GPU temp)
→ Sees node cards with status indicators
→ Notes any alerts in AlertsPanel
→ Total time: 5 seconds
```

### Scenario 2: Deep Dive Debugging
```
Alert fires for high GPU temperature
→ Typhon Command shows alert in AlertsPanel
→ Click node card → NodeDetailModal with GPU details
→ Open Grafana link for historical temperature graph
→ SSH to node via Claude Code to check nvidia-smi
→ Adjust power limit via bash command
→ Verify in Prometheus query
```

### Scenario 3: Hands-Free Control
```
"Hey Hydra, what's the status of the cluster?"
→ Wake word detected → STT processes
→ RouteLLM routes to 7B (simple query)
→ Steward agent queries MCP for status
→ Response synthesized
→ Kokoro TTS streams audio response
→ Total latency: ~600ms to first word
```

### Scenario 4: Creative Work Session
```
Open SillyTavern for Empire of Broken Queens
→ Select character card
→ Chat with 70B uncensored model
→ Request portrait → triggers ComfyUI workflow
→ Image returns to chat
→ Continue story with generated art
```

### Scenario 5: Autonomous Operation
```
3 AM: Disk space exceeds 90%
→ Prometheus alert fires
→ Alertmanager sends to n8n webhook
→ n8n workflow checks policy (FULL_AUTO mode)
→ Executes cleanup script via MCP
→ Logs action to Activity API
→ Morning: User sees success in Typhon Command audit log
```

---

*Hydra Unified Control Plane v4.0*
*December 14, 2025*
*Created with ULTRATHINK deep synthesis*
