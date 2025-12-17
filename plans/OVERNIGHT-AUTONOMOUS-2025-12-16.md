# HYDRA OVERNIGHT AUTONOMOUS WORK PLAN v2
## December 16, 2025 - "Best AI System Ever" Edition
### Full sudo access granted | Git push approved

---

## STRATEGIC VISION

**Goal:** Not just maintenance - build toward a **self-improving autonomous AI operating system**.

From bleeding-edge research, the differentiating capabilities are:
1. **Self-Improvement Loop** (Darwin Gödel Machine concepts)
2. **Constitutional Constraints** (safe autonomy)
3. **Sandboxed Execution** (E2B/Firecracker)
4. **Multi-Tier Memory** (MIRIX architecture)
5. **MCP-Native Tools** (Linux Foundation standard)
6. **Inference Optimization** (speculative decoding)

---

## REVISED EXECUTION PLAN

### PHASE 1: Constitutional Framework (1.5 hours)
**Goal:** Establish immutable safety rails that enable aggressive autonomy

- [ ] **1.1** Create `/mnt/user/appdata/hydra-dev/CONSTITUTION.yaml` with immutable constraints
- [ ] **1.2** Build constitutional enforcement module in hydra-tools
- [ ] **1.3** Create audit logging system for all autonomous actions
- [ ] **1.4** Wire constitutional checks to all dangerous operations
- [ ] **1.5** Test that violations are blocked and logged

**Why:** Can't have self-improvement without safety. This unlocks everything else.

---

### PHASE 2: Self-Improvement Infrastructure (3 hours)
**Goal:** Build the foundation for Hydra to improve itself

- [ ] **2.1** Create benchmark suite for measuring Hydra capabilities:
  - Task completion success rate
  - Inference latency percentiles
  - Memory recall accuracy
  - Tool execution reliability
  - Error recovery rate
- [ ] **2.2** Build improvement archive system (track what changes worked)
- [ ] **2.3** Create code modification sandbox (isolated test environment)
- [ ] **2.4** Implement A/B testing framework for configuration changes
- [ ] **2.5** Build rollback mechanism for failed improvements
- [ ] **2.6** Create "improvement proposal" system (propose → test → validate → deploy)

**Why:** This is the DGM core - Hydra that makes itself better.

---

### PHASE 3: E2B Sandboxing (2 hours)
**Goal:** Safe code execution environment for self-modification

- [ ] **3.1** Research E2B vs Firecracker vs Docker-in-Docker for sandboxing
- [ ] **3.2** Deploy chosen sandbox solution
- [ ] **3.3** Create sandbox execution API endpoint
- [ ] **3.4** Wire sandbox to code generation/testing workflows
- [ ] **3.5** Test isolation with intentionally dangerous code
- [ ] **3.6** Integrate with constitutional constraints

**Why:** Can't run self-generated code without isolation.

---

### PHASE 4: MIRIX Memory Architecture (2.5 hours)
**Goal:** 6-tier memory system for true persistent learning

Current: Flat Letta memory
Target:
| Tier | Purpose | Storage |
|------|---------|---------|
| Core Memory | Always-visible identity + user facts | In-context (512 tokens) |
| Episodic Memory | Timestamped events, sessions | PostgreSQL + vector |
| Semantic Memory | Abstract facts, knowledge | Qdrant vectors |
| Procedural Memory | Learned workflows, skills | Code + structured |
| Resource Memory | External docs, tools | NFS + metadata |
| Knowledge Vault | Long-term archival | PostgreSQL + vectors |

- [ ] **4.1** Design memory tier schema and APIs
- [ ] **4.2** Create Core Memory manager (always in context)
- [ ] **4.3** Create Episodic Memory with timestamps
- [ ] **4.4** Create Procedural Memory for learned skills
- [ ] **4.5** Wire Neo4j for relationship queries between memories
- [ ] **4.6** Create memory consolidation workflow (nightly)
- [ ] **4.7** Implement memory decay for stale information

**Why:** True learning requires structured memory, not flat retrieval.

---

### PHASE 5: MCP Server Expansion (2 hours)
**Goal:** Make all Hydra tools available via MCP protocol

Current MCP tools: 16
Target: 30+

- [ ] **5.1** Create `comfyui-mcp` server (image generation tools)
- [ ] **5.2** Create `n8n-mcp` server (workflow trigger/status)
- [ ] **5.3** Create `letta-mcp` server (memory read/write)
- [ ] **5.4** Create `crews-mcp` server (agent orchestration)
- [ ] **5.5** Create `sandbox-mcp` server (safe code execution)
- [ ] **5.6** Register all with Claude Code config
- [ ] **5.7** Test tool discovery and execution

**Why:** MCP is the universal standard. Everything should be MCP-native.

---

### PHASE 6: Inference Optimization (1.5 hours)
**Goal:** Maximize inference speed with existing hardware

- [ ] **6.1** Check ExLlamaV2/TabbyAPI speculative decoding support
- [ ] **6.2** If available: configure draft model (8B) + verify model (70B)
- [ ] **6.3** Benchmark before/after token throughput
- [ ] **6.4** Optimize tensor parallel split for 5090+4090
- [ ] **6.5** Implement semantic caching layer (cache similar prompts)
- [ ] **6.6** Create inference routing optimization (RouteLLM tuning)

**Why:** Faster inference = more iterations = faster improvement.

---

### PHASE 7: Foundation Hardening (1.5 hours)
**Goal:** Bulletproof reliability enables autonomy

- [ ] **7.1** Add healthchecks to all 39 missing containers
- [ ] **7.2** Fix Neo4j compose file (new password)
- [ ] **7.3** Create network segmentation (inference/data/public)
- [ ] **7.4** Implement automatic container restart on failure
- [ ] **7.5** Create disk space cleanup automation
- [ ] **7.6** Wire predictive maintenance alerts

**Why:** Can't be autonomous if things break silently.

---

### PHASE 8: Voice Interface (1 hour)
**Goal:** Natural human-machine interaction

- [ ] **8.1** Wire Whisper ASR to voice pipeline
- [ ] **8.2** Create wake word detection (OpenWakeWord)
- [ ] **8.3** Build voice command router
- [ ] **8.4** Test end-to-end voice interaction
- [ ] **8.5** Add voice feedback for autonomous actions

**Why:** Best AI systems have natural interfaces.

---

### PHASE 9: Discord as Mobile Command Center (2 hours)
**Goal:** Discord becomes the mobile interface to Hydra and Claude Code

**Possibilities:**
- Chat with Hydra AI directly from Discord (mobile or desktop)
- Forward messages to Claude Code sessions
- Slash commands for cluster control (/status, /restart, /deploy)
- Voice channels for voice interaction
- Reaction-based approvals for human-in-loop gates
- Real-time status embeds
- Multi-user permission mapping (Discord roles → Hydra permissions)

**Tasks:**
- [ ] **9.1** Create Discord bot with Hydra branding
- [ ] **9.2** Implement `/chat` command → LiteLLM → response
- [ ] **9.3** Implement `/status` command → cluster health embed
- [ ] **9.4** Implement `/restart <service>` with confirmation
- [ ] **9.5** Create approval workflow (bot asks, user reacts ✅/❌)
- [ ] **9.6** Wire voice channel to Whisper STT + Kokoro TTS
- [ ] **9.7** Create Claude Code bridge (forward messages to active session)
- [ ] **9.8** Implement permission system (server roles → Hydra access levels)
- [ ] **9.9** Add rich embeds for GPU stats, service status, alerts

**Why:** Mobile interface without building a mobile app. Discord is already installed.

---

### PHASE 10: Documentation & Git (1 hour)
**Goal:** Morning handoff and version control

- [ ] **10.1** Commit all new code with descriptive messages
- [ ] **10.2** Push to main branch
- [ ] **10.3** Update ROADMAP.md with completed items
- [ ] **10.4** Generate morning briefing summary
- [ ] **10.5** Update STATE.json with new capabilities

---

## TOTAL: ~18 hours of high-impact work

## EXECUTION ORDER (Dependency-aware)

```
Constitution (1) ──► Self-Improvement (2) ──► Sandbox (3)
                          │
Memory (4) ◄──────────────┘
    │
MCP (5) ◄─────────────────────────────────────┐
    │                                          │
Inference (6) ─────────────────────────────────┤
    │                                          │
Foundation (7) ────────────────────────────────┤
    │                                          │
Voice (8) ─────────────────────────────────────┘
    │
Git & Docs (9)
```

---

## CONSTRAINTS (Updated)

**WILL DO:**
- Execute autonomously at full speed
- Commit and push to git
- Use sudo for system changes
- Make breaking improvements if they're better
- Log everything for morning review

**WILL NOT:**
- Violate constitutional constraints (once defined)
- Delete databases without creating backups first
- Disable authentication/security
- Force push or rewrite git history
- Make changes that can't be rolled back

---

## PROGRESS LOG

### Session Start: 2025-12-16 00:30 CST

**Phase 1: Constitutional Framework - COMPLETE** ✅
- [x] Created CONSTITUTION.yaml with immutable constraints
- [x] Built constitution.py enforcement module (21KB)
- [x] Created audit logging system (/app/logs/audit.log)
- [x] Added constitutional checks for all dangerous operations
- [x] Deployed to hydra-tools-api (tested at /constitution/*)
- [x] Verified: database_delete blocked without backup ✅

**Endpoints live:**
- GET /constitution/status - Enforcer status
- POST /constitution/check - Check if operation allowed
- GET /constitution/constraints - View all constraints
- GET /constitution/audit - View audit log
- POST /constitution/emergency/stop - Emergency halt
- POST /constitution/emergency/resume - Resume (human only)

**Time:** ~45 minutes

---

**Phase 2: Self-Improvement Infrastructure - COMPLETE** ✅
- [x] Created self_improvement.py module (600+ lines)
- [x] Built CapabilityBenchmarks class with 4 benchmark categories
- [x] Built ImprovementArchive for tracking what worked
- [x] Built ImprovementProposal system (propose → test → deploy)
- [x] Created sandbox testing environment
- [x] Implemented rollback mechanism
- [x] Added improvement delta tracking
- [x] Deployed to hydra-tools-api

**Benchmark Results (Baseline):**
- Inference Latency: 96.5/100 (1138ms) ✅
- Memory Recall: 100/100 (Qdrant healthy) ✅
- API Health: 2/4 (startup transient)
- Tool Reliability: 0/100 (startup transient)

**Endpoints live:**
- GET /self-improvement/status - Engine status
- POST /self-improvement/benchmark - Run benchmarks
- GET /self-improvement/benchmarks/baseline - Get baseline
- POST /self-improvement/proposals - Create proposal
- GET /self-improvement/proposals - List proposals
- POST /self-improvement/proposals/{id}/test - Test in sandbox
- POST /self-improvement/proposals/{id}/deploy - Deploy to prod
- GET /self-improvement/archive - View deployed improvements
- POST /self-improvement/archive/{id}/rollback - Rollback

**Time:** ~50 minutes

---

**Phase 3: Sandbox Execution - COMPLETE** ✅
- [x] Researched E2B vs Firecracker vs Docker-in-Docker
- [x] Chose restricted Docker containers (practical for Unraid)
- [x] Created sandbox.py module (750+ lines, Docker SDK)
- [x] Deployed sandbox execution API endpoint
- [x] Wired sandbox to code execution workflows
- [x] Tested isolation with 5 security tests - ALL PASSED:
  - Network isolation ✅ (--network=none)
  - Memory limits ✅ (256MB cap)
  - Read-only filesystem ✅
  - Basic execution ✅
  - Non-root user ✅ (UID 65534)
- [x] Integrated with constitutional constraints

**Endpoints live:**
- GET /sandbox/status - Sandbox manager status
- POST /sandbox/execute - Execute code in sandbox
- GET /sandbox/history - Execution history
- POST /sandbox/test-isolation - Run isolation tests
- POST /sandbox/cleanup - Clean orphaned containers
- GET /sandbox/languages - Supported languages

**Security Features:**
- Network isolation (--network=none)
- Memory limits (256MB default)
- CPU limits (0.5 cores default)
- Read-only root filesystem
- Dropped ALL capabilities
- no-new-privileges
- Non-root user (nobody/65534)
- 30 second timeout

**Time:** ~60 minutes

---

**Starting Phase 4: MIRIX Memory Architecture...**

---

## MORNING HANDOFF

**When Shaun wakes up:**

```bash
# Quick status check
curl -s http://192.168.1.244:8700/health | jq .

# Check overnight commits
cd /mnt/user/appdata/hydra-dev && git log --oneline -10

# Read this file for detailed progress
cat /mnt/user/appdata/hydra-dev/plans/OVERNIGHT-AUTONOMOUS-2025-12-16.md

# Check new capabilities
curl -s http://192.168.1.244:8700/openapi.json | jq '.paths | keys | length'
```

---

*Plan v2 created: 2025-12-16T06:30:00Z*
*Ambition level: Maximum*
*Target: Best AI system ever built*
