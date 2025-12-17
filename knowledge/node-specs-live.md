# HYDRA CLUSTER - LIVE NODE SPECIFICATIONS
## Generated: December 16, 2025

---

## CLUSTER OVERVIEW

| Node | IP | Role | CPUs | RAM | GPUs | VRAM |
|------|----|----|------|-----|------|------|
| hydra-ai | 192.168.1.250 | Primary Inference | 24c/48t | 125GB | RTX 5090 + RTX 4090 | 56GB |
| hydra-compute | 192.168.1.203 | Secondary Inference + Images | 16c/32t | 60GB | 2x RTX 5070 Ti | 32GB |
| hydra-storage | 192.168.1.244 | Orchestration + Services | 56c/112t | 251GB | Arc A380 (transcode) | N/A |

**Combined Compute:**
- **CPU Cores:** 96 cores / 192 threads
- **RAM:** 436GB total
- **GPU VRAM:** 88GB AI compute
- **Storage:** 164TB (NFS shared)

---

## NODE 1: HYDRA-AI (Primary Inference)

### Hardware
```
Host: hydra-ai
OS: NixOS 24.11 (kernel 6.12.60)
CPU: AMD Ryzen Threadripper 7960X (24c/48t, boost 5.3GHz)
RAM: 125GB DDR5 (117GB available)
Storage: 916GB NVMe (84GB used, 786GB free)
```

### GPUs (Live Status)
| GPU | VRAM Total | VRAM Free | Temp | Power |
|-----|------------|-----------|------|-------|
| RTX 5090 | 32607 MB | 2320 MB | 36°C | 22W |
| RTX 4090 | 24564 MB | 3833 MB | 29°C | 4W |

**Note:** ~50GB VRAM in use = Midnight-Miqu-70B loaded

### Services Running
| Service | Type | Port | Status |
|---------|------|------|--------|
| TabbyAPI | systemd | 5000 | Active |
| Node Exporter | systemd | 9100 | Active |
| NVIDIA Exporter | systemd | 9835 | Active |

### Key Capabilities
- **Primary 70B+ inference** via ExLlamaV2 tensor parallel
- **50+ tok/s** on Midnight-Miqu-70B-v1.5
- **Speculative decoding** available (n-gram)
- **Power headroom:** 1400W UPS capacity

### Access
```bash
ssh typhon@192.168.1.250
# Tailscale: 100.84.120.44
```

---

## NODE 2: HYDRA-COMPUTE (Secondary Inference + Images)

### Hardware
```
Host: hydra-compute
OS: NixOS 24.11 (kernel 6.12.60)
CPU: AMD Ryzen 9 9950X (16c/32t, boost 5.7GHz)
RAM: 60GB DDR5 (53GB available)
Storage: 916GB NVMe (177GB used, 692GB free)
```

### GPUs (Live Status)
| GPU | VRAM Total | VRAM Free | Temp | Power |
|-----|------------|-----------|------|-------|
| RTX 5070 Ti #1 | 16303 MB | 6721 MB | 50°C | 19W |
| RTX 5070 Ti #2 | 16303 MB | 15122 MB | 47°C | 14W |

**Note:** GPU #1 running TabbyAPI (Qwen), GPU #2 available for ComfyUI

### Services Running
| Service | Type | Port | Status |
|---------|------|------|--------|
| Ollama | systemd | 11434 | Active |
| TabbyAPI | Docker | 5000 | Active |
| ComfyUI | Docker | 8188 | Active |
| Whisper ASR | Docker | 9002 | Active |
| Kohya Training | Docker | - | Available |
| Node Exporter | Docker | 9100 | Active |

### Container List
```
comfyui-cu128
tabbyapi
kohya-training
whisper-asr
node-exporter
```

### Key Capabilities
- **Ollama** for fast 7B models (qwen2.5, llama3.2, deepseek-r1)
- **Embedding generation** via nomic-embed-text (768 dims)
- **Image generation** via ComfyUI (SDXL, Flux)
- **Speech-to-text** via Whisper ASR
- **Model training** via Kohya

### Access
```bash
ssh typhon@192.168.1.203
# Tailscale: 100.74.73.44
```

---

## NODE 3: HYDRA-STORAGE (Orchestration Hub)

### Hardware
```
Host: Unraid
OS: Unraid 7.2 (kernel 6.12.54)
CPU: AMD EPYC 7663 (56c/112t, boost 3.5GHz)
     256MB L3 cache - ideal for parallel agents
RAM: 251GB DDR4 ECC (187GB available, 63GB in use)
Storage: 164TB array (148TB used, 17TB free = 90%)
```

### GPU (Transcoding Only)
- **Intel Arc A380** - Dedicated to Plex via Quick Sync Video
- Handles all media transcoding, freeing CPU for orchestration

### Containers Running: 63 Total

#### Core Hydra Services
| Container | Port | Function |
|-----------|------|----------|
| hydra-tools-api | 8700 | Main Hydra API (Phase 11 tools) |
| hydra-mcp | 8600 | MCP control API |
| hydra-crewai | - | Agent crews (monitoring, research, maintenance) |
| hydra-letta | 8283 | Stateful agent memory |
| hydra-litellm | 4000 | Unified model routing |
| hydra-n8n | 5678 | Workflow automation |
| hydra-prometheus | 9090 | Metrics collection |
| hydra-grafana | 3003 | Dashboards |
| hydra-alertmanager | 9093 | Alert routing |

#### Databases
| Container | Port | Function |
|-----------|------|----------|
| hydra-postgres | 5432 | Primary PostgreSQL |
| letta-db | 5433 | Letta pgvector DB |
| hydra-qdrant | 6333 | Vector database |
| hydra-neo4j | 7474/7687 | Knowledge graph |
| hydra-redis | 6379 | Cache/queue |
| hydra-meilisearch | 7700 | Full-text search |

#### AI Services
| Container | Port | Function |
|-----------|------|----------|
| kokoro-tts | 8880 | Voice synthesis (67 voices) |
| open-webui | 3001 | Chat interface |
| hydra-searxng | 8080 | Web search |
| hydra-firecrawl-api | 3005 | Web scraping |
| hydra-docling | 5001 | Document parsing |
| perplexica | 3030 | Research assistant |

#### Home Automation
| Container | Port | Function |
|-----------|------|----------|
| homeassistant | 8123 | Home automation hub |
| adguard | 53 | DNS filtering |

#### Media (Managed by Arc A380)
| Container | Port | Function |
|-----------|------|----------|
| Plex-Media-Server | 32400 | Media streaming |
| stash | 9999 | Media organizer |
| sonarr/radarr/etc | various | Media automation |

### Key Capabilities
- **56 cores available** for agent orchestration
- **180GB+ RAM** available for KV caching / semantic caching
- **Central orchestration** for all Hydra services
- **NFS server** for model storage to AI nodes

### Access
```bash
ssh claude@192.168.1.244  # Claude user
ssh root@192.168.1.244    # Root access
# Tailscale: 100.111.54.59
```

---

## NETWORK TOPOLOGY

```
                    ┌─────────────────────────────────────┐
                    │        10GbE Backbone               │
                    │   (USW-Pro-XG-10-PoE, MTU 9000)    │
                    └─────────────────────────────────────┘
                              │         │         │
                    ┌─────────┴─────────┴─────────┴─────────┐
                    │                                       │
         ┌──────────▼──────────┐             ┌──────────────▼──────────────┐
         │     hydra-ai        │             │      hydra-compute          │
         │   192.168.1.250     │             │      192.168.1.203          │
         │  ─────────────────  │             │  ──────────────────────     │
         │  TabbyAPI :5000     │             │  Ollama :11434              │
         │  70B inference      │             │  ComfyUI :8188              │
         │  RTX 5090 + 4090    │             │  Whisper :9002              │
         └─────────────────────┘             │  2x RTX 5070 Ti             │
                    │                        └─────────────────────────────┘
                    │                                       │
                    │         ┌─────────────────────┐       │
                    └─────────▶│   hydra-storage    │◀──────┘
                              │   192.168.1.244    │
                              │  ──────────────────│
                              │  63 containers     │
                              │  Hydra Tools API   │
                              │  164TB NFS storage │
                              │  EPYC 7663 (56c)   │
                              └─────────────────────┘
                                       │
                              ┌────────▼────────┐
                              │   NFS Exports   │
                              │  /mnt/models    │
                              │  /mnt/hydra_shared │
                              └─────────────────┘
```

---

## API ENDPOINTS SUMMARY

### Primary API: hydra-tools-api (192.168.1.244:8700)

| Router | Endpoints | Function |
|--------|-----------|----------|
| `/memory` | 15+ | MIRIX memory system (Qdrant + Neo4j) |
| `/sandbox` | 5 | Code execution sandbox |
| `/constitution` | 5 | Safety enforcement |
| `/self-improvement` | 5 | Benchmark + propose |
| `/voice` | 7 | STT/TTS/Voice chat |
| `/search` | 6 | Hybrid search |
| `/crews` | 15+ | CrewAI orchestration |
| `/health` | 10 | Cluster health |
| `/reconcile` | 6 | State management |
| `/benchmark` | 5 | Capability testing |

### Inference APIs
| Service | URL | Auth |
|---------|-----|------|
| TabbyAPI (70B) | http://192.168.1.250:5000 | None |
| Ollama (7B) | http://192.168.1.203:11434 | None |
| LiteLLM (unified) | http://192.168.1.244:4000 | Bearer sk-PyKRr5... |

### Database APIs
| Service | URL | Auth |
|---------|-----|------|
| Qdrant | http://192.168.1.244:6333 | None |
| Neo4j | http://192.168.1.244:7474 | neo4j/HydraNeo4jPass2024 |
| PostgreSQL | localhost:5432 | hydra/g9cUyFK6... |

---

## AUTONOMOUS CAPABILITIES CHECKLIST

### Implemented
- [x] 6-tier MIRIX memory architecture
- [x] Qdrant vector storage with semantic search
- [x] Neo4j graph relationships with multi-hop traversal
- [x] Constitutional safety enforcement
- [x] Sandboxed code execution
- [x] Self-improvement workflow (benchmark + analyze)
- [x] Voice pipeline (STT → LLM → TTS)
- [x] MCP proxy (30 tools)
- [x] CrewAI orchestration (3 crews)
- [x] n8n workflow automation (18 workflows)
- [x] Discord notifications
- [x] Prometheus/Grafana monitoring

### Remaining
- [ ] Agent scheduling (AIOS-style priority queues)
- [ ] Wake word detection (OpenWakeWord)
- [ ] Home Assistant presence integration
- [ ] Native MCP servers (git, postgres, docker)

---

*Document Version: 1.0*
*Generated: December 16, 2025*
*Status: Live Specs*
