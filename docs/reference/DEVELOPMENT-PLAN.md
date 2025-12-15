# HYDRA DEVELOPMENT PLAN

> *Comprehensive roadmap from current state to autonomous AI operating system*

**Generated:** 2025-12-13
**Author:** Hydra Autonomous Steward
**Baseline:** Phase 11 Code Complete, Pre-Deployment

---

## Executive Summary

Hydra has achieved **Phase 11 code completion** - all self-improvement tools, APIs, deployment scripts, and test suites are written. The system is positioned at a critical transition point: moving from "development" to "production deployment" and then to the advanced phases (12-15) that will realize the full vision of an autonomous AI operating system.

### Current State Assessment

| Metric | Value | Status |
|--------|-------|--------|
| Phases Complete | 10 of 15 | On Track |
| Phase 11 Code | 100% | Complete |
| Phase 11 Deployed | 0% | Pending |
| Containers Running | 54 | Active |
| Containers Healthy | 36 | Degraded |
| n8n Workflows Created | 14 | Not Activated |
| NixOS Modules Created | 15 | Not Applied |
| Prometheus Targets | 11/11 | All Up |

### Critical Path

```
IMMEDIATE (Deploy What's Built)
    ↓
Phase 11 Production → Fix Healthchecks → Activate Workflows → Apply NixOS Configs
    ↓
SHORT-TERM (Stabilize & Integrate)
    ↓
SOPS Migration → Uptime Kuma Setup → Validate Self-Improvement Loop
    ↓
MEDIUM-TERM (Advanced Capabilities)
    ↓
Phase 12: Empire Production → Phase 13: Home Automation → Phase 14: External APIs
    ↓
LONG-TERM (Vision Complete)
    ↓
Phase 15: Multi-User → Full Autonomy
```

---

## Part 1: Immediate Deployment (Priority: CRITICAL)

### 1.1 Deploy Phase 11 Tools API

**What:** Deploy the unified self-improvement API to production
**Why:** All Phase 11 code is written but not running in production
**How:**

```bash
# From hydra-storage or any node with SSH access
./scripts/deploy-hydra-tools.sh --build
```

**Verification:**
```bash
curl http://192.168.1.244:8700/health
curl http://192.168.1.244:8700/docs  # OpenAPI documentation
```

**Components Deployed:**
- `/diagnosis/*` - Failure pattern detection & auto-remediation
- `/optimization/*` - GPU/CPU/RAM utilization analysis
- `/knowledge/*` - Knowledge lifecycle management
- `/capabilities/*` - Feature gap tracking
- `/routing/*` - RouteLLM prompt classification
- `/preferences/*` - User preference learning

### 1.2 Fix Container Healthchecks

**What:** Resolve 18 containers showing "unhealthy" status
**Why:** STATE.json shows degraded status; monitoring false positives
**How:**

1. **Apply healthcheck fixes:**
```bash
ssh root@192.168.1.244
cd /mnt/user/appdata/hydra-stack
docker-compose -f docker-compose.yml -f healthchecks-additions.yml up -d
```

2. **Containers requiring fixes:**
| Container | Issue | Fix |
|-----------|-------|-----|
| hydra-postgres | Missing pg_isready | Add healthcheck with pg_isready |
| hydra-redis | Missing redis-cli ping | Add healthcheck with redis-cli |
| hydra-qdrant | Wrong endpoint | Use /readiness endpoint |
| hydra-letta | HTTP check timeout | Increase timeout to 30s |
| hydra-neo4j | Missing curl | Use neo4j status command |
| letta-db | Missing pg_isready | Add proper PostgreSQL check |
| letta-proxy | No curl available | Use Python urllib |
| hydra-alertmanager | Wrong port | Fix to 9093 |
| hydra-uptime-kuma | Slow startup | Increase start_period |
| hydra-searxng | Wrong path | Use /healthz endpoint |
| homepage | Missing check | Add HTTP check |
| open-webui | Slow startup | Increase start_period to 60s |
| Plex-Media-Server | Different API | Use /identity endpoint |
| hydra-crewai | No healthcheck | Add HTTP /health check |
| hydra-mcp | Timeout | Increase to 30s |
| hydra-watchtower | No healthcheck | Not needed (runs periodically) |
| auditforecaster-* | Various | Fix per service needs |

### 1.3 Activate n8n Workflows

**What:** Import and activate 14 created workflows
**Why:** Workflows exist as JSON but aren't running in n8n
**How:**

```bash
cd /mnt/user/projects/hydra
python scripts/activate-n8n-workflows.py
```

**Workflows to Activate:**
| Workflow | Schedule | Purpose |
|----------|----------|---------|
| letta-memory-update | Every 6 hours | Memory synchronization |
| learnings-capture | Every 6 hours | LEARNINGS.md updates |
| knowledge-refresh | Daily midnight | Knowledge file refresh |
| autonomous-research | Daily 2 AM | Overnight research |
| cluster-health-digest | Daily 6 AM | Morning health report |
| container-auto-restart | On alert | Self-healing |
| disk-cleanup | Weekly Sunday | Storage maintenance |

### 1.4 Apply NixOS Configurations

**What:** Apply DNS and firewall modules to NixOS nodes
**Why:** Nodes still using router DNS, firewall rules are temporary
**How:**

```bash
# On hydra-ai (192.168.1.250)
sudo cp /path/to/dns-adguard.nix /etc/nixos/modules/
sudo cp /path/to/firewall-hydra.nix /etc/nixos/modules/
sudo nixos-rebuild switch

# On hydra-compute (192.168.1.203)
sudo cp /path/to/dns-adguard.nix /etc/nixos/modules/
sudo cp /path/to/firewall-hydra.nix /etc/nixos/modules/
sudo nixos-rebuild switch
```

**Configuration Changes:**
- DNS: Point to AdGuard at 192.168.1.244:53
- Firewall: Permanent rules for ports 9100 (node-exporter), 9835 (nvidia-exporter)

---

## Part 2: Short-Term Stabilization (Priority: HIGH)

### 2.1 SOPS Secrets Migration

**Current State:** Infrastructure secrets in plaintext docker-compose.yml
**Target State:** All secrets encrypted with SOPS + age

**Secrets to Migrate:**
| Secret | Current Location | Priority |
|--------|-----------------|----------|
| PostgreSQL password | docker-compose.yml | HIGH |
| Redis password | docker-compose.yml | HIGH |
| LiteLLM master key | docker-compose.yml | HIGH |
| Vaultwarden admin token | CLAUDE.md | MEDIUM |
| n8n encryption key | docker-compose.yml | MEDIUM |

**Implementation:**
```bash
# Create secrets.yaml
cat > secrets.yaml << 'EOF'
postgresql:
  password: <encrypted>
redis:
  password: <encrypted>
litellm:
  master_key: <encrypted>
EOF

# Encrypt with SOPS
sops -e -i secrets.yaml

# Update docker-compose to use sops-decrypt
```

### 2.2 Uptime Kuma Monitor Setup

**Current State:** Uptime Kuma running but NO monitors configured
**Target State:** 40+ monitors covering all critical services

**Monitor Categories:**
| Category | Count | Services |
|----------|-------|----------|
| Core Infrastructure | 8 | Databases, Redis, Qdrant, Neo4j |
| Inference | 4 | TabbyAPI, Ollama x2, LiteLLM |
| Memory & Agents | 4 | Letta, CrewAI, MCP Server |
| Observability | 4 | Prometheus, Grafana, Loki, Alertmanager |
| Media | 6 | Plex, *Arr apps, Stash |
| Web Services | 8 | SearXNG, Firecrawl, Homepage, etc. |
| Control Plane | 4 | UI, Backend, Tools API |
| NixOS Nodes | 4 | hydra-ai, hydra-compute health |

**Implementation:**
```bash
python scripts/setup-uptime-kuma.py
```

### 2.3 Validate Self-Improvement Loop

**Objective:** Verify that Phase 11 tools actually improve the system

**Test Scenarios:**

1. **Preference Learning:**
   - Generate 20 varied prompts through LiteLLM
   - Record outcomes (success, regeneration, latency)
   - Verify model recommendations update

2. **Self-Diagnosis:**
   - Intentionally trigger failures (kill a container)
   - Verify failure pattern detection
   - Verify remediation suggestions are accurate

3. **Knowledge Optimization:**
   - Query for stale knowledge entries
   - Verify staleness thresholds work
   - Test consolidation suggestions

4. **Resource Optimization:**
   - Run inference workload
   - Check GPU utilization tracking
   - Verify optimization suggestions make sense

---

## Part 3: Phase 12 - Empire of Broken Queens Production

### Vision Alignment
> *"Generates the next batch of character assets for Empire of Broken Queens"* - VISION.md Morning scenario

### 3.1 Character Consistency Pipeline

**Components:**
- **Reference Manager:** Store canonical character references (face, outfit, pose variations)
- **InstantID Integration:** Face consistency across generations
- **IP-Adapter Integration:** Style consistency across scenes
- **LoRA Training Pipeline:** Custom character LoRAs for perfect consistency

**Implementation:**

```
┌─────────────────────────────────────────────────────────────┐
│                  CHARACTER PIPELINE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CHARACTER_REF_DB (Qdrant)                                  │
│  └─ Characters: Aria, Marcus, Elena, ...                    │
│  └─ Per character: face_ref, outfit_refs[], pose_refs[]     │
│  └─ Style guide: lighting, color palette, mood              │
│                                                              │
│  GENERATION REQUEST                                          │
│  {                                                           │
│    "character": "aria",                                      │
│    "scene": "throne_room_confrontation",                    │
│    "emotion": "determined",                                  │
│    "outfit": "battle_armor"                                 │
│  }                                                           │
│         │                                                    │
│         ▼                                                    │
│  COMFYUI WORKFLOW                                           │
│  └─ Load character references from Qdrant                   │
│  └─ Apply InstantID for face                                │
│  └─ Apply IP-Adapter for style                              │
│  └─ Apply character LoRA (if available)                     │
│  └─ Generate with scene prompt                              │
│  └─ Post-process: upscale, color correct                    │
│         │                                                    │
│         ▼                                                    │
│  OUTPUT                                                      │
│  └─ Image stored to project folder                          │
│  └─ Metadata logged to Neo4j                                │
│  └─ Quality score computed                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Chapter Asset Automation

**n8n Workflow: Empire Asset Generator**

```
Trigger: New chapter script uploaded OR manual trigger
    ↓
Parse script for character appearances, scenes, dialogue
    ↓
For each scene:
    ├─ Generate background/environment
    ├─ Generate character poses per character present
    └─ Queue dialogue for voice synthesis
    ↓
Assembly: Organize assets into chapter folder structure
    ↓
Notify: "Chapter N assets ready for review"
```

### 3.3 Voice Pipeline

**Components:**
- **Kokoro TTS** (already deployed): Base voice synthesis
- **Voice Character Profiles:** Per-character voice settings
- **Emotion Detection:** Map script emotions to TTS parameters

**Character Voice Profiles:**
```yaml
characters:
  aria:
    voice_id: "af_bella"
    speed: 0.95
    pitch_shift: 0
    emotion_mapping:
      angry: {speed: 1.1, pitch: +10}
      sad: {speed: 0.8, pitch: -5}

  marcus:
    voice_id: "am_michael"
    speed: 1.0
    pitch_shift: -20
```

### 3.4 Quality Feedback Loop

**Automated Quality Scoring:**
- Face consistency score (compare to reference)
- Style consistency score (compare to style guide)
- Technical quality (resolution, artifacts)

**Human Feedback Integration:**
- Accept/reject generated assets
- Feedback recorded to preference learning
- Model and prompt improvements derived

---

## Part 4: Phase 13 - Home Automation Integration

### Vision Alignment
> *"Presence-aware operations"* - ROADMAP.md

### 4.1 Home Assistant Connection

**Current State:** Home Assistant running at 192.168.1.244:8123
**Target State:** Full bidirectional integration with Hydra

**Integration Points:**

1. **Presence Awareness:**
   - Detect when Shaun is home/away/sleeping
   - Adjust GPU power states based on presence
   - Queue heavy workloads for away time

2. **Voice Control:**
   - Home Assistant voice pipeline → Hydra inference
   - "Hey Hydra, research X overnight"
   - "Hey Hydra, generate chapter 5 assets"

3. **Ambient Feedback:**
   - LED strip showing cluster health (green/yellow/red)
   - Notification announcements via speakers
   - Dashboard on always-on tablet

### 4.2 Device Integration

**Pending Devices:**
| Device | Protocol | Integration |
|--------|----------|-------------|
| Lutron Caseta | Lutron Bridge | Lighting control |
| Bond Bridge | Bond API | Fan/shade control |
| Nest Thermostat | Nest API | Climate awareness |
| Ring Doorbell | Ring API | Presence detection |

**Hydra-Specific Automations:**
```yaml
automations:
  - trigger: Shaun leaves home
    action:
      - Set GPU power to eco mode
      - Queue overnight research
      - Reduce HVAC in office

  - trigger: Shaun returns home
    action:
      - Set GPU power to normal
      - Pre-warm office
      - Show cluster status on display

  - trigger: Bedtime detected
    action:
      - Queue any pending research
      - Set GPU to full power (overnight work)
      - Prepare morning briefing
```

### 4.3 Voice Interface

**Components:**
- **Whisper ASR:** Speech-to-text (hydra-compute:9000)
- **Kokoro TTS:** Text-to-speech (hydra-compute:8080)
- **Wake Word:** "Hey Hydra" detection
- **Intent Recognition:** Route to appropriate system

**Voice Flow:**
```
"Hey Hydra" → Wake word detected
    ↓
Speech recorded → Whisper transcription
    ↓
Intent classification (RouteLLM)
    ↓
Execute: Inference | Research | Home Control | Creative
    ↓
Response generated → Kokoro synthesis
    ↓
Audio played through speakers
```

---

## Part 5: Phase 14 - External Intelligence

### Vision Alignment
> *"API integrations (calendar, email, etc.), Proactive notifications"* - ROADMAP.md

### 5.1 Calendar Integration

**Source:** Google Calendar API
**Use Cases:**
- Awareness of Shaun's schedule
- Block heavy inference during meetings
- Pre-research for upcoming meetings

**Implementation:**
```python
# Scheduled workflow
def sync_calendar():
    events = google_calendar.get_events(next_7_days)
    for event in events:
        letta.update_memory("upcoming_events", event)
        if event.has_topic():
            queue_research(event.topic)
```

### 5.2 Email Intelligence

**Source:** Gmail API (read-only)
**Use Cases:**
- Summarize important emails in morning briefing
- Flag urgent items for attention
- Research context for specific threads

**Privacy Guardrails:**
- Read-only access
- No sending capability
- Local processing only
- Opt-in per sender/thread

### 5.3 Financial Awareness

**Sources:** Plaid API, crypto exchanges
**Use Cases:**
- Portfolio summary in morning briefing
- Significant change alerts
- Research on holdings

### 5.4 News & Research

**Sources:** RSS (Miniflux), SearXNG, specialized APIs
**Use Cases:**
- Curated tech news summary
- Monitoring specific topics (AI, gaming, etc.)
- Research queue processing

---

## Part 6: Phase 15 - Multi-User Support

### Vision Alignment
> *"Separate memory contexts, Shared vs private knowledge"* - ROADMAP.md

### 6.1 User Context Separation

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                   MULTI-USER ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  USER CONTEXTS (Letta)                                      │
│  ├─ shaun (primary)                                         │
│  │   ├─ core_memory: personal preferences, projects         │
│  │   ├─ archival: full history                              │
│  │   └─ permissions: ADMIN (full access)                    │
│  │                                                           │
│  ├─ guest_1                                                  │
│  │   ├─ core_memory: limited context                        │
│  │   ├─ archival: session only                              │
│  │   └─ permissions: LIMITED (no admin, no media)           │
│  │                                                           │
│  └─ family_member                                            │
│      ├─ core_memory: family context                         │
│      ├─ archival: persistent but separate                   │
│      └─ permissions: STANDARD (media, no admin)             │
│                                                              │
│  SHARED KNOWLEDGE                                            │
│  └─ Cluster documentation                                    │
│  └─ General capabilities                                     │
│  └─ Approved research                                        │
│                                                              │
│  PRIVATE KNOWLEDGE (per user)                                │
│  └─ Personal preferences                                     │
│  └─ Individual projects                                      │
│  └─ Private conversations                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Authentication

**Options:**
1. **Vaultwarden SSO:** Use existing password manager for auth
2. **Tailscale Identity:** Use Tailscale user identity
3. **Local Auth:** Simple username/password in Hydra

**Recommendation:** Tailscale identity (already deployed) + optional PIN for sensitive operations

### 6.3 Collaboration Features

**Shared Workspaces:**
- Joint projects with shared context
- Collaborative research queues
- Shared media requests

**Privacy Controls:**
- Per-conversation privacy setting
- Audit log for admin
- Data export/deletion per user

---

## Part 7: Technical Debt & Maintenance

### 7.1 Known Technical Debt

| Item | Priority | Effort | Impact |
|------|----------|--------|--------|
| Plaintext secrets | HIGH | Medium | Security risk |
| 18 unhealthy containers | HIGH | Low | Monitoring noise |
| Inactive n8n workflows | HIGH | Low | Missing automation |
| NixOS DNS/firewall | MEDIUM | Low | Minor inefficiency |
| Uptime Kuma empty | MEDIUM | Medium | No endpoint monitoring |
| temp_migration cleanup | LOW | Low | 2.9TB disk space |
| Documentation sync | LOW | Ongoing | Drift risk |

### 7.2 Maintenance Schedule

**Daily (Automated):**
- STATE.json update (every 15 min)
- Health digest generation (6 AM)
- Log rotation
- Backup verification

**Weekly (Automated):**
- Disk cleanup workflow
- Maintenance crew assessment
- Docker image updates (Watchtower)

**Monthly (Manual Review):**
- Security audit
- Performance baseline comparison
- Capacity planning review
- ROADMAP progress assessment

### 7.3 Backup Strategy

**Currently Implemented:**
- PostgreSQL daily dumps
- Docker volume snapshots (Unraid)
- NixOS configuration in git

**Recommended Additions:**
- Letta memory export (weekly)
- Qdrant collection backup (weekly)
- Neo4j graph export (weekly)
- Full disaster recovery test (quarterly)

---

## Part 8: Success Metrics & Milestones

### From VISION.md Success Criteria

| Criteria | Current | Target | Measurement |
|----------|---------|--------|-------------|
| Service uptime | ~95% | 99%+ | Uptime Kuma |
| Manual intervention | Daily | Rare | Incident log |
| Declarative deployment | Partial | Full | All services in compose/nix |
| Disaster recovery | Untested | Proven | Quarterly test |
| 70B inference speed | 30+ tok/s | 30+ tok/s | Prometheus |
| Context persistence | Working | Seamless | User feedback |
| Character consistency | N/A | 95%+ | Quality scores |
| Voice synthesis | Basic | Natural | User feedback |
| Need anticipation | None | Proactive | Briefing quality |
| Preference memory | Basic | Automatic | Preference API |
| Overnight research | Manual | Autonomous | Morning findings |
| Knowledge growth | N/A | Measurable | Knowledge metrics |

### Phase Completion Milestones

| Phase | Milestone | Status |
|-------|-----------|--------|
| 11 | Self-improvement tools deployed & validated | PENDING |
| 12 | First automated chapter generation | NOT STARTED |
| 13 | Voice control working room-to-room | NOT STARTED |
| 14 | Morning briefing includes calendar/email | NOT STARTED |
| 15 | Second user onboarded successfully | NOT STARTED |

---

## Part 9: Implementation Order

### Execution Sequence

```
WEEK 1: Deploy What's Built
├── Day 1-2: Deploy Phase 11 Tools API
│   └── ./scripts/deploy-hydra-tools.sh --build
│   └── Verify all endpoints responding
│
├── Day 3: Fix Container Healthchecks
│   └── Apply healthchecks-additions.yml
│   └── Verify STATE.json shows all healthy
│
├── Day 4-5: Activate n8n Workflows
│   └── python scripts/activate-n8n-workflows.py
│   └── Monitor first 24h of execution
│
└── Day 6-7: Apply NixOS Configs
    └── DNS and firewall on both nodes
    └── Verify nodes using AdGuard DNS

WEEK 2: Stabilize & Secure
├── Day 1-3: SOPS Secrets Migration
│   └── Encrypt all secrets
│   └── Update compose files
│   └── Verify services still work
│
├── Day 4-5: Uptime Kuma Setup
│   └── python scripts/setup-uptime-kuma.py
│   └── Configure alerting
│
└── Day 6-7: Validate Self-Improvement
    └── Run test scenarios
    └── Document results

WEEK 3-4: Phase 12 Foundation
├── Character reference system design
├── ComfyUI workflow development
├── n8n orchestration workflow
└── First automated chapter test

MONTH 2: Phase 12 Production
├── Full character consistency pipeline
├── Voice synthesis integration
├── Quality feedback loops
└── First "real" chapter generation

MONTH 3: Phase 13 Home Automation
├── Home Assistant deep integration
├── Presence automation
├── Voice interface
└── Ambient feedback

MONTH 4+: Phases 14-15
├── External API integrations
├── Multi-user foundation
└── Full vision realization
```

---

## Part 10: Quick Reference Commands

### Deployment Commands
```bash
# Deploy Phase 11 Tools API
./scripts/deploy-hydra-tools.sh --build

# Fix healthchecks
docker-compose -f docker-compose.yml -f healthchecks-additions.yml up -d

# Activate n8n workflows
python scripts/activate-n8n-workflows.py

# Apply NixOS changes
sudo nixos-rebuild switch
```

### Verification Commands
```bash
# Check Phase 11 API
curl http://192.168.1.244:8700/health
curl http://192.168.1.244:8700/diagnosis/report
curl http://192.168.1.244:8700/optimization/suggestions

# Check container health
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -v healthy

# Check n8n workflows
curl http://192.168.1.244:5678/api/v1/workflows | jq '.data[] | {name, active}'

# Check cluster status
curl http://192.168.1.244:8600/cluster/status
```

### Rollback Commands
```bash
# Docker rollback
docker-compose down <service>
docker-compose pull <service>
docker-compose up -d <service>

# NixOS rollback
sudo nixos-rebuild switch --rollback

# Phase 11 Tools rollback
ssh root@192.168.1.244 "cd /mnt/user/appdata/hydra-tools && docker-compose down"
```

---

## Appendix A: File Reference

### Phase 11 Files Created

| File | Purpose |
|------|---------|
| `src/hydra_tools/self_diagnosis.py` | Failure pattern detection |
| `src/hydra_tools/resource_optimization.py` | GPU/CPU/RAM analysis |
| `src/hydra_tools/knowledge_optimization.py` | Knowledge lifecycle |
| `src/hydra_tools/capability_expansion.py` | Feature gap tracking |
| `src/hydra_tools/routellm.py` | Prompt classification |
| `src/hydra_tools/preference_learning.py` | User preference tracking |
| `src/hydra_tools/api.py` | Unified FastAPI |
| `docker/Dockerfile.hydra-tools` | Container definition |
| `docker-compose/hydra-tools-api.yml` | Service composition |
| `scripts/deploy-hydra-tools.sh` | Deployment automation |
| `tests/test_*.py` | Comprehensive test suite |

### Configuration Files

| File | Purpose |
|------|---------|
| `config/n8n/workflows/*.json` | n8n workflow definitions |
| `config/nixos/dns-adguard.nix` | DNS configuration |
| `config/nixos/firewall-hydra.nix` | Firewall rules |
| `config/grafana/dashboards/*.json` | Dashboard definitions |
| `docker-compose/healthchecks-additions.yml` | Healthcheck fixes |

---

## Appendix B: API Reference

### Hydra Tools API (Port 8700)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Overall health status |
| `/diagnosis/report` | GET | Diagnostic report |
| `/diagnosis/failure` | POST | Record failure |
| `/diagnosis/patterns` | GET | Failure patterns |
| `/optimization/suggestions` | GET | Optimization suggestions |
| `/optimization/patterns` | GET | Resource patterns |
| `/knowledge/metrics` | GET | Knowledge metrics |
| `/knowledge/stale` | GET | Stale entries |
| `/capabilities/backlog` | GET | Capability gaps |
| `/capabilities/gap` | POST | Report gap |
| `/routing/classify` | POST | Classify prompt |
| `/preferences/interaction` | POST | Record interaction |
| `/preferences/recommendation` | GET | Model recommendation |

### MCP Server (Port 8600)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/cluster/status` | GET | Cluster overview |
| `/services/status` | GET | Service status |
| `/containers/list` | GET | Container list |
| `/containers/restart` | POST | Restart container |
| `/metrics` | GET | Prometheus metrics |
| `/letta/message` | POST | Send to Letta |
| `/crews/run/{name}` | POST | Trigger crew |
| `/knowledge/search` | GET | Search knowledge |

---

*This document is the implementation plan for achieving the VISION.md end state.*
*Update as phases complete and priorities shift.*
*Last updated: 2025-12-13*
