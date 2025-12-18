# HYDRA AUTONOMOUS WORK QUEUE
## Comprehensive Backlog for 24/7 Operation
### Generated: 2025-12-18T01:45:00Z by Claude Code (Opus 4.5)

---

## SYSTEM OVERVIEW

| Metric | Value |
|--------|-------|
| API Endpoints | 439 |
| Python Modules | 72 |
| Lines of Code | 41,443 |
| Containers Running | 70 |
| Prometheus Targets Down | 0 |
| Architecture Score | 99/100 |
| Benchmark Score | 96.5% |
| Phase 12 Completion | 98% |
| Scene Generator | ✅ COMPLETE |
| Model Hot-Swap API | ✅ COMPLETE |
| Human Feedback API | ✅ COMPLETE |
| Daily Digest API | ✅ COMPLETE |

---

## TIER 1: IMMEDIATE AUTONOMOUS WORK (No User Input Required)

### 1.1 Fix Memory Status Endpoint
**Priority:** HIGH | **Effort:** 30 min | **Impact:** Core functionality
**Problem:** `/memory/status` returns null values
**Location:** `src/hydra_tools/memory_architecture.py`
**Task:** Debug and fix the status endpoint to return actual memory counts

### 1.2 Implement Alertmanager Silence Integration
**Priority:** MEDIUM | **Effort:** 1 hr | **Impact:** Alert management
**Problem:** Silence endpoint is a placeholder (alerts_api.py:328)
**Task:** Wire actual Alertmanager API for alert silencing

### 1.3 Wire SSE Events to Real Data Sources
**Priority:** HIGH | **Effort:** 2 hr | **Impact:** Real-time monitoring
**Problem:** events.py has TODO items at lines 139, 186, 200, 249
**Tasks:**
- Integrate container updates with Docker API
- Integrate GPU metrics with actual Prometheus queries
- Wire agent scheduler events to SSE stream

### 1.4 Implement Benchmark Results Persistence
**Priority:** MEDIUM | **Effort:** 1 hr | **Impact:** Self-improvement tracking
**Problem:** benchmark_suite.py:653 - latest results is placeholder
**Task:** Store benchmark results in SQLite/Qdrant for historical tracking

### 1.5 Complete Reconcile API Persistence
**Priority:** LOW | **Effort:** 1 hr | **Impact:** State management
**Problem:** reconcile_api.py:505,520 - placeholders for file/db storage
**Task:** Implement YAML/JSON persistence for desired state

### 1.6 Wire Presence Automation to SSH
**Priority:** LOW | **Effort:** 2 hr | **Impact:** Presence features
**Problem:** presence_automation.py:208 - placeholder for SSH to nodes
**Task:** Implement actual SSH commands for GPU eco mode switching

### 1.7 Implement Container Remediation Audit Log
**Priority:** MEDIUM | **Effort:** 30 min | **Impact:** Audit trail
**Problem:** container_health.py:448 - placeholder for audit log
**Task:** Wire to activity API for remediation tracking

---

## TIER 2: FEATURE ENHANCEMENTS (Can Build Autonomously)

### 2.1 Add Maintenance Work Type Handler
**Priority:** HIGH | **Effort:** 1 hr | **Impact:** Autonomous operations
**Problem:** Maintenance tasks return "no_processor"
**Location:** `autonomous_queue.py`
**Task:** Implement `process_maintenance()` calling cleanup scripts

### 2.2 Create Inference Work Type Handler
**Priority:** MEDIUM | **Effort:** 1 hr | **Impact:** Queue inference jobs
**Location:** `autonomous_queue.py`
**Task:** Implement `process_inference()` for batch LLM tasks

### 2.3 Build Model Hot-Swap API ✅ COMPLETE
**Priority:** MEDIUM | **Effort:** 2 hr | **Impact:** Model flexibility
**Status:** IMPLEMENTED - src/hydra_tools/model_hotswap.py
**Endpoints:**
- `GET /models/available` - List EXL2 and Ollama models
- `GET /models/loaded` - Current model status across all backends
- `GET /models/status` - Comprehensive status with backend info
- `POST /models/load` - Load a model on TabbyAPI/Ollama
- `POST /models/unload` - Unload current model
- `POST /models/switch` - Atomic unload/load switch

### 2.4 Create Background Scene Generator ✅ COMPLETE
**Priority:** HIGH | **Effort:** 3 hr | **Impact:** Empire pipeline
**Status:** IMPLEMENTED - src/hydra_tools/scene_backgrounds.py (717 lines)
**Completed:**
- 18 location definitions with architectural styles
- Time/weather/mood modifiers
- ComfyUI integration tested and working
- API endpoints: /scenes/generate, /scenes/locations, /scenes/modifiers

### 2.5 Implement Human Feedback Collection API ✅ COMPLETE
**Priority:** MEDIUM | **Effort:** 2 hr | **Impact:** Learning loop
**Status:** IMPLEMENTED - src/hydra_tools/human_feedback.py
**Endpoints:**
- `POST /feedback/asset` - Rate generated assets (images, audio)
- `POST /feedback/generation` - Rate text generations
- `POST /feedback/comparison` - A/B preference testing
- `GET /feedback/stats` - Feedback statistics and trends
- `GET /feedback/by-model` - Stats grouped by model
- `GET /feedback/pending` - Assets needing regeneration

### 2.6 Build Daily Digest Generator ✅ COMPLETE
**Priority:** LOW | **Effort:** 1 hr | **Impact:** Awareness
**Status:** IMPLEMENTED - src/hydra_tools/daily_digest.py
**Endpoints:**
- `GET /digest/daily` - Full 24h digest with all sections
- `GET /digest/overnight` - 8h overnight summary
- `GET /digest/weekly` - Weekly summary
- `GET /digest/quick` - One-line status summary
- `GET /digest/trends` - Performance trends from Prometheus
- `POST /digest/send` - Generate and send to Discord

### 2.7 Create Test Scaffolding
**Priority:** LOW | **Effort:** 2 hr | **Impact:** Code quality
**Current tests:** 13 files
**Task:** Generate test stubs for all major modules

---

## TIER 3: RESEARCH & OPTIMIZATION (Queue via CrewAI)

### 3.1 Research: ExLlamaV3 Migration Path
**Priority:** LOW | **Effort:** Research task
**Topic:** Evaluate ExLlamaV3 tensor parallelism for 5090+4090
**Task:** Queue research task to CrewAI

### 3.2 Research: MCP Server Registry Integration
**Priority:** LOW | **Effort:** Research task
**Topic:** Official MCP servers from Linux Foundation registry
**Task:** Evaluate which servers to add (postgres, docker, github)

### 3.3 Research: LangGraph for Agent Orchestration
**Priority:** LOW | **Effort:** Research task
**Topic:** LangGraph vs current CrewAI architecture
**Task:** Compare orchestration patterns

### 3.4 Optimize: Semantic Cache Hit Rate
**Priority:** MEDIUM | **Effort:** 2 hr
**Current:** semantic_cache.py exists
**Task:** Analyze cache performance, tune similarity thresholds

### 3.5 Optimize: Inference Latency Baseline
**Priority:** MEDIUM | **Effort:** 1 hr
**Task:** Run comprehensive latency benchmarks across models

### 3.6 Optimize: Docker Image Cleanup
**Priority:** LOW | **Effort:** 30 min
**Task:** Prune unused images, analyze disk usage by container

---

## TIER 4: DOCUMENTATION & KNOWLEDGE

### 4.1 Update Knowledge Files
**Priority:** LOW | **Effort:** Ongoing
**Current files:** 18 knowledge/*.md files
**Tasks:**
- Audit for outdated information
- Add new Phase 12 documentation
- Document 439 API endpoints

### 4.2 Generate API Documentation
**Priority:** MEDIUM | **Effort:** 1 hr
**Task:** Auto-generate markdown docs from OpenAPI spec

### 4.3 Create Troubleshooting Guide
**Priority:** LOW | **Effort:** 2 hr
**Task:** Document common issues and solutions

### 4.4 Update STATE.json
**Priority:** HIGH | **Effort:** 30 min
**Task:** Add session summary with completed tasks

---

## TIER 5: INTEGRATION IMPROVEMENTS

### 5.1 Wire Discord Notifications to All Handlers
**Priority:** BLOCKED (needs webhook URL)
**Task:** When URL available, add Discord notifications to:
- Chapter generation completion
- Research task completion
- Asset generation completion
- Quality scoring results
- Benchmark results

### 5.2 Wire Home Assistant Presence Detection
**Priority:** BLOCKED (needs HA_TOKEN)
**Task:** When token available, implement:
- Arrive/leave detection
- GPU power mode switching
- Morning briefing triggers

### 5.3 Improve n8n Workflow Robustness
**Priority:** MEDIUM | **Effort:** 2 hr
**Current workflows:** 19 (17 active)
**Tasks:**
- Add error handling to all workflows
- Add retry logic for failed requests
- Add notification on failures

---

## TIER 6: QUALITY & TESTING

### 6.1 Run Full Benchmark Suite
**Priority:** HIGH | **Effort:** 10 min
**Command:** `POST /self-improvement/benchmarks/run`
**Task:** Establish fresh baseline scores

### 6.2 Test Character Portrait Pipeline
**Priority:** HIGH | **Effort:** 20 min
**Task:** Queue portrait generation for test character

### 6.3 Test Voice Pipeline End-to-End
**Priority:** MEDIUM | **Effort:** 10 min
**Task:** Test `/voice/chat` with sample prompt

### 6.4 Test Agentic RAG Pipeline
**Priority:** MEDIUM | **Effort:** 10 min
**Task:** Test `/search/hybrid` with knowledge query

### 6.5 Validate All 22 Character References
**Priority:** LOW | **Effort:** 20 min
**Task:** Check all reference images are accessible

---

## TIER 7: CREATIVE PIPELINE (Empire of Broken Queens)

### 7.1 Generate Test Chapter Structure
**Priority:** MEDIUM | **Effort:** 30 min
**Task:** Create Chapter 1 structure with `/characters/create-chapter-structure`

### 7.2 Test TTS Generation for All Queens
**Priority:** MEDIUM | **Effort:** 1 hr
**Task:** Generate sample dialogue for all 22 characters

### 7.3 Create Expression Variations
**Priority:** LOW | **Effort:** 2 hr
**Task:** Generate multiple expressions per character for visual novel

### 7.4 Build Scene Transition Library
**Priority:** LOW | **Effort:** 2 hr
**Task:** Create standard transitions for Ren'Py

### 7.5 Create Music Cue Database
**Priority:** LOW | **Effort:** 1 hr
**Task:** Catalog background music for scene types

---

## EXECUTION ORDER (Recommended)

### Phase A: Immediate Fixes (Next 2 hours)
1. Fix memory status endpoint
2. Wire SSE events to real data
3. Implement maintenance handler
4. Update STATE.json with session

### Phase B: Core Enhancements (Hours 3-6)
5. Run full benchmark suite
6. Implement benchmark persistence
7. Test character pipeline
8. Build background generator

### Phase C: Research Queue (Queue for overnight)
9. Queue ExLlamaV3 research
10. Queue MCP server research
11. Queue semantic cache optimization

### Phase D: Documentation (Low priority, fill gaps)
12. Generate API documentation
13. Update knowledge files
14. Create troubleshooting guide

---

## AUTONOMOUS EXECUTION NOTES

### What I Can Do Without User Input:
- All Tier 1 items (code fixes)
- All Tier 2 items (new features)
- All Tier 3 research (queue to CrewAI)
- All Tier 4 documentation
- Most Tier 6 testing
- All Tier 7 creative pipeline

### What Requires User Input:
- Tier 5.1: Discord webhook URL
- Tier 5.2: Home Assistant token
- Any changes to production docker-compose
- Git push to remote repository
- Changes to NixOS configuration

### Continuous Work Protocol:
1. Pick highest priority item from available tiers
2. Execute to completion
3. Update STATE.json or relevant docs
4. Move to next item
5. Queue research tasks for overnight processing
6. Report significant completions

---

*This document is the autonomous work backlog. Update as tasks complete.*
*Next review: After completing Phase A items*
