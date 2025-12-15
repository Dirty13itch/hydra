# HYDRA ARCHITECTURE

> *Technical blueprint for the autonomous AI operating system*

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                         INTERACTION LAYER                                    │
│                                                                              │
│    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                │
│    │ Claude Code  │    │  Open WebUI  │    │ Hydra Control│                │
│    │  (Primary)   │    │ (Chat UI)    │    │  Plane (TBD) │                │
│    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                │
│           │                   │                   │                         │
│           └───────────────────┴───────────────────┘                         │
│                               │                                              │
│                               ▼                                              │
│                    ┌─────────────────────┐                                  │
│                    │      LiteLLM        │ Unified API Gateway              │
│                    │   (Router/Proxy)    │ Port 4000                        │
│                    └──────────┬──────────┘                                  │
│                               │                                              │
└───────────────────────────────┼──────────────────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────────────────┐
│                               │                                              │
│                         INTELLIGENCE LAYER                                   │
│                                                                              │
│    ┌──────────────────────────┼──────────────────────────┐                  │
│    │                          ▼                          │                  │
│    │         ┌────────────────────────────────┐          │                  │
│    │         │           INFERENCE            │          │                  │
│    │         ├────────────────────────────────┤          │                  │
│    │         │                                │          │                  │
│    │         │  hydra-ai:5000 (TabbyAPI)      │          │                  │
│    │         │  └─ 70B models, tensor parallel│          │                  │
│    │         │  └─ RTX 5090 + RTX 4090        │          │                  │
│    │         │                                │          │                  │
│    │         │  hydra-ai:11434 (Ollama)       │          │                  │
│    │         │  └─ Backup, specialized models │          │                  │
│    │         │                                │          │                  │
│    │         │  hydra-compute:11434 (Ollama)  │          │                  │
│    │         │  └─ Draft models, embeddings   │          │                  │
│    │         │  └─ RTX 5070Ti + RTX 3060      │          │                  │
│    │         │                                │          │                  │
│    │         └────────────────────────────────┘          │                  │
│    │                          │                          │                  │
│    │         ┌────────────────┴────────────────┐         │                  │
│    │         ▼                                 ▼         │                  │
│    │  ┌─────────────┐                  ┌─────────────┐   │                  │
│    │  │   Letta     │                  │   CrewAI    │   │                  │
│    │  │  (Memory)   │◄────────────────►│  (Agents)   │   │                  │
│    │  └─────────────┘                  └─────────────┘   │                  │
│    │         │                                 │         │                  │
│    └─────────┼─────────────────────────────────┼─────────┘                  │
│              │                                 │                            │
└──────────────┼─────────────────────────────────┼────────────────────────────┘
               │                                 │
┌──────────────┼─────────────────────────────────┼────────────────────────────┐
│              │                                 │                            │
│              │      ORCHESTRATION LAYER        │                            │
│              │                                 │                            │
│              ▼                                 ▼                            │
│    ┌─────────────────────────────────────────────────────┐                 │
│    │                       n8n                            │                 │
│    │              (Workflow Automation)                   │                 │
│    │                                                      │                 │
│    │  • Self-healing workflows                           │                 │
│    │  • Overnight research pipelines                     │                 │
│    │  • Creative content automation                      │                 │
│    │  • Media acquisition triggers                       │                 │
│    │  • Notification routing                             │                 │
│    │                                                      │                 │
│    └─────────────────────────────────────────────────────┘                 │
│                               │                                             │
└───────────────────────────────┼─────────────────────────────────────────────┘
                                │
┌───────────────────────────────┼─────────────────────────────────────────────┐
│                               │                                             │
│                         DATA LAYER                                          │
│                               │                                             │
│    ┌──────────────────────────┼──────────────────────────┐                 │
│    │                          ▼                          │                 │
│    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│    │  │PostgreSQL│  │  Qdrant  │  │  Redis   │  │  Neo4j   │             │
│    │  │  :5432   │  │  :6333   │  │  :6379   │  │  :7687   │             │
│    │  │          │  │          │  │          │  │          │             │
│    │  │ • State  │  │ • Vectors│  │ • Cache  │  │ • Graph  │             │
│    │  │ • Letta  │  │ • Memory │  │ • Sessions│ │ • Entities│            │
│    │  │ • n8n    │  │ • RAG    │  │ • Locks  │  │ • Relations│           │
│    │  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │
│    │                                                      │                │
│    └──────────────────────────────────────────────────────┘                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                         OBSERVABILITY LAYER                                  │
│                                                                              │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│    │Prometheus│  │ Grafana  │  │   Loki   │  │  Uptime  │  │  Alert   │   │
│    │  :9090   │  │  :3003   │  │  :3100   │  │   Kuma   │  │ Manager  │   │
│    │          │  │          │  │          │  │  :3001   │  │  :9093   │   │
│    │ • Metrics│  │ • Graphs │  │ • Logs   │  │ • Pings  │  │ • Routes │   │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Node Responsibilities

### hydra-ai (192.168.1.250) - INFERENCE PLANE

**Hardware:**
- CPU: AMD Threadripper 7960X (24C/48T)
- RAM: 128GB DDR5
- GPU: RTX 5090 (32GB) + RTX 4090 (24GB) = 56GB VRAM
- OS: NixOS 24.11

**Primary Role:** Large model inference with tensor parallelism

**Services:**
| Service | Port | Purpose |
|---------|------|---------|
| TabbyAPI | 5000 | Primary inference (ExLlamaV2, 70B models) |
| Ollama | 11434 | Backup inference |

**Configuration Approach:** NixOS flake, declarative services

**Key Files:**
- `/etc/nixos/configuration.nix` - Main system config
- `/etc/nixos/services/tabbyapi.nix` - TabbyAPI service
- `/etc/nixos/services/ollama.nix` - Ollama service

**Why NixOS:** Atomic rollbacks, reproducible builds, declarative configuration that Claude Code can safely modify.

---

### hydra-compute (192.168.1.203) - CREATIVE PLANE

**Hardware:**
- CPU: AMD Ryzen 9 9950X (16C/32T)
- RAM: 64GB DDR5
- GPU: RTX 5070 Ti (16GB) + RTX 3060 (12GB) = 28GB VRAM
- OS: NixOS 24.11

**Primary Role:** Image generation, audio processing, secondary inference

**Services:**
| Service | Port | Purpose |
|---------|------|---------|
| ComfyUI | 8188 | Image generation workflows |
| Ollama | 11434 | Draft models (8B), embeddings |
| Kokoro TTS | 8080 | Text-to-speech synthesis |
| Whisper ASR | 9000 | Speech-to-text transcription |

**Configuration Approach:** NixOS flake, shared modules with hydra-ai

**GPU Allocation:**
- RTX 5070 Ti: ComfyUI (primary), large image models
- RTX 3060: Ollama (embeddings, draft models), Whisper

---

### hydra-storage (192.168.1.244) - CONTROL PLANE

**Hardware:**
- CPU: AMD EPYC 7663 (56C/112T)
- RAM: 256GB DDR4 ECC
- GPU: Intel Arc A380 (basic transcoding only)
- Storage: ~180TB array (parity protected)
- OS: Unraid 7.0

**Primary Role:** Orchestration, state, storage, media, always-on services

**Services:**
| Category | Services | Ports |
|----------|----------|-------|
| API Gateway | LiteLLM | 4000 |
| Databases | PostgreSQL, Qdrant, Redis, Neo4j | 5432, 6333, 6379, 7687 |
| Memory | Letta | 8283 |
| Orchestration | n8n | 5678 |
| Observability | Prometheus, Grafana, Loki, Uptime Kuma, Alertmanager | 9090, 3003, 3100, 3004, 9093 |
| Media | Plex, *arr stack, Stash | 32400, various |
| Web | SearXNG, Firecrawl | 8888, 3002 |
| Management | Portainer, Homepage | 9000, 80 |

**Configuration Approach:** Docker Compose files, Unraid Community Apps

**Why Unraid (not NixOS):**
- Best-in-class storage management (parity, cache pools)
- Mature Docker ecosystem
- Web UI for manual intervention when needed
- 256GB RAM ideal for caching and databases

**Storage Layout:**
```
/mnt/user/
├── models/              # AI models (NFS shared)
│   ├── exl2/           # ExLlamaV2 quantized models
│   ├── gguf/           # Ollama/llama.cpp models
│   ├── diffusion/      # Stable Diffusion models
│   └── loras/          # LoRA adapters
│
├── hydra_shared/        # Shared workspace (NFS shared)
│   ├── datasets/       # Training data, RAG corpora
│   ├── outputs/        # Generated content
│   └── scratch/        # Temporary processing
│
├── appdata/             # Docker container data
│   ├── postgresql/
│   ├── qdrant/
│   ├── letta/
│   ├── n8n/
│   ├── prometheus/
│   ├── grafana/
│   └── ...
│
├── media/               # Media library
│   ├── movies/
│   ├── tv/
│   ├── music/
│   └── ...
│
└── backups/             # System backups
    ├── nixos-configs/
    ├── docker-volumes/
    └── databases/
```

---

### hydra-dev (VM on hydra-storage) - DEVELOPMENT

**Resources:**
- vCPU: 16
- RAM: 64GB
- Storage: 500GB qcow2
- OS: Ubuntu/NixOS (flexible)

**Primary Role:** Development, testing, CI/CD runners

**Use Cases:**
- Test NixOS changes before deploying to production nodes
- Run CI/CD pipelines
- Development environment for Hydra Control Plane UI
- Isolated testing of new services

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        NETWORK TOPOLOGY                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ┌─────────────────┐                          │
│                    │    UDM Pro      │                          │
│                    │  192.168.1.1    │                          │
│                    │    (Gateway)    │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│              ┌──────────────┼──────────────┐                    │
│              │              │              │                    │
│              ▼              ▼              ▼                    │
│     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│     │  hydra-ai    │ │hydra-compute │ │hydra-storage │         │
│     │    .250      │ │    .203      │ │    .244      │         │
│     │              │ │              │ │              │         │
│     │ 10GbE: eno1  │ │10GbE:enp1s0f0│ │10GbE: bond0  │         │
│     │  (Aquantia)  │ │ (Intel X540) │ │(2x Intel X550)│        │
│     └──────────────┘ └──────────────┘ └──────────────┘         │
│              │              │              │                    │
│              └──────────────┴──────────────┘                    │
│                             │                                    │
│                    ┌────────┴────────┐                          │
│                    │   10GbE Switch  │                          │
│                    │ USW-Pro-XG-10   │                          │
│                    │                 │                          │
│                    │ Validated:      │                          │
│                    │ 9.4 Gbps link   │                          │
│                    │ 1.1 GB/s NFS    │                          │
│                    └─────────────────┘                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Critical Network Dependencies:**
- 10GbE backbone enables fast model loading (30s vs 5+ min on 1GbE)
- NFS mounts require hydra-storage to be available
- All inter-node API calls traverse this backbone

**NFS Mounts (on NixOS nodes):**
```nix
fileSystems."/mnt/models" = {
  device = "192.168.1.244:/mnt/user/models";
  fsType = "nfs";
  options = [ "nfsvers=4.2" "rsize=1048576" "wsize=1048576" "hard" "intr" ];
};

fileSystems."/mnt/shared" = {
  device = "192.168.1.244:/mnt/user/hydra_shared";
  fsType = "nfs";
  options = [ "nfsvers=4.2" "rsize=1048576" "wsize=1048576" "hard" "intr" ];
};
```

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MEMORY SYSTEM                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      LETTA (MemGPT)                              │   │
│  │                    hydra-storage:8283                            │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                  │   │
│  │  CORE MEMORY (Always in LLM context window - ~8KB)              │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ persona:                                                    │ │   │
│  │  │   "I am Hydra, an autonomous AI operating system..."       │ │   │
│  │  │                                                            │ │   │
│  │  │ human:                                                      │ │   │
│  │  │   "Shaun, Minneapolis area. Prefers autonomous operation,  │ │   │
│  │  │    minimal hand-holding. Working on Empire of Broken       │ │   │
│  │  │    Queens visual novel. Values bleeding-edge tech..."      │ │   │
│  │  │                                                            │ │   │
│  │  │ system_state:                                               │ │   │
│  │  │   "TabbyAPI: healthy (Llama-3.1-70B loaded)                │ │   │
│  │  │    ComfyUI: healthy                                        │ │   │
│  │  │    Last issue: [resolved] TabbyAPI CUDA mismatch..."       │ │   │
│  │  │                                                            │ │   │
│  │  │ active_projects:                                            │ │   │
│  │  │   "1. Empire of Broken Queens - Wave 1 prototype           │ │   │
│  │  │    2. Hydra Control Plane UI - design phase                │ │   │
│  │  │    3. Overnight research pipeline - pending setup..."      │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  ARCHIVAL MEMORY (Qdrant vector store - unlimited)              │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ • All conversation history (chunked, embedded)             │ │   │
│  │  │ • Project documentation and decisions                      │ │   │
│  │  │ • Research findings and summaries                          │ │   │
│  │  │ • Error resolutions and troubleshooting steps              │ │   │
│  │  │ • User preferences (inferred from interactions)            │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  │  RECALL MEMORY (PostgreSQL - conversation search)               │   │
│  │  ┌────────────────────────────────────────────────────────────┐ │   │
│  │  │ • Recent conversations (searchable)                        │ │   │
│  │  │ • Message timestamps and metadata                          │ │   │
│  │  │ • Session boundaries                                       │ │   │
│  │  └────────────────────────────────────────────────────────────┘ │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    KNOWLEDGE GRAPH (Neo4j)                       │   │
│  │                    hydra-storage:7687                            │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                  │   │
│  │  Entities:                                                       │   │
│  │  • (Shaun:Person {role: "owner"})                               │   │
│  │  • (Hydra:System {version: "0.1"})                              │   │
│  │  • (EmpireOfBrokenQueens:Project {status: "active"})            │   │
│  │  • (TabbyAPI:Service {node: "hydra-ai", port: 5000})            │   │
│  │  • (Llama70B:Model {format: "EXL2", bpw: 3.5})                  │   │
│  │                                                                  │   │
│  │  Relationships:                                                  │   │
│  │  • (Shaun)-[:OWNS]->(Hydra)                                     │   │
│  │  • (Shaun)-[:WORKS_ON]->(EmpireOfBrokenQueens)                  │   │
│  │  • (TabbyAPI)-[:RUNS_ON]->(hydra-ai)                            │   │
│  │  • (TabbyAPI)-[:SERVES]->(Llama70B)                             │   │
│  │  • (EmpireOfBrokenQueens)-[:REQUIRES]->(ComfyUI)                │   │
│  │                                                                  │   │
│  │  Temporal:                                                       │   │
│  │  • Relationships have valid_from/valid_to timestamps            │   │
│  │  • Enables "what was the state at time X?" queries              │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Inference Routing

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LiteLLM ROUTING                                   │
│                    hydra-storage:4000                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Incoming Request                                                        │
│       │                                                                  │
│       ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ROUTING LOGIC                                 │   │
│  │                                                                  │   │
│  │  1. Check requested model explicitly                            │   │
│  │     └─ If specified, route directly                             │   │
│  │                                                                  │   │
│  │  2. Analyze query complexity (future: RouteLLM)                 │   │
│  │     └─ Simple queries → fast small model                        │   │
│  │     └─ Complex queries → large model                            │   │
│  │                                                                  │   │
│  │  3. Check model availability                                    │   │
│  │     └─ If primary down, failover to backup                      │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                  │
│       ├─────────────────────┬─────────────────────┐                     │
│       ▼                     ▼                     ▼                     │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐             │
│  │  TabbyAPI   │      │   Ollama    │      │   Ollama    │             │
│  │  hydra-ai   │      │  hydra-ai   │      │hydra-compute│             │
│  │   :5000     │      │   :11434    │      │   :11434    │             │
│  │             │      │             │      │             │             │
│  │ • 70B models│      │ • 8B-32B   │      │ • 8B models │             │
│  │ • 30-45 t/s │      │ • Backup   │      │ • Embeddings│             │
│  │ • Highest Q │      │ • 100+ t/s │      │ • 200+ t/s  │             │
│  └─────────────┘      └─────────────┘      └─────────────┘             │
│                                                                          │
│  MODEL INVENTORY:                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ TabbyAPI (hydra-ai):                                            │   │
│  │   • Llama-3.1-70B-EXL2-3.5bpw (primary)                        │   │
│  │   • Qwen2.5-72B-EXL2-4.0bpw (alternate)                        │   │
│  │   • DeepSeek-V3-70B-EXL2 (reasoning)                           │   │
│  │   • Lumimaid-70B-EXL2 (creative/NSFW)                          │   │
│  │                                                                  │   │
│  │ Ollama (hydra-ai):                                              │   │
│  │   • llama3.2:8b (fast responses)                               │   │
│  │   • qwen2.5:32b (medium complexity)                            │   │
│  │   • deepseek-r1:8b (reasoning)                                 │   │
│  │                                                                  │   │
│  │ Ollama (hydra-compute):                                         │   │
│  │   • llama3.2:3b (draft model for speculative decoding)         │   │
│  │   • nomic-embed-text (embeddings)                              │   │
│  │   • all-minilm (fast embeddings)                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Creative Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CREATIVE PIPELINE                                   │
│              (Empire of Broken Queens Production)                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  INPUT                                                                   │
│    │                                                                     │
│    │  Script/Chapter Document                                           │
│    │  (markdown with character tags, scenes, dialogue)                  │
│    │                                                                     │
│    ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    n8n ORCHESTRATION                             │   │
│  │                    hydra-storage:5678                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│    │                                                                     │
│    ├──────────────────────┬──────────────────────┐                      │
│    │                      │                      │                      │
│    ▼                      ▼                      ▼                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   DIALOGUE   │  │    IMAGE     │  │    VOICE     │                  │
│  │  GENERATION  │  │  GENERATION  │  │   SYNTHESIS  │                  │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤                  │
│  │              │  │              │  │              │                  │
│  │ LiteLLM →    │  │ ComfyUI API  │  │ Kokoro TTS   │                  │
│  │ TabbyAPI     │  │ hydra-compute│  │ hydra-compute│                  │
│  │              │  │ :8188        │  │ :8080        │                  │
│  │ • Character  │  │              │  │              │                  │
│  │   voice/style│  │ • InstantID  │  │ • Character  │                  │
│  │ • Procedural │  │   (face)     │  │   voices     │                  │
│  │   dialogue   │  │ • IP-Adapter │  │ • Emotion    │                  │
│  │ • Scene      │  │   (style)    │  │   control    │                  │
│  │   adaptation │  │ • LoRAs      │  │              │                  │
│  │              │  │   (characters│  │              │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│    │                      │                      │                      │
│    └──────────────────────┴──────────────────────┘                      │
│                           │                                              │
│                           ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ASSET ASSEMBLY                                │   │
│  │                                                                  │   │
│  │  /mnt/shared/projects/empire-of-broken-queens/                  │   │
│  │  └── chapters/                                                   │   │
│  │      └── chapter-03/                                            │   │
│  │          ├── script.md                                          │   │
│  │          ├── images/                                            │   │
│  │          │   ├── scene_01_queen_aria.png                       │   │
│  │          │   └── scene_02_throne_room.png                      │   │
│  │          ├── audio/                                             │   │
│  │          │   ├── dialogue_001.wav                              │   │
│  │          │   └── dialogue_002.wav                              │   │
│  │          └── metadata.json                                      │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                           │                                              │
│                           ▼                                              │
│                    NOTIFICATION                                          │
│              "Chapter 3 assets ready"                                    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Self-Healing Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SELF-HEALING SYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  DETECTION                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                  │   │
│  │  Prometheus (metrics)          Uptime Kuma (endpoints)          │   │
│  │  • CPU/RAM/GPU utilization     • HTTP health checks             │   │
│  │  • Container status            • TCP port checks                │   │
│  │  • Custom service metrics      • Response time                  │   │
│  │                                                                  │   │
│  │  Loki (logs)                   Netdata (anomaly detection)      │   │
│  │  • Error pattern matching      • ML-based anomaly detection     │   │
│  │  • Log rate changes            • Predictive alerts              │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                           │                                              │
│                           ▼                                              │
│  ALERTING                                                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AlertManager                                  │   │
│  │                                                                  │   │
│  │  Routes:                                                         │   │
│  │  • Critical → n8n webhook (immediate remediation)               │   │
│  │  • Warning → n8n webhook (queued remediation)                   │   │
│  │  • Info → Loki only (logged)                                    │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                           │                                              │
│                           ▼                                              │
│  REMEDIATION                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    n8n Workflow                                  │   │
│  │                                                                  │   │
│  │  1. Receive alert webhook                                       │   │
│  │  2. Parse alert (which service, which node)                     │   │
│  │  3. Check remediation history (avoid loops)                     │   │
│  │  4. Execute remediation:                                        │   │
│  │                                                                  │   │
│  │     NixOS services (hydra-ai, hydra-compute):                   │   │
│  │     ┌────────────────────────────────────────────────────────┐  │   │
│  │     │ ssh shaun@{node} "sudo systemctl restart {service}"   │  │   │
│  │     │                                                        │  │   │
│  │     │ If still failing after 2 attempts:                     │  │   │
│  │     │ ssh shaun@{node} "sudo nixos-rebuild switch --rollback"│  │   │
│  │     └────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │     Docker services (hydra-storage):                            │   │
│  │     ┌────────────────────────────────────────────────────────┐  │   │
│  │     │ ssh root@hydra-storage "docker restart {container}"   │  │   │
│  │     │                                                        │  │   │
│  │     │ If still failing:                                      │  │   │
│  │     │ ssh root@hydra-storage "docker-compose -f {file} up -d"│  │   │
│  │     └────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │  5. Verify health (check endpoint again)                        │   │
│  │  6. Log outcome to Letta archival memory                        │   │
│  │  7. If unresolved: Alert Shaun via Discord                      │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  GUARDRAILS:                                                             │
│  • Rate limit: Max 3 remediation attempts per service per hour          │
│  • Blast radius: Only restart affected service, not entire node         │
│  • Rollback: NixOS changes can be reverted atomically                   │
│  • Escalation: Human notified after automated attempts fail             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Security Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SECURITY MODEL                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  NETWORK SECURITY:                                                       │
│  • All services on private 192.168.1.0/24 network                       │
│  • No services exposed to internet (except via VPN)                     │
│  • 10GbE backbone is isolated cluster traffic                           │
│  • Gluetun VPN gateway for *arr stack traffic                          │
│                                                                          │
│  ACCESS CONTROL:                                                         │
│  • SSH key-only authentication (no passwords)                           │
│  • sudo without password for shaun (convenience, single user)           │
│  • Docker socket access for management                                  │
│                                                                          │
│  DATA PROTECTION:                                                        │
│  • Parity protection on hydra-storage array                            │
│  • Regular backups of:                                                  │
│    - PostgreSQL databases                                               │
│    - NixOS configurations                                               │
│    - Docker volumes                                                     │
│    - Letta memory state                                                 │
│                                                                          │
│  ISOLATION:                                                              │
│  • Each service runs in its own container/systemd unit                 │
│  • GPU access controlled via device passthrough                        │
│  • NFS mounts are read-only where possible                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Port Reference

### hydra-ai (192.168.1.250)
| Port | Service | Protocol |
|------|---------|----------|
| 22 | SSH | TCP |
| 4000 | LiteLLM | HTTP |
| 5000 | TabbyAPI | HTTP |
| 11434 | Ollama | HTTP |

### hydra-compute (192.168.1.203)
| Port | Service | Protocol |
|------|---------|----------|
| 22 | SSH | TCP |
| 8080 | Kokoro TTS | HTTP |
| 8188 | ComfyUI | HTTP |
| 9000 | Whisper ASR | HTTP |
| 11434 | Ollama | HTTP |

### hydra-storage (192.168.1.244)
| Port | Service | Protocol |
|------|---------|----------|
| 22 | SSH | TCP |
| 80 | Homepage | HTTP |
| 3000 | Open WebUI | HTTP |
| 3001 | Uptime Kuma | HTTP |
| 3003 | Grafana | HTTP |
| 3100 | Loki | HTTP |
| 5432 | PostgreSQL | TCP |
| 5678 | n8n | HTTP |
| 6333 | Qdrant | HTTP |
| 6379 | Redis | TCP |
| 7687 | Neo4j Bolt | TCP |
| 7474 | Neo4j HTTP | HTTP |
| 8283 | Letta | HTTP |
| 9090 | Prometheus | HTTP |
| 9093 | AlertManager | HTTP |
| 32400 | Plex | HTTP |

---

*This document is the technical reference. For the "why", see VISION.md.*
*For implementation plan, see ROADMAP.md.*
*Last updated: December 2025*
