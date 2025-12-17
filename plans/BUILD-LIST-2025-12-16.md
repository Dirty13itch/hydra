# HYDRA BUILD LIST
## December 16, 2025 - Comprehensive Priority Actions
### Generated from: ROADMAP.md, STRATEGIC-PLAN, bleeding-edge-research, STATE.json, system-assessment

---

## EXECUTIVE SUMMARY

**Current Phase:** 11 COMPLETE → Transitioning to Phase 12
**Cluster Health:** 100% (all services operational)
**Key Blockers:** Sudo access needed for compose file edits

---

## TIER 1: IMMEDIATE (Can Execute Now)

### 1.1 Voice Interface Completion (Phase 10 Gap)
**Impact:** HIGH | **Effort:** 2-3 hours | **Dependencies:** None

Voice endpoints exist at `/voice/*` but are not wired up. Kokoro TTS operational (67 voices).

**Tasks:**
- [ ] Deploy wake word detection (OpenWakeWord or Porcupine)
- [ ] Wire Whisper ASR to voice pipeline
- [ ] Create voice-triggered automation workflow in n8n
- [ ] Test end-to-end: wake word → STT → LLM → TTS

**Commands:**
```bash
# Test existing voice endpoints
curl -s http://192.168.1.244:8700/voice/status | jq .
curl -s http://192.168.1.244:8700/voice/voices | jq '.voices | length'
```

---

### 1.2 Activate Learning Loop
**Impact:** HIGH | **Effort:** 1 hour | **Dependencies:** hydra-tools-api running

Preference learning code exists but isn't collecting data.

**Tasks:**
- [ ] Add preference feedback collection to LiteLLM proxy
- [ ] Create n8n workflow to periodically analyze preferences
- [ ] Wire feedback to RouteLLM classifier training
- [ ] Set up weekly model performance report

**Files:**
- `src/hydra_tools/preference_learning.py` (exists)
- Endpoints: `/preferences/*`

---

### 1.3 MCP Server Enhancement (bleeding-edge alignment)
**Impact:** MEDIUM | **Effort:** 2 hours | **Dependencies:** None

MCP is now Linux Foundation standard. Enhance existing hydra-mcp with new capabilities.

**Tasks:**
- [ ] Add ComfyUI tools to MCP server
- [ ] Add n8n workflow trigger tools
- [ ] Implement code execution pattern (98.7% token reduction)
- [ ] Register tools with Claude Code config

**Reference:** bleeding-edge-research §3 - MCP Standardization

---

### 1.4 Predictive Maintenance Implementation
**Impact:** HIGH | **Effort:** 2 hours | **Dependencies:** Prometheus data

Currently reactive only. Need proactive failure prediction.

**Tasks:**
- [ ] Create Prometheus recording rules for trend analysis
- [ ] Implement VRAM usage trend prediction (warning before OOM)
- [ ] Add disk fill-rate prediction
- [ ] Create GPU thermal trend alerts
- [ ] Wire to self-diagnosis engine

**Files:**
- `src/hydra_tools/self_diagnosis.py` (extend)
- `prometheus/recording_rules.yml` (add)

---

### 1.5 GitHub Webhook Activation
**Impact:** LOW | **Effort:** 30 min | **Dependencies:** GitHub repo access

1 n8n workflow inactive due to missing GitHub config.

**Tasks:**
- [ ] Create GitHub webhook in relevant repos
- [ ] Configure n8n GitHub Webhook Handler workflow
- [ ] Test with push event

---

## TIER 2: SHORT-TERM (This Week)

### 2.1 Phase 12 Kickoff: Empire Character System
**Impact:** HIGH | **Effort:** 4-6 hours | **Dependencies:** ComfyUI running

Start automated visual novel asset generation.

**Tasks:**
- [ ] Create Qdrant collection `empire_characters` for face embeddings
- [ ] Set up InstantID workflow in ComfyUI for face consistency
- [ ] Create character reference sheet format (JSON schema)
- [ ] Import 21 queen reference images
- [ ] Test character generation consistency

**Reference:** ROADMAP.md Phase 12 Week 13

---

### 2.2 Speculative Decoding Evaluation
**Impact:** HIGH | **Effort:** 3 hours | **Dependencies:** None

Potential 2-4x inference speedup per bleeding-edge research.

**Tasks:**
- [ ] Check ExLlamaV2 current version for speculative decoding support
- [ ] If supported, test draft model configuration (8B draft → 70B verify)
- [ ] Benchmark before/after token throughput
- [ ] If significant gain, deploy to production

**Reference:** bleeding-edge-research §7 - Inference Optimization

---

### 2.3 MIRIX-Style Memory Enhancement
**Impact:** MEDIUM | **Effort:** 4 hours | **Dependencies:** Letta running

Current memory is flat. Implement tiered architecture.

**Tasks:**
- [ ] Implement Core Memory tier (always in context, 512 tokens max)
- [ ] Add Procedural Memory for learned workflows
- [ ] Create Resource Memory index for documents
- [ ] Wire Neo4j for relationship queries
- [ ] Test multi-hop reasoning

**Reference:** bleeding-edge-research §2 - MIRIX architecture

---

### 2.4 E2B Sandbox Deployment
**Impact:** HIGH | **Effort:** 2 hours | **Dependencies:** None

Required for safe self-modification capabilities (DGM-style evolution).

**Tasks:**
- [ ] Deploy E2B sandbox container
- [ ] Configure Firecracker microVM settings
- [ ] Create sandbox execution API endpoint
- [ ] Wire to code generation workflows
- [ ] Test isolation with malicious payload

**Reference:** bleeding-edge-research §10 - Safety & Sandboxing

---

## TIER 3: MEDIUM-TERM (This Month)

### 3.1 Home Assistant Deep Integration
**Impact:** HIGH | **Effort:** 6 hours | **Dependencies:** HA running

Enable presence-aware operations and voice control.

**Tasks:**
- [ ] Configure HA REST API integration in hydra-tools
- [ ] Create presence detection automations
- [ ] Implement GPU power management based on presence
- [ ] Add room-aware voice routing
- [ ] Create "Shaun leaves" / "Shaun arrives" automations

**Reference:** ROADMAP.md Phase 13

---

### 3.2 Calendar Intelligence
**Impact:** MEDIUM | **Effort:** 4 hours | **Dependencies:** OAuth setup

Morning briefing should include schedule awareness.

**Tasks:**
- [ ] Set up Google Calendar OAuth2 flow
- [ ] Create calendar sync workflow (7-day lookahead)
- [ ] Implement meeting-aware inference blocking
- [ ] Add pre-meeting research triggers
- [ ] Include schedule in morning briefing

**Reference:** ROADMAP.md Phase 14 Week 21

---

### 3.3 Network Segmentation (Requires Sudo)
**Impact:** MEDIUM | **Effort:** 3 hours | **Dependencies:** sudo access

All 64 containers on single Docker network - security risk.

**Tasks:**
- [ ] Create isolated Docker networks (inference, data, public)
- [ ] Migrate containers to appropriate networks
- [ ] Configure firewall rules between segments
- [ ] Test service communication
- [ ] Document network topology

---

### 3.4 Container Healthcheck Audit (Requires Sudo)
**Impact:** HIGH | **Effort:** 4 hours | **Dependencies:** sudo access

39 containers without healthchecks = monitoring blind spots.

**Priority Containers:**
- hydra-n8n (core automation)
- homeassistant (home integration)
- sillytavern (creative tool)
- hydra-brain (orchestration)
- kokoro-tts (voice synthesis)

---

## TIER 4: LONG-TERM (This Quarter)

### 4.1 DGM-Inspired Self-Improvement Loop
**Impact:** VERY HIGH | **Effort:** 20+ hours | **Dependencies:** E2B, benchmarks

Implement Darwin Gödel Machine concepts for autonomous evolution.

**Tasks:**
- [ ] Create Hydra capability benchmark suite
- [ ] Implement code modification sandbox
- [ ] Build empirical validation pipeline
- [ ] Create improvement archive
- [ ] Add constitutional constraints enforcement
- [ ] Human-in-loop gates for significant changes

**Reference:** bleeding-edge-research §1 - Darwin Gödel Machine

---

### 4.2 AIOS Kernel Integration
**Impact:** HIGH | **Effort:** 15 hours | **Dependencies:** Research

Implement agent scheduling and resource management.

**Tasks:**
- [ ] Evaluate AIOS kernel concepts
- [ ] Implement agent scheduling (FIFO, Round Robin, priority)
- [ ] Add context window management
- [ ] Create memory isolation between agents
- [ ] Implement tool access control

**Reference:** bleeding-edge-research §4 - AIOS

---

### 4.3 Multi-User Architecture
**Impact:** MEDIUM | **Effort:** 25 hours | **Dependencies:** Auth system

Support multiple users with isolation.

**Tasks:**
- [ ] Letta multi-agent deployment (per-user)
- [ ] Implement permission system (ADMIN/STANDARD/LIMITED)
- [ ] Create auth layer with Tailscale identity
- [ ] Build shared workspaces feature
- [ ] Onboard second user

**Reference:** ROADMAP.md Phase 15

---

## QUICK WINS (< 30 min each)

| Task | Command/Action |
|------|----------------|
| Test all CrewAI crews | `curl -X POST http://192.168.1.244:8700/scheduler/trigger/monitoring` |
| Verify Kokoro TTS | `curl -X POST http://192.168.1.244:8880/v1/audio/speech -d '{"input":"Test","voice":"af_bella"}'` |
| Check inference routing | `curl -s http://192.168.1.244:8700/routing/classify -d '{"prompt":"Hello world"}'` |
| Trigger overnight research | `curl -X POST http://192.168.1.244:5678/webhook/research-queue` |
| Check capability gaps | `curl -s http://192.168.1.244:8700/capabilities/backlog` |
| View self-diagnosis | `curl -s http://192.168.1.244:8700/diagnosis/report` |
| Check optimization suggestions | `curl -s http://192.168.1.244:8700/optimization/suggestions` |

---

## TECHNOLOGY DECISIONS (From Research)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tool Integration | MCP-native | Linux Foundation standard, 97M+ monthly downloads |
| Memory Architecture | Hybrid (vector + graph) | Multi-hop reasoning per MIRIX |
| Code Execution | Always sandboxed | E2B/Firecracker for safety |
| Agent Architecture | Multi-agent orchestrated | Not single-agent for complex tasks |
| Primary TTS | Kokoro | Apache 2.0, 40-70ms latency, #1 on HF Arena |
| Inference Optimization | Monitor ExLlamaV3 | Speculative decoding potential |

---

## SUCCESS METRICS

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Voice interface operational | No | Yes | 1 week |
| Preference data collected | 0 | 1000+ interactions | 1 month |
| Inference speedup | 1x | 2-3x (speculative) | 2 weeks |
| Predictive alerts | 0 | 10+ patterns | 1 week |
| Empire chapters automated | 0 | 1 complete | 1 month |
| External integrations | 0 | 2 (calendar, HA) | 1 month |

---

## NEXT SESSION PRIORITIES

When Claude Code starts next session, focus on:
1. **Voice pipeline wiring** - Highest user-facing impact
2. **Predictive maintenance** - Prevents overnight failures
3. **Speculative decoding test** - Could double inference speed
4. **Empire character setup** - Enables Phase 12

---

*Generated: 2025-12-16T06:15:00Z*
*Based on: 5 source documents, 142 identified improvements*
*Author: Claude Code (Opus 4.5) as Hydra Autonomous Steward*
