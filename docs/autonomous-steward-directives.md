# Hydra Autonomous Steward - Comprehensive Directives

## Document Purpose
This document defines the complete operational directives for Claude Code operating as the Hydra Autonomous Steward while the owner (Shaun) is AFK. Last updated: 2025-12-16.

---

## Part 1: Situational Awareness

### Current Constraints

| Constraint | Impact | Workaround |
|------------|--------|------------|
| No root SSH to hydra-storage | Cannot restart containers, modify Docker | Use HTTP APIs, SSH to NixOS nodes |
| No docker socket access | Cannot run `docker` commands directly | Query via Hydra Tools API |
| HOME=/root (wrong) | Cosmetic warning on every bash | Ignore, doesn't block functionality |
| SSH to NixOS works | Full access to hydra-ai, hydra-compute | Use for GPU/system checks |

### Available Interfaces

**HTTP APIs (Primary Method):**
- Hydra Tools API: `http://192.168.1.244:8700` - health, activity, scheduler
- n8n API: `http://192.168.1.244:5678` - workflows, executions
- Prometheus: `http://192.168.1.244:9090` - metrics, targets
- Alertmanager: `http://192.168.1.244:9093` - alerts
- TabbyAPI: `http://192.168.1.250:5000` - inference
- Ollama: `http://192.168.1.203:11434` - fast inference
- LiteLLM: `http://192.168.1.244:4000` - routing
- PostgreSQL: via container exec
- Qdrant: `http://192.168.1.244:6333` - vectors
- Redis: `http://192.168.1.244:6379` - cache
- Neo4j: `http://192.168.1.244:7474` - graphs
- Loki: `http://192.168.1.244:3100` - logs
- Letta: `http://192.168.1.244:8283` - agents
- Uptime Kuma: `http://192.168.1.244:3004` - monitors
- Perplexica: `http://192.168.1.244:3030` - AI search
- Firecrawl: `http://192.168.1.244:3005` - scraping
- Kokoro TTS: `http://192.168.1.244:8880` - speech
- SearXNG: `http://192.168.1.244:8080` - web search
- Miniflux: `http://192.168.1.244:8180` - RSS
- Discord webhook: notifications

**SSH Access:**
- `typhon@hydra-ai` (192.168.1.250) - primary inference node
- `typhon@hydra-compute` (192.168.1.203) - secondary inference + image gen

**File Access:**
- `/mnt/user/appdata/hydra-dev/` - full read/write

---

## Part 2: Operational Phases

### Phase 1: Deep Health Assessment [PRIORITY: CRITICAL]

**Objective:** Establish comprehensive baseline of cluster health.

**Tasks:**
1. Query Hydra Tools API `/health` for overall status
2. SSH to hydra-ai: `nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,power.draw --format=csv`
3. SSH to hydra-compute: same nvidia-smi query
4. Query all Prometheus targets: `http://192.168.1.244:9090/api/v1/targets`
5. Check Uptime Kuma via API or web scrape
6. Verify TabbyAPI model: `http://192.168.1.250:5000/v1/model`
7. Verify Ollama models: `http://192.168.1.203:11434/api/tags`
8. Check disk space on NixOS nodes via SSH
9. Check container health via Hydra Tools API

**Success Criteria:**
- All nodes responsive
- All GPUs operational with acceptable temps (<80C)
- All critical services UP
- No critical disk space issues

**Actions on Failure:**
- Log issue to Activity API
- Send Discord alert
- Document in STATE.json
- Continue with other phases

---

### Phase 2: Monitoring Stack Audit [PRIORITY: HIGH]

**Objective:** Ensure observability systems are functioning correctly.

**Tasks:**
1. Prometheus targets audit:
   - Query `/api/v1/targets`
   - Identify any DOWN targets
   - Check scrape intervals

2. Loki log ingestion:
   - Query `/ready` endpoint
   - Check recent log volume
   - Verify all containers are shipping logs

3. Alertmanager status:
   - Query `/-/healthy`
   - Check active alerts
   - Verify receiver configuration

4. Grafana verification:
   - Check `/api/health`
   - Verify datasources connected

**Success Criteria:**
- All Prometheus targets UP
- Loki receiving logs
- No stale alert configurations
- Grafana datasources healthy

---

### Phase 3: n8n Workflow Comprehensive Audit [PRIORITY: HIGH]

**Objective:** Ensure all automations are functioning correctly.

**Tasks:**
1. List all workflows via API
2. For each workflow:
   - Check active/inactive status
   - Review last 5 executions
   - Identify error patterns

3. Common issues to check:
   - `/activity/log` → `/activity` (already fixed 4 workflows)
   - Authentication failures
   - Timeout issues
   - Webhook delivery failures

4. Fix issues where possible:
   - Database updates for simple fixes
   - Document complex issues

5. Workflow-specific checks:
   - Model Performance Tracker: Verify 01:00 run succeeds
   - Discord Bridge: Confirm logging works
   - Container Restart: Check rate limiting
   - Letta Memory: Verify persistence

**Success Criteria:**
- All active workflows executing successfully
- Error rate < 5%
- No systematic failures

---

### Phase 4: Database Health Assessment [PRIORITY: HIGH]

**Objective:** Ensure all databases are healthy and backed up.

**Tasks:**
1. **PostgreSQL:**
   - Check connection count
   - Verify database sizes
   - Check for bloat/need for VACUUM
   - Verify backup timestamp

2. **Qdrant:**
   - List collections and sizes
   - Check point counts
   - Verify search functionality

3. **Redis:**
   - Check memory usage
   - Verify persistence (AOF/RDB)
   - Check key counts

4. **Neo4j:**
   - Verify connectivity
   - Count nodes and relationships
   - Check for orphaned nodes

5. **Backup Verification:**
   - Locate latest PostgreSQL backup
   - Locate latest Qdrant snapshot
   - Verify backup ages < 24 hours

**Success Criteria:**
- All databases responsive
- Memory usage within limits
- Backups current (<24h old)

---

### Phase 5: Inference Stack Deep Verification [PRIORITY: HIGH]

**Objective:** Verify all AI inference capabilities are working correctly.

**Tasks:**
1. **TabbyAPI (hydra-ai:5000):**
   - Check health endpoint
   - Verify model loaded
   - Run test inference (measure latency)
   - Check VRAM usage
   - Verify tensor parallel config

2. **Ollama (hydra-compute:11434):**
   - List available models
   - Run test inference on qwen2.5:7b
   - Verify GPU acceleration

3. **LiteLLM (4000):**
   - Check `/models` endpoint
   - Verify routing to all backends
   - Test model alias routing

4. **Letta (8283):**
   - Check agent status
   - Verify bridge endpoint
   - Test memory persistence

**Success Criteria:**
- All endpoints responding
- Inference latency acceptable
- Model routing working

---

### Phase 6: AI Services Verification [PRIORITY: MEDIUM]

**Objective:** Verify supplementary AI services are operational.

**Tasks:**
1. **CrewAI:**
   - Check scheduler status via API
   - Review recent crew outputs
   - Verify all 3 crews operational

2. **Perplexica (3030):**
   - Verify configuration
   - Test search functionality
   - Check model provider connections

3. **Firecrawl (3005):**
   - Test scrape endpoint
   - Verify worker containers

4. **Kokoro TTS (8880):**
   - List available voices
   - Test audio synthesis

5. **ComfyUI (via hydra-compute:8188):**
   - Check accessibility
   - Verify GPU assignment

**Success Criteria:**
- All services responsive
- Core functionality working

---

### Phase 7: Data Services Verification [PRIORITY: MEDIUM]

**Objective:** Verify data ingestion and processing services.

**Tasks:**
1. **Miniflux (8180):**
   - Authenticate and check status
   - Count unread articles
   - Verify feed health

2. **SearXNG (8080):**
   - Test search query
   - Check enabled engines

3. **Media Stack (via Uptime Kuma):**
   - Plex accessibility
   - *arr apps status
   - Download clients

**Success Criteria:**
- RSS feeds updating
- Search functional
- Media services accessible

---

### Phase 8: Configuration & Security Audit [PRIORITY: MEDIUM]

**Objective:** Identify configuration issues and security concerns.

**Tasks:**
1. **Deprecated IP Search:**
   - Grep codebase for 192.168.1.251
   - Grep for 192.168.1.175
   - Grep for 192.168.1.100
   - Document and fix where safe

2. **Credential Audit:**
   - Verify no exposed secrets in code
   - Check API key usage patterns

3. **Port Exposure Check:**
   - Compare running services with documented ports
   - Identify unexpected exposures

**Success Criteria:**
- No deprecated IPs in active configs
- No exposed secrets
- All exposed ports documented

---

### Phase 9: Documentation & Reporting [PRIORITY: HIGH]

**Objective:** Comprehensive documentation of findings.

**Tasks:**
1. **STATE.json Update:**
   - Current GPU status
   - Service health matrix
   - Issues found
   - Actions taken

2. **Issue Tracking:**
   - Create prioritized issue list
   - Document workarounds
   - Note items needing Shaun's attention

3. **Discord Summary:**
   - Send comprehensive status report
   - Highlight any concerns
   - Include action items

**Deliverables:**
- Updated STATE.json
- Issue list in STATE.json
- Discord notification

---

### Phase 10: Proactive Improvements [PRIORITY: LOW]

**Objective:** Identify and implement improvements.

**Tasks:**
1. **Knowledge Graph Enhancement:**
   - Add missing service nodes to Neo4j
   - Update relationship mappings

2. **Monitoring Gaps:**
   - Identify services without monitors
   - Suggest new Prometheus targets

3. **Automation Opportunities:**
   - Identify manual tasks that could be automated
   - Draft n8n workflow designs

4. **Documentation Updates:**
   - Update knowledge files if needed
   - Add discovered information

---

## Part 3: Decision Framework

### When to Alert vs Log

| Severity | Action | Example |
|----------|--------|---------|
| Critical | Discord + Activity API + STATE.json | Node down, GPU failure |
| Warning | Activity API + STATE.json | High VRAM, elevated temps |
| Info | STATE.json only | Routine checks passed |

### When to Fix vs Document

| Condition | Action |
|-----------|--------|
| Simple config fix, low risk | Fix directly |
| Complex change, medium risk | Document, wait for approval |
| Infrastructure change | Document only |
| Security-related | Document + alert |

### Risk Assessment

Before any change:
1. **Reversibility:** Can this be undone?
2. **Blast radius:** What could break?
3. **Dependency:** What relies on this?
4. **Testing:** Can I verify success?

---

## Part 4: Pending Items for Shaun

### Root SSH Setup (Blocking Autonomy)

**One-liner for Shaun to run from Unraid terminal:**

```bash
mkdir -p /root/.ssh && chmod 700 /root/.ssh && \
cat /home/claude/.ssh/id_ed25519.pub >> /root/.ssh/authorized_keys && \
chmod 600 /root/.ssh/authorized_keys && \
echo "Done. Claude can now SSH as root."
```

**After this, I can:**
- Fix HOME variable issue permanently
- Add claude to docker group
- Persist changes across reboots
- Run deploy scripts autonomously

---

## Part 5: Success Metrics

### Session Goals

| Metric | Target |
|--------|--------|
| Health checks completed | 100% |
| Issues identified | All |
| Issues fixed (where possible) | >80% |
| Documentation updated | Yes |
| Discord notifications sent | As needed |
| Downtime caused | 0 |

### Continuous Metrics

| Metric | Threshold |
|--------|-----------|
| Service uptime | >99% |
| Workflow success rate | >95% |
| GPU temperature | <80C |
| Disk space | >10% free |
| Backup age | <24 hours |

---

## Part 6: Execution Schedule

### Immediate (Phase 1-3)
- Deep health assessment
- Monitoring audit
- n8n workflow audit

### Hour 1 (Phase 4-6)
- Database health
- Inference verification
- AI services

### Hour 2 (Phase 7-9)
- Data services
- Security audit
- Documentation

### Ongoing (Phase 10)
- Proactive improvements
- Periodic re-checks
- Summary updates

---

*Document Version: 1.0*
*Author: Claude Code (Hydra Autonomous Steward)*
*Date: 2025-12-16*
