# HYDRA CLUSTER - MASTER SYNTHESIS & CLAUDE CODE AUTONOMOUS EXECUTION STRATEGY

**Created:** December 8, 2025  
**Purpose:** Comprehensive gap analysis, canonical master plan, and Claude Code optimization strategy

---

## PART 1: GAP ANALYSIS - What's Missing from Current Documents

### 1.1 Items Found in Conversations but NOT in Current Artifacts

| Category | Missing Items | Source |
|----------|---------------|--------|
| **MCP Integration** | Full 8-server Claude Desktop config (SSH, Unraid, Docker, Filesystem, Windows CLI, Grafana, Notifications) | chat/38f48bc3 |
| **Home Automation** | Complete device inventory (Nest, Lutron, Bond, Roborock, Sonos, TVs, BirdBuddy), protocol analysis, integration priorities | chat/f34ac81b |
| **UPS Power Constraints** | 2000W total capacity vs ~2700W potential load, GPU power limiting strategies (50-60% for safety), redistribution plans | chat/3527f372 |
| **NixOS Flake Structure** | Complete flake.nix with Colmena for multi-node deployment, shared modules, agenix for secrets | chat/3527f372 |
| **Knowledge Files Missing** | nixos-modules.md, observability.md, rag-pipeline.md, automation.md, home-automation.md (referenced in CLAUDE.md but not created) | outputs/hydra-claude-code |
| **Voice Pipeline Details** | Kokoro TTS (82M params, 210x realtime, Apache 2.0), Piper TTS, faster-whisper STT, Silero VAD | chat/77761b45 |
| **Bleeding Edge Specifics** | AIOS v0.2.2 commands, Darwin-Gödel Machine sandbox setup, OpenHands SDK integration, MergeKit workflow | chat/77761b45 |
| **Security Considerations** | SSH key strategy, Tailscale mesh VPN config, AdGuard NSFW blocklists, no Zigbee/Z-Wave | chat/f34ac81b |

### 1.2 Items in Artifacts but Incomplete

| Document | What's Incomplete |
|----------|-------------------|
| **HYDRA-MASTER-DOCUMENT.md** | Missing NixOS flake details, no MCP config, simplified home automation |
| **hydra-unraid-docker-map.md** | Has containers but missing detailed configs for VPN routing, GPU passthrough for Arc A380 |
| **CLAUDE.md** | References knowledge files that don't exist, missing PRP templates |
| **knowledge/infrastructure.md** | Good but missing IPMI details (hydra-storage at 192.168.1.216) |
| **knowledge/models.md** | Has models but missing download commands, HuggingFace URLs |

### 1.3 Current State Reality Check

**What IS Actually Complete:**
- ✅ 10GbE network backbone (validated 9.4 Gbps, 1.1 GB/s NFS)
- ✅ hydra-ai hardware with NixOS + NVIDIA drivers
- ✅ hydra-compute hardware with NixOS + NVIDIA drivers  
- ✅ hydra-storage (Unraid) operational
- ✅ TabbyAPI running on hydra-ai:5000 (as systemd service)
- ✅ Open WebUI running on hydra-ai:3000
- ✅ Plex running on hydra-storage:32400
- ✅ Stash running on hydra-storage:9999
- ✅ NFS mounts working for model storage

**What is NOT Complete:**
- ❌ Databases (PostgreSQL, Qdrant, Redis) - CRITICAL BLOCKER
- ❌ Observability stack (Prometheus, Grafana, Loki)
- ❌ LiteLLM routing
- ❌ Ollama on hydra-compute
- ❌ n8n automation
- ❌ RAG pipeline
- ❌ ComfyUI
- ❌ SillyTavern
- ❌ Voice pipeline (TTS/STT)
- ❌ Home Assistant
- ❌ *Arr stack
- ❌ VPN/download infrastructure
- ❌ Agent frameworks (LangGraph, CrewAI)
- ❌ MCP server integration

---

## PART 2: CANONICAL MASTER PLAN (Revised & Complete)

### 2.1 Phase 0: Immediate Fixes (Day 0)

**Power Management** - BEFORE ANYTHING ELSE:
```bash
# On hydra-ai - Set GPU power limits to prevent UPS overload
nvidia-smi -pl 450 -i 0  # RTX 5090
nvidia-smi -pl 300 -i 1  # RTX 4090
# Make persistent via systemd service
```

**NFS Mount Verification:**
```bash
# Verify correct IP (192.168.1.244, not 192.168.1.100)
df -h /mnt/models
# Should show 192.168.1.244:/mnt/user/models
```

### 2.2 Phase 1: Foundation Layer (Days 1-3)

**Day 1: Databases**
| Service | Port | Image | Priority |
|---------|------|-------|----------|
| PostgreSQL 16 | 5432 | postgres:16 | CRITICAL |
| Redis 7 | 6379 | redis:7-alpine | CRITICAL |
| Qdrant | 6333/6334 | qdrant/qdrant:latest | CRITICAL |
| MinIO | 9000/9001 | minio/minio | HIGH |

**Day 2: Observability**
| Service | Port | Image | Priority |
|---------|------|-------|----------|
| Prometheus | 9090 | prom/prometheus:v2.48.0 | CRITICAL |
| Grafana | 3003 | grafana/grafana:10.2.2 | CRITICAL |
| Loki | 3100 | grafana/loki:2.9.2 | HIGH |
| Uptime Kuma | 3001 | louislam/uptime-kuma:1 | HIGH |
| AlertManager | 9093 | prom/alertmanager:v0.26.0 | MEDIUM |

**Day 3: API Gateway**
| Service | Port | Location | Priority |
|---------|------|----------|----------|
| LiteLLM | 4000 | hydra-storage | CRITICAL |
| Ollama | 11434 | hydra-compute | HIGH |
| Update Open WebUI | 3000 | Point to LiteLLM | HIGH |

### 2.3 Phase 2: Automation & Knowledge (Days 4-7)

**Day 4: n8n Workflow Engine**
- Deploy n8n with PostgreSQL backend
- Create first workflow: cluster health check → Discord/email alert
- Connect to LiteLLM for AI-powered workflows

**Day 5: Search & Crawling**
| Service | Port | Purpose |
|---------|------|---------|
| SearXNG | 8080 | Metasearch engine |
| Firecrawl | 3002 | URL → Markdown |
| Docling | 5001 | PDF parsing |

**Day 6: Embeddings Pipeline**
- Deploy Ollama with nomic-embed-text on hydra-compute RTX 3060
- Configure LiteLLM to route embedding requests
- Test: document → chunk → embed → Qdrant

**Day 7: RSS & Knowledge Ingestion**
| Service | Port | Purpose |
|---------|------|---------|
| Miniflux | 8180 | RSS aggregation |
| n8n workflow | - | RSS → Summarize → Store |

### 2.4 Phase 3: Creative Pipeline (Days 8-10)

**Day 8: ComfyUI**
- Install on hydra-compute (RTX 5070 Ti 16GB)
- Download checkpoints: PonyXL, epiCRealism XL, RealVisXL
- Install custom nodes: Manager, ControlNet, IPAdapter, FaceDetailer
- Test API generation

**Day 9: SillyTavern + Voice**
| Service | Port | Purpose |
|---------|------|---------|
| SillyTavern | 8000 | RP frontend |
| Kokoro TTS | 10200 | Voice synthesis |
| faster-whisper | 10300 | Speech-to-text |

**Day 10: Integration**
- Connect SillyTavern → LiteLLM → TabbyAPI
- Connect SillyTavern → ComfyUI for character images
- Download uncensored models (Dark Champion 70B, Lumimaid 70B)

### 2.5 Phase 4: Content & Media (Days 11-14)

**Day 11: VPN Infrastructure**
| Service | Port | Purpose |
|---------|------|---------|
| Gluetun | - | VPN gateway |
| qBittorrent | 8082 | Torrents (through VPN) |
| SABnzbd | 8085 | Usenet (through VPN) |

**Day 12-13: *Arr Stack**
| Service | Port | Purpose |
|---------|------|---------|
| Prowlarr | 9696 | Indexer manager |
| Sonarr | 8989 | TV shows |
| Radarr | 7878 | Movies |
| Lidarr | 8686 | Music |
| Readarr | 8787 | Books |
| Bazarr | 6767 | Subtitles |
| Whisparr | 6969 | Adult content |

**Day 14: Web Crawlers**
- gallery-dl for image sites
- yt-dlp for video
- Crawl4AI for LLM-optimized scraping
- n8n workflows for automated acquisition

### 2.6 Phase 5: Home & Polish (Days 15-17)

**Day 15: Home Assistant**
| Integration | Protocol | Priority |
|-------------|----------|----------|
| Lutron | Local API | HIGH |
| Bond Bridge | Local API | HIGH |
| Nest/Google | Cloud | HIGH |
| Sonos | Local | MEDIUM |
| TVs | Local | MEDIUM |
| Roborock | Cloud/Local | MEDIUM |

**Day 16: DNS & Security**
| Service | Port | Purpose |
|---------|------|---------|
| AdGuard Home | 53, 3000 | DNS + ad blocking |
| Tailscale | - | Mesh VPN |

**Day 17: Documentation & Backup**
- Finalize NixOS configs → Git repo
- Create backup workflows in n8n
- Test disaster recovery procedures

### 2.7 Phase 6: Advanced AI (Days 18-21+)

**Day 18: Agent Foundations**
- LangGraph with PostgreSQL state persistence
- CrewAI multi-agent configuration
- Tool registry (search, crawl, code, files, images)

**Day 19: MCP Integration**
| MCP Server | Transport | Purpose |
|------------|-----------|---------|
| mcp-ssh-manager | stdio (npm) | Multi-node SSH |
| jmagar/unraid-mcp | SSE (Docker) | Unraid management |
| @modelcontextprotocol/server-docker | stdio (npm) | Container control |
| @modelcontextprotocol/server-filesystem | stdio (npm) | File operations |
| @simonb97/server-win-cli | stdio (npm) | Windows terminal |

**Day 20: Empire of Broken Queens**
- Character LoRA training pipeline
- ComfyUI workflow for consistent sprites
- Ren'Py + LLM API integration
- Wave 1 prototype

**Day 21+: Bleeding Edge**
- AIOS evaluation
- OpenHands coding agent
- Darwin-Gödel Machine experiments
- Continuous improvement

---

## PART 3: CLAUDE CODE AUTONOMOUS EXECUTION STRATEGY

### 3.1 How Claude Code Learns Context

Claude Code uses multiple mechanisms to understand project context:

| Mechanism | How It Works | Priority |
|-----------|--------------|----------|
| **CLAUDE.md** | Auto-loaded at session start, appears before every prompt | HIGHEST |
| **knowledge/** files | Referenced with `@knowledge/filename.md`, loaded on demand | HIGH |
| **Custom commands** | `.claude/commands/*.md` define reusable workflows | HIGH |
| **PRPs** | Product Requirements Prompts for feature planning | MEDIUM |
| **Sub-agents** | Spawn isolated contexts for specific tasks | MEDIUM |
| **Extended thinking** | `think`, `think hard`, `think harder`, `ultrathink` | AS NEEDED |

### 3.2 Current CLAUDE.md Analysis

**Strengths:**
- Critical rules established (discovery first, consolidated commands, NixOS declarative)
- Node architecture table with IPs
- Key services listed
- Storage paths documented
- Development patterns (SSH, NixOS rebuild, Docker)
- Port reference

**Weaknesses:**
- References knowledge files that don't exist
- Missing PRP templates
- No verification scripts
- No rollback procedures
- Missing phase-specific guidance

### 3.3 Proposed CLAUDE.md Enhancements

```markdown
# Additions to CLAUDE.md

## 🎯 CURRENT DEPLOYMENT PHASE
**Phase:** 1 - Foundation Layer
**Focus:** Databases → Observability → LiteLLM
**Blocked by:** None
**Next gate:** All DBs accessible, Grafana showing metrics

## 🔴 CRITICAL CONSTRAINTS
- GPU power limits MUST be set (5090: 450W, 4090: 300W) before heavy inference
- UPS capacity: 2000W total, hydra-ai alone can peak at 1400W
- NFS IP is 192.168.1.244 (NOT 192.168.1.100)
- IPMI for hydra-storage at 192.168.1.216

## ✅ VERIFICATION COMMANDS
```bash
# After any database deployment
docker exec hydra-postgres pg_isready -U hydra
docker exec hydra-redis redis-cli ping
curl -s http://192.168.1.244:6333/health | jq .

# After observability deployment
curl -s http://192.168.1.244:9090/-/healthy
curl -s http://192.168.1.244:3003/api/health

# After LiteLLM deployment
curl -s http://192.168.1.244:4000/health
```

## 🔄 ROLLBACK PROCEDURES
```bash
# Docker service rollback
docker-compose -f /mnt/user/appdata/hydra-stack/docker-compose.yml down <service>
docker-compose -f /mnt/user/appdata/hydra-stack/docker-compose.yml up -d <service>

# NixOS rollback
sudo nixos-rebuild switch --rollback
```
```

### 3.4 Missing Knowledge Files to Create

| File | Contents |
|------|----------|
| **nixos-modules.md** | Flake structure, module patterns, Colmena deployment, declarative containers |
| **observability.md** | Prometheus config, Grafana dashboards, alert rules, Loki queries |
| **rag-pipeline.md** | Chunking strategies, embedding models, Qdrant schemas, hybrid search |
| **automation.md** | n8n workflow patterns, LangGraph state machines, CrewAI crews |
| **home-automation.md** | Device inventory, HA integrations, automation recipes |
| **mcp-integration.md** | Claude Desktop config, SSH hosts TOML, server configurations |
| **security.md** | SSH keys, Tailscale setup, firewall rules, secrets management |

### 3.5 Custom Commands to Add

**Phase-Specific Commands:**

`.claude/commands/phase1-databases.md`:
```markdown
Deploy Phase 1 databases to hydra-storage:
1. SSH to 192.168.1.244
2. Create /mnt/user/appdata/hydra-stack directory
3. Create docker-compose.yml with PostgreSQL, Redis, Qdrant
4. Create .env with secure passwords
5. Run docker-compose up -d
6. Verify each service is healthy
7. Create required databases (hydra, n8n, litellm, grafana)
8. Report status
```

`.claude/commands/verify-phase.md`:
```markdown
Verify current phase completion:
1. Read @knowledge/infrastructure.md for service list
2. For each service in current phase:
   - Check if container/service is running
   - Verify health endpoint
   - Test basic functionality
3. Report pass/fail for each
4. Identify blockers for next phase
```

`.claude/commands/gpu-status.md`:
```markdown
Check GPU status across cluster:
1. SSH to hydra-ai: nvidia-smi --query-gpu=name,memory.used,memory.total,power.draw,temperature.gpu --format=csv
2. SSH to hydra-compute: same command
3. Check power limits are set correctly
4. Report any issues
```

### 3.6 PRP Templates

Create `PRPs/TEMPLATE.md`:
```markdown
# PRP: [Feature Name]

## Problem Statement
What problem does this solve?

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Technical Approach
### Option A: [Approach]
Pros: ...
Cons: ...

### Option B: [Approach]
Pros: ...
Cons: ...

## Recommended Approach
[Which option and why]

## Implementation Steps
1. Step 1
2. Step 2

## Verification
How do we know it's working?

## Rollback Plan
If something goes wrong...

## Dependencies
- Requires X to be complete
- Blocked by Y
```

### 3.7 Sub-Agent Strategy

Define when to use sub-agents in CLAUDE.md:

```markdown
## 🤖 SUB-AGENT USAGE

Use sub-agents for:
- **Security review:** "Use a subagent to review this config for security issues"
- **Dry-run testing:** "Have a subagent test this docker-compose file"
- **Research:** "Spawn a subagent to research latest ExLlamaV2 features"
- **Parallel tasks:** When main context is needed for something else

Don't use sub-agents for:
- Simple commands that need main context
- Tasks that require understanding the full system state
- Anything that modifies production systems (keep in main context for accountability)
```

### 3.8 Autonomous Execution Strategy

**For Claude Code to execute autonomously:**

1. **Read Phase Context First**
   - CLAUDE.md tells current phase
   - Knowledge files provide details
   - Custom commands provide workflows

2. **Discovery Before Action**
   - Always verify current state first
   - Check what's running, what's not
   - Identify actual blockers

3. **Consolidated Execution**
   - Chain commands with &&
   - Batch operations
   - Minimize back-and-forth

4. **Verification After Action**
   - Run health checks
   - Verify expected state
   - Report completion or failure

5. **Escalation Protocol**
   - If blocked → Report clearly what's needed
   - If uncertain → Ask one focused question
   - If multiple paths → Present options briefly

### 3.9 Ideal Prompt Engineering for Hydra

**Good prompts for autonomous execution:**
```
"Deploy Phase 1 databases. Follow @knowledge/databases.md for configs. Verify each is healthy before proceeding to next. Report final status."

"Check cluster status using /project:cluster-status. If any service is down, diagnose and fix. Report what was found and fixed."

"Research the current state of ExLlamaV3 tensor parallelism. Use ultrathink. Create a recommendation document."
```

**Bad prompts:**
```
"Set up the databases" (too vague, no verification)
"What should I do next?" (puts burden on human)
"Fix everything" (no specific scope)
```

---

## PART 4: RECOMMENDED IMMEDIATE ACTIONS

### 4.1 Before Using Claude Code

1. **Create missing knowledge files** (I can do this now)
2. **Enhance CLAUDE.md** with phase tracking and verification commands
3. **Add phase-specific custom commands**
4. **Create PRP template**

### 4.2 First Claude Code Session

```
Session Goal: Complete Phase 1 - Foundation Layer

Prompt: "Deploy Phase 1 databases following the master plan. Use @knowledge/databases.md for detailed configs. Chain all commands. Verify each service is healthy. Create the required databases. Report final status with any issues."
```

### 4.3 Ongoing Strategy

- Start each session by checking current phase status
- Use custom commands for common operations
- Use ultrathink for complex decisions
- Use sub-agents for research and review
- Keep main context focused on execution

---

## APPENDIX A: Complete Service Port Map

| Port | Service | Location | Phase |
|------|---------|----------|-------|
| 22 | SSH | All nodes | 0 |
| 53 | AdGuard DNS | hydra-storage | 5 |
| 80/443 | Traefik | hydra-storage | 5 |
| 1883 | MQTT | hydra-storage | 5 |
| 2283 | Immich | hydra-storage | 4 |
| 3000 | Open WebUI | hydra-ai | 0 ✅ |
| 3001 | Uptime Kuma | hydra-storage | 1 |
| 3002 | Firecrawl | hydra-storage | 2 |
| 3003 | Grafana | hydra-storage | 1 |
| 3030 | Perplexica | hydra-storage | 2 |
| 3080 | LibreChat | hydra-storage | 3 |
| 3100 | Loki | hydra-storage | 1 |
| 4000 | LiteLLM | hydra-storage | 1 |
| 5000 | TabbyAPI | hydra-ai | 0 ✅ |
| 5001 | Docling | hydra-storage | 2 |
| 5432 | PostgreSQL | hydra-storage | 1 |
| 5678 | n8n | hydra-storage | 2 |
| 6333 | Qdrant HTTP | hydra-storage | 1 |
| 6334 | Qdrant gRPC | hydra-storage | 1 |
| 6379 | Redis | hydra-storage | 1 |
| 6767 | Bazarr | hydra-storage | 4 |
| 6969 | Whisparr | hydra-storage | 4 |
| 7474 | Neo4j HTTP | hydra-storage | 6 |
| 7687 | Neo4j Bolt | hydra-storage | 6 |
| 7700 | Meilisearch | hydra-storage | 2 |
| 7878 | Radarr | hydra-storage | 4 |
| 8000 | SillyTavern | hydra-storage | 3 |
| 8080 | SearXNG | hydra-storage | 2 |
| 8082 | qBittorrent | hydra-storage | 4 |
| 8085 | SABnzbd | hydra-storage | 4 |
| 8123 | Home Assistant | hydra-storage | 5 |
| 8180 | Miniflux | hydra-storage | 2 |
| 8188 | ComfyUI | hydra-compute | 3 |
| 8686 | Lidarr | hydra-storage | 4 |
| 8787 | Readarr | hydra-storage | 4 |
| 8989 | Sonarr | hydra-storage | 4 |
| 9000 | MinIO API | hydra-storage | 1 |
| 9001 | MinIO Console | hydra-storage | 1 |
| 9090 | Prometheus | hydra-storage | 1 |
| 9093 | AlertManager | hydra-storage | 1 |
| 9696 | Prowlarr | hydra-storage | 4 |
| 9999 | Stash | hydra-storage | 0 ✅ |
| 10200 | Kokoro TTS | hydra-storage | 3 |
| 10300 | faster-whisper | hydra-storage | 3 |
| 11434 | Ollama | hydra-compute | 1 |
| 32400 | Plex | hydra-storage | 0 ✅ |

---

*Document generated: December 8, 2025*
*This is the canonical synthesis for Hydra Cluster autonomous deployment*
