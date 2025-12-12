# HYDRA ROADMAP

> *Phased journey from homelab to autonomous AI operating system*

---

## Current Position

Based on the Phase 7 completion (infrastructure deployed), Hydra is now transitioning from **"running services"** to **"intelligent autonomy"**.

```
COMPLETED                          CURRENT                           FUTURE
─────────────────────────────────────────────────────────────────────────────
                                      │
Phase 1: Network        ████████████  │
Phase 2: Storage        ████████████  │
Phase 3: Databases      ████████████  │
Phase 4: Observability  ████████████  │
Phase 5: Inference      ████████████  │
Phase 6: Automation     ████████████  │
Phase 7: Creative       ████████████  │
Phase 8: Memory         ████████████  │
Phase 9: Agents         ████████████  │
                                      │
Phase 10: Control Plane ████████████  │
                                      │
Phase 11: Evolution     ██░░░░░░░░░░ ◄┘  ← YOU ARE HERE (15%)
```

---

## Phase 8: Memory Layer (Weeks 1-3)

**Objective:** Give Hydra persistent memory that survives sessions and accumulates knowledge.

### Week 1: Letta Deployment

- [x] **Deploy Letta on hydra-storage** ✅ COMPLETED 2025-12-10
  - Port: 8283
  - Backend: PostgreSQL with pgvector (letta-db container)
  - Version: 0.15.1

- [x] **Configure Letta → LiteLLM connection** ✅ COMPLETED 2025-12-10/12-11
  - Letta uses Ollama directly at http://192.168.1.203:11434/v1 (hydra-compute)
  - Model: qwen2.5:7b for inference (changed from mistral:7b-instruct - better tool-calling)
  - Embedding: nomic-embed-text:latest (768-dim)

- [x] **Initialize core memory blocks** ✅ COMPLETED 2025-12-10
  - Agent: **hydra-steward** (agent-b3fb1747-1a5b-4c94-b713-11d6403350bf)
  - persona: Hydra Steward identity and capabilities
  - human: Shaun's preferences and working style
  - cluster_state: Current cluster status
  - tasks: Active and completed tasks

- [x] **Test basic memory persistence** ✅ COMPLETED 2025-12-10
  - Agent persists across container restarts
  - Memory blocks stored in pgvector DB

### Week 2: Knowledge Integration

- [ ] **Deploy Graphiti/Neo4j** (if not running)
  - Store entity relationships
  - Enable temporal queries
  
- [ ] **Import existing knowledge**
  - Parse `knowledge/*.md` files into Letta archival
  - Build initial knowledge graph from infrastructure
  
- [ ] **Connect Letta to Open WebUI**
  - Create Letta function provider
  - Enable memory-aware conversations

### Week 3: Memory Workflows

- [x] **Create memory update workflow in n8n** ✅ COMPLETED 2025-12-11
  - Workflow: "Letta Memory Update" (ID: 1)
  - Webhook: http://hydra-n8n:5678/webhook/letta-memory
  - Scheduled 6-hour check + webhook triggers
  - NOTE: Activate via n8n UI at http://192.168.1.244:5678

- [x] **Implement knowledge capture** ✅ COMPLETED 2025-12-11
  - letta_memory_tools.py deployed with log_event, log_alert, log_action
  - Alertmanager configured to send to letta-memory receiver

- [x] **Test cross-session continuity** ✅ COMPLETED 2025-12-12
  - Sent PHOENIX-ALPHA project info to hydra-steward
  - Memory block created and persisted in PostgreSQL (letta-db)
  - Note: qwen2.5:7b has tool-calling format issues but memory writes succeed

**Milestone:** Conversations reference past interactions naturally.

---

## Phase 9: Agent Infrastructure (Weeks 4-6)

**Objective:** Deploy autonomous agents that can work independently on delegated tasks.

**Status:** STARTED (2025-12-10)

### Week 4: CrewAI Foundation

- [x] **Deploy CrewAI on hydra-storage** (2025-12-10)
  - Close to inference for low latency
  - Uses LiteLLM for model access
  
- [x] **Create Monitoring Crew** (2025-12-10)
  - System Monitor, Log Analyst, Health Reporter agents
  - Scheduled daily 6 AM via cron

- [x] **Create Research Crew** (2025-12-10)
  ```python
  research_crew = Crew(
    agents=[
      Agent(role="Web Researcher", goal="Find current information"),
      Agent(role="Synthesizer", goal="Combine findings"),
      Agent(role="Reporter", goal="Write clear summaries")
    ],
    tools=[SearXNG, Firecrawl, WebScraper]
  )
  ```

### Week 5: Crew Integration

- [x] **Connect CrewAI to n8n** (2025-12-10)
  - CrewAI API exposed on :8500
  - Endpoints: /run/monitoring, /run/research, /health
  - n8n triggers crew execution
  - Crew results flow back to n8n
  
- [x] **Create overnight research workflow** (2025-12-10)
  - Cron schedules: Monitoring daily 6AM, Research Mon 2AM, Maintenance Sun 3AM
  ```
  Trigger: 2 AM cron
  → Check Letta for pending research tasks
  → Execute research crew
  → Store results in Qdrant
  → Update Letta with summary
  → Morning notification with findings
  ```

- [x] **Create maintenance crew** (2025-12-10)
  - Container Inspector, Storage Analyst, Maintenance Planner agents
  - Scheduled weekly Sunday 3AM
  - Scheduled health checks
  - Proactive issue identification
  - Automated remediation suggestions

### Week 6: Agent Autonomy

- [x] **Implement agent memory integration** ✅ COMPLETED 2025-12-11
  - letta_memory_tools.py provides LettaMemory class
  - Methods: add_memory, query_memory, log_event, log_alert, log_action
  - Deployed to /mnt/user/appdata/hydra-stack/scripts/

- [x] **Create escalation protocols** ✅ COMPLETED 2025-12-11
  - escalation_protocols.py with EscalationEngine class
  - Confidence scoring with context modifiers (time, failures, cluster health)
  - Thresholds: auto_threshold, confirm_threshold
  - Default rules: container restarts, scaling, cache clearing, security alerts
  - Deployed to /mnt/user/appdata/hydra-stack/scripts/

- [ ] **Test autonomous operation**
  - Queue research task before bed
  - Verify completion and quality in morning

**Milestone:** Research tasks execute overnight without intervention.

---

## Phase 10: Conversational Control Plane (Weeks 7-9)

**Objective:** Replace dashboards with natural language infrastructure control.

**Status:** COMPLETED (100% - 2025-12-12)

### Week 7: MCP Server Development

- [x] **Create Hydra MCP Server** ✅ COMPLETED 2025-12-11
  - Port: 8600
  - Endpoints: /health, /cluster/status, /metrics, /metrics/summary, /metrics/nodes
  - Endpoints: /knowledge/search, /inference/models, /inference/complete
  - Endpoints: /services/status, /letta/message, /letta/memory, /crews/run/{name}

- [x] **Add Prometheus metrics** ✅ COMPLETED 2025-12-11
  - /metrics endpoint with Prometheus format
  - Scrape targets: hydra-mcp:8600, hydra-crewai:8500
  - Grafana "MCP Control Plane" dashboard created

- [x] **Implement safety layer** ✅ COMPLETED 2025-12-11
  - Confirmation tokens for protected containers (5-minute expiry)
  - Rate limiting: default 100/60s, dangerous 5/60s, inference 20/60s
  - Audit logging with in-memory 1000 entry log
  - Container management: /containers/list, /containers/restart, /containers/{name}/logs
  - Safety endpoints: /audit/log, /safety/pending, /safety/protected

- [x] **Connect to Claude Desktop/Code** ✅ COMPLETED 2025-12-11/12-12
  - MCP protocol proxy: `mcp/hydra_mcp_proxy.py`
  - Project config: `.mcp.json` with hydra server definition
  - 16 tools: cluster_status, services_status, metrics, containers, letta, knowledge, crews
  - Test: `echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | python mcp/hydra_mcp_proxy.py`

### Week 8: Hydra Control Plane UI

- [x] **Initialize UI project** ✅ COMPLETED
  - React/Next.js foundation on port 3200
  - Cyberpunk terminal aesthetic (per VISUAL-DESIGN-SPEC)

- [x] **Implement core components** ✅ COMPLETED
  - Node status cards with GPU metrics
  - Service status panels
  - Container list with actions
  - Storage pools visualization
  - Alerts panel

- [x] **Add conversational interface** ✅ COMPLETED 2025-12-11
  - LettaChat component (bottom-right chat bubble)
  - hydra-steward agent integration
  - Message history with reasoning display
  - Error handling for LLM failures

- [x] **Add AI Crews panel** ✅ COMPLETED 2025-12-12
  - CrewStatusPanel component
  - Displays monitoring, research, maintenance crews
  - "Run Now" button for manual crew triggers
  - Real-time status updates from CrewAI API

### Week 9: Integration

- [x] **Connect UI to backend services** ✅ COMPLETED 2025-12-12
  - REST API with 5-second polling for real-time updates
  - MCP Server integration for all operations
  - LettaChat component for conversational interface

- [ ] **Implement voice interface** (optional)
  - Whisper for speech-to-text
  - Kokoro for text-to-speech
  - Wake word detection

**Milestone:** Control Hydra through conversation, not buttons. ✅ ACHIEVED

---

## Phase 11: Evolution & Self-Improvement (Weeks 10-12)

**Objective:** Hydra becomes self-improving through feedback loops.

### Week 10: Documentation Synchronization

- [x] **Create STATE.json auto-update** ✅ COMPLETED 2025-12-12
  - Script: `scripts/generate_state.py`
  - Queries MCP server, Ollama, Letta for cluster state
  - Uses only Python built-in modules (no external deps)
  - Run: `python scripts/generate_state.py > STATE.json`
  - STATE.json reflects reality
  - Claude Code reads accurate state at session start
  
- [ ] **Implement LEARNINGS.md capture**
  - After significant sessions, log insights
  - These inform future sessions
  
- [ ] **Create knowledge refresh workflow**
  - Periodically verify knowledge/*.md accuracy
  - Flag outdated information

### Week 11: Feedback Loops

- [ ] **Implement preference learning**
  - Track corrections and preferences
  - Update Letta human block automatically
  
- [ ] **Create capability expansion**
  - When encountering new requirements, document them
  - Prioritize implementation in roadmap
  
- [ ] **Implement self-diagnosis**
  - Agent analyzes own failures
  - Suggests improvements

### Week 12: Optimization

- [ ] **Inference optimization**
  - Implement RouteLLM for dynamic routing
  - Add speculative decoding with draft models
  
- [ ] **Resource optimization**
  - Analyze GPU utilization patterns
  - Adjust model loading for efficiency
  
- [ ] **Knowledge optimization**
  - Prune outdated archival memory
  - Consolidate redundant knowledge

**Milestone:** Hydra measurably improves between sessions.

---

## Future Phases (Beyond Week 12)

### Phase 12: Empire of Broken Queens Production
- Full character consistency pipeline
- Automated chapter asset generation
- Quality feedback loops

### Phase 13: Home Automation Integration
- Home Assistant connection
- Presence-aware operations
- Voice control throughout home

### Phase 14: External Intelligence
- API integrations (calendar, email, etc.)
- Proactive notifications
- Cross-platform awareness

### Phase 15: Multi-User Support
- Separate memory contexts
- Shared vs private knowledge
- Collaboration features

---

## Success Criteria by Phase

| Phase | Success Criteria |
|-------|------------------|
| 8 | Memory persists across sessions; past context recalled naturally |
| 9 | Research tasks complete overnight; findings available in morning |
| 10 | Infrastructure controlled via conversation; UI provides visibility |
| 11 | Documentation stays accurate; system measurably improves |

---

## Task Tracking

### Immediate (This Week)
- [x] Deploy Letta container ✅
- [x] Initialize core memory blocks ✅
- [x] Test memory persistence ✅
- [x] Deploy Neo4j for knowledge graph ✅
- [x] Import knowledge files to Letta archival ✅ (9 files - 2025-12-11)
- [ ] Connect Letta to Open WebUI (manual)
- [ ] Activate n8n workflow via UI (http://192.168.1.244:5678)
- [x] Fix Letta LLM model ✅ (2025-12-11 - Changed from mistral:7b-instruct to qwen2.5:7b)

### Short-term (This Month)
- [ ] Complete Phase 8 (Memory Layer)
- [ ] Begin Phase 9 (Agent Infrastructure)
- [ ] Create monitoring crew

### Medium-term (This Quarter)
- [ ] Complete through Phase 11
- [ ] Hydra Control Plane UI functional
- [ ] Self-improving documentation

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Letta instability | Memory loss | PostgreSQL backups, test thoroughly |
| Agent loops | Resource exhaustion | Rate limits, max iterations, human escalation |
| NixOS rebuild failure | Node down | Always have rollback plan, test in hydra-dev first |
| Model compatibility | Inference broken | Keep previous working model, test new models offline |

---

## How Claude Code Should Use This Document

1. **At session start**: Check current phase and immediate tasks
2. **When choosing work**: Prioritize tasks aligned with current phase
3. **After completing tasks**: Update task checkboxes, move to next
4. **When blocked**: Check risk mitigation, escalate if needed
5. **At session end**: Note progress for next session

---

*This document is the implementation plan. For the "why", see VISION.md.*
*For technical details, see ARCHITECTURE.md.*
*Last updated: December 2025*
