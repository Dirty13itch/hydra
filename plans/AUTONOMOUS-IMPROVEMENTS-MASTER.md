# HYDRA AUTONOMOUS IMPROVEMENTS MASTER LIST
## Continuous Development Backlog
### Generated: 2025-12-16T22:40:00Z by Claude Code (Opus 4.5)

---

## EXECUTIVE SUMMARY

This is the comprehensive list of improvements that can be executed autonomously to enhance Hydra. Items are prioritized by impact and organized by category. Claude Code should work through these systematically during autonomous sessions.

**Current System Health:** 100%
**Architecture Score:** 96/100
**Benchmark Score:** 93.4%

---

## TIER 1: HIGH IMPACT - EXECUTE IMMEDIATELY

### 1.1 Enable Wake Word Detection
**Impact:** HIGH | **Effort:** 5 min | **Status:** READY
```bash
curl -X POST http://192.168.1.244:8700/voice/wake/start
```
Wake word infrastructure exists but is disabled. Enable it.

---

### 1.2 Seed Knowledge Base from knowledge/*.md
**Impact:** HIGH | **Effort:** 10 min | **Status:** READY
The `hydra_knowledge` collection has 58 points but knowledge/*.md files (9 files) may not all be indexed.
```bash
# Index each knowledge file
for f in knowledge/*.md; do
  curl -X POST http://192.168.1.244:8700/ingest/document \
    -H "Content-Type: application/json" \
    -d "{\"content\":\"$(cat $f | jq -Rs .)\",\"title\":\"$(basename $f)\",\"collection\":\"hydra_knowledge\"}"
done
```

---

### 1.3 Index Source Code to code Collection
**Impact:** MEDIUM | **Effort:** 15 min | **Status:** READY
The `code` collection is empty. Index key source files for code search.
```bash
# Index Python files
find src/hydra_tools -name "*.py" -exec curl -X POST http://192.168.1.244:8700/ingest/document \
  -H "Content-Type: application/json" \
  -d '{"content":"'$(cat {} | jq -Rs .)'","title":"'$(basename {})'","collection":"code"}' \;
```

---

### 1.4 Run Full Benchmark and Store Results
**Impact:** MEDIUM | **Effort:** 5 min | **Status:** READY
```bash
curl -X POST http://192.168.1.244:8700/benchmark/run -H "Content-Type: application/json" -d '{"categories":["all"]}'
```
Store in Discovery Archive for trend tracking.

---

### 1.5 Test End-to-End Voice Chat
**Impact:** HIGH | **Effort:** 10 min | **Status:** READY
```bash
# Test full voice pipeline
curl -X POST http://192.168.1.244:8700/voice/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello Hydra, what is your current status?","voice":"af_bella"}'
```

---

## TIER 2: MEDIUM IMPACT - THIS SESSION

### 2.1 Create character_creation_agent Handler
**Impact:** HIGH | **Effort:** 30 min | **Status:** DESIGN COMPLETE
Add new agent handler to agent_scheduler.py:
- Input: Creative brief (name, archetype)
- LLM generates metadata
- ComfyUI generates portrait
- Store in Qdrant

---

### 2.2 Sync LiteLLM SpendLogs for Preference Learning
**Impact:** MEDIUM | **Effort:** 15 min | **Status:** READY
```bash
curl -X POST http://192.168.1.244:8700/preference-collector/sync-from-litellm
```
Currently 160+ interactions in SpendLogs - sync to preference learner.

---

### 2.3 Create Preference Sync n8n Workflow
**Impact:** MEDIUM | **Effort:** 20 min | **Status:** NOT STARTED
Hourly workflow to sync SpendLogs → preference learner → routing improvements.

---

### 2.4 Add Docker Healthchecks for Priority Containers
**Impact:** HIGH | **Effort:** 30 min | **Status:** BLOCKED (needs compose access)
39 containers lack healthchecks. Priority targets:
- hydra-n8n
- homeassistant
- sillytavern
- kokoro-tts

---

### 2.5 Create ComfyUI Character Portrait Workflow
**Impact:** HIGH | **Effort:** 45 min | **Status:** NOT STARTED
Build workflow for consistent character portraits:
- InstantID for face consistency
- IP-Adapter for style
- Template for Empire aesthetic

---

## TIER 3: INFRASTRUCTURE IMPROVEMENTS

### 3.1 Archive Old Session Data to Discovery Archive
**Impact:** LOW | **Effort:** 15 min | **Status:** READY
Move completed session accomplishments to discoverable archive.

---

### 3.2 Populate Empty Qdrant Collections
**Impact:** MEDIUM | **Effort:** 30 min | **Status:** READY
- `code`: Index src/hydra_tools/*.py
- `documents`: Index docs/*.md
- `multimodal`: Add reference images

---

### 3.3 Create Agent Handler for Research Tasks
**Impact:** HIGH | **Effort:** 30 min | **Status:** NOT STARTED
Add `deep_research` agent type that:
- Uses SearXNG for web search
- Crawls with Firecrawl
- Synthesizes with LLM
- Stores in knowledge base

---

### 3.4 Wire Predictive Maintenance Alerts to Discord
**Impact:** MEDIUM | **Effort:** 20 min | **Status:** READY
Connect Prometheus predicted alerts → Alertmanager → Discord.

---

### 3.5 Create Grafana Dashboard for MCP Tools
**Impact:** LOW | **Effort:** 30 min | **Status:** NOT STARTED
Track MCP tool usage, latencies, error rates.

---

## TIER 4: PHASE 12 - EMPIRE OF BROKEN QUEENS

### 4.1 Generate Character Portraits for 21 Queens
**Impact:** HIGH | **Effort:** 2 hours | **Status:** READY TO START
Use ComfyUI + characters API to generate portraits.

---

### 4.2 Create Voice Profiles for All Characters
**Impact:** MEDIUM | **Effort:** 30 min | **Status:** PARTIALLY DONE
Map remaining queens to Kokoro voices.

---

### 4.3 Build Script Parser for Dialogue Extraction
**Impact:** HIGH | **Effort:** 1 hour | **Status:** NOT STARTED
Parse Empire script markdown → structured scene data.

---

### 4.4 Create n8n Chapter Processor Workflow
**Impact:** HIGH | **Effort:** 2 hours | **Status:** NOT STARTED
Automated chapter → assets pipeline.

---

## TIER 5: ADVANCED CAPABILITIES

### 5.1 Implement Speculative Decoding
**Impact:** HIGH | **Effort:** 2 hours | **Status:** RESEARCH DONE
Requires sudo on hydra-ai to configure draft model.

---

### 5.2 Add OpenHands Integration for Code Tasks
**Impact:** HIGH | **Effort:** 3 hours | **Status:** RESEARCH NEEDED
OpenHands SDK for autonomous coding tasks.

---

### 5.3 Create Multi-Agent Crew for Content Generation
**Impact:** HIGH | **Effort:** 4 hours | **Status:** NOT STARTED
CrewAI crew for parallel content generation.

---

### 5.4 Implement DGM Self-Modification Loop
**Impact:** VERY HIGH | **Effort:** 8 hours | **Status:** FOUNDATION READY
Full Darwin Gödel Machine cycle:
- Benchmark → Analyze → Propose → Test → Deploy → Monitor

---

## QUICK WINS (< 5 min each)

| Task | Command |
|------|---------|
| Enable wake word | `curl -X POST http://192.168.1.244:8700/voice/wake/start` |
| Sync preferences | `curl -X POST http://192.168.1.244:8700/preference-collector/sync-from-litellm` |
| Trigger monitoring crew | `curl -X POST http://192.168.1.244:8700/scheduler/trigger/monitoring` |
| Run benchmark | `curl -X POST http://192.168.1.244:8700/benchmark/run` |
| Test voice chat | `curl -X POST http://192.168.1.244:8700/voice/chat -d '{"text":"test"}'` |
| Check memory status | `curl http://192.168.1.244:8700/memory/status` |
| List characters | `curl http://192.168.1.244:8700/characters/` |
| Check crew schedule | `curl http://192.168.1.244:8700/scheduler/status` |

---

## METRICS TO TRACK

| Metric | Current | Target | Notes |
|--------|---------|--------|-------|
| Benchmark Score | 93.4% | 98% | Fix remaining tests |
| Memory Entries | 28 | 500+ | Index knowledge |
| Code Collection | 0 | 100+ | Index source |
| Voice Latency | ~2s | <1s | Optimize pipeline |
| Character Portraits | 0 | 21 | Generate all queens |
| Preference Data | 160 | 1000+ | Sync regularly |
| Agent Tasks Completed | 0 | 100+ | Use scheduler |

---

## EXECUTION PRIORITY

When starting autonomous work, follow this order:

1. **Quick Wins First** - Enable features that are just disabled
2. **Data Population** - Index knowledge, code, documents
3. **Test Infrastructure** - Verify all endpoints work
4. **Build New Features** - Agent handlers, workflows
5. **Generate Assets** - Character portraits, voice profiles
6. **Optimize** - Performance tuning, advanced features

---

## HOW TO USE THIS DOCUMENT

1. Check current task progress in TODO list
2. Pick highest priority incomplete item
3. Execute and mark complete
4. Update metrics section
5. Add new discoveries to ROADMAP.md learnings
6. Continue to next item

---

*Master List Version: 1.0*
*Last Updated: 2025-12-16T22:40:00Z*
*Maintainer: Claude Code (Opus 4.5)*
