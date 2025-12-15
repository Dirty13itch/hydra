# HYDRA AUTONOMOUS AI SYSTEM - STRATEGIC IMPLEMENTATION PLAN

**Version:** 1.0.0
**Date:** December 14, 2025
**Author:** Hydra Autonomous Steward
**Classification:** Strategic Planning Document

---

## EXECUTIVE SUMMARY

This document presents a comprehensive strategic plan for evolving the Hydra cluster from its current "Phase 12 Complete" state into a fully autonomous, self-improving AI operating system. Based on deep analysis of 36 Python modules, 87 existing roadmap items, 63 running containers, and extensive documentation, this plan identifies **142 actionable improvements** organized into a coherent implementation strategy.

**Current State:** Production-ready infrastructure with significant untapped potential
**Target State:** Self-improving autonomous AI system with voice interface, external intelligence integration, and multi-user support
**Estimated Total Effort:** 180+ hours of implementation across 6-12 months

---

## TABLE OF CONTENTS

1. [Strategic Analysis](#1-strategic-analysis)
2. [Architecture Vision](#2-architecture-vision)
3. [Phase 1: Foundation Hardening](#3-phase-1-foundation-hardening)
4. [Phase 2: Intelligence Activation](#4-phase-2-intelligence-activation)
5. [Phase 3: Autonomous Operations](#5-phase-3-autonomous-operations)
6. [Phase 4: Human-Machine Interface](#6-phase-4-human-machine-interface)
7. [Phase 5: External Integration](#7-phase-5-external-integration)
8. [Phase 6: Creative Production](#8-phase-6-creative-production)
9. [Phase 7: Multi-Stakeholder Operations](#9-phase-7-multi-stakeholder-operations)
10. [Phase 8: Research & Evolution](#10-phase-8-research--evolution)
11. [Implementation Timeline](#11-implementation-timeline)
12. [Success Metrics & KPIs](#12-success-metrics--kpis)
13. [Risk Analysis](#13-risk-analysis)
14. [Resource Requirements](#14-resource-requirements)

---

## 1. STRATEGIC ANALYSIS

### 1.1 Current State Assessment

**Infrastructure Strengths:**
- 3-node cluster with heterogeneous GPU compute (56GB VRAM on hydra-ai, 32GB on hydra-compute)
- 63 operational containers across inference, databases, automation, observability
- Complete observability stack (Prometheus, Grafana, Loki, Alertmanager)
- Phase 11 self-improvement code complete but largely undeployed
- Comprehensive documentation (50K+ words in ARCHITECTURE.md alone)

**Critical Gaps Identified:**

| Gap Category | Current State | Impact |
|--------------|---------------|--------|
| **Deployment Gap** | Phase 11 tools coded but not deployed | 90% of self-improvement capability dormant |
| **Automation Gap** | 1/9+ n8n workflows active | Manual intervention still required |
| **Routing Gap** | RouteLLM pointing to external models | Paying for inference we can do locally |
| **Voice Gap** | No voice interface | Limited human-machine interaction |
| **Integration Gap** | No external APIs connected | System operates in isolation |
| **Security Gap** | Plaintext secrets in docker-compose | Vulnerability to credential theft |
| **Utilization Gap** | hydra-compute GPU 1 at 0.02% | $1500+ hardware sitting idle |

### 1.2 Strategic Priorities

Based on impact analysis, the following priority order is recommended:

1. **Deploy What's Built** - Activate Phase 11 tools, n8n workflows, dashboards
2. **Fix Critical Issues** - IP drift, secrets encryption, health checks
3. **Establish Autonomy** - Self-diagnosis, auto-remediation, intelligent routing
4. **Enable Voice** - Wake word, STT, TTS for natural interaction
5. **Connect Externally** - Calendar, email, research, financial awareness
6. **Scale Production** - Empire pipeline, multi-user, enterprise features

### 1.3 Competitive Positioning

Hydra's unique advantages:
- **Heterogeneous Tensor Parallelism**: ExLlamaV2 supports 5090+4090 TP (unique capability)
- **Local Privacy**: All inference on-premise, no data leaves the network
- **Customization**: Full control over models, prompts, routing, memory
- **Integration Depth**: Direct access to home automation, media, databases

---

## 2. ARCHITECTURE VISION

### 2.1 Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HYDRA AUTONOMOUS SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 7: HUMAN INTERFACE                                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ Voice       │ │ Web UI      │ │ Mobile App  │ │ Claude Code │       │
│  │ "Hey Hydra" │ │ Dashboard   │ │ Companion   │ │ MCP Tools   │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 6: EXTERNAL INTEGRATION                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ Calendar    │ │ Email       │ │ Financial   │ │ Research    │       │
│  │ Google/O365 │ │ Gmail/IMAP  │ │ Plaid/Crypto│ │ Papers/News │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 5: AUTONOMOUS INTELLIGENCE                                       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  COGNITIVE CORE                                                  │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │   │
│  │  │RouteLLM   │ │Self-Diag  │ │Knowledge  │ │Capability │       │   │
│  │  │Classifier │ │Engine     │ │Optimizer  │ │Tracker    │       │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │   │
│  │  │Preference │ │Resource   │ │Learning   │ │Scheduling │       │   │
│  │  │Learning   │ │Optimizer  │ │Loop       │ │Intelligence│       │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 4: AGENT ORCHESTRATION                                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ Letta       │ │ CrewAI      │ │ n8n         │ │ LangGraph   │       │
│  │ Memory      │ │ Multi-Agent │ │ Workflows   │ │ Chains      │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 3: INFERENCE ENGINE                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ LiteLLM Router → TabbyAPI (70B) | Ollama (7B-22B) | CPU Fallback  │ │
│  │                   ↑ RouteLLM Classification                        │ │
│  └───────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 2: DATA LAYER                                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ PostgreSQL  │ │ Qdrant      │ │ Redis       │ │ Neo4j       │       │
│  │ 7 Databases │ │ 6 Collections│ │ Cache/Queue │ │ Graph       │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
├─────────────────────────────────────────────────────────────────────────┤
│  LAYER 1: INFRASTRUCTURE                                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ hydra-ai    │ │hydra-compute│ │hydra-storage│ │ Tailscale   │       │
│  │ 5090+4090   │ │ 2x5070Ti    │ │ Unraid+Docker│ │ VPN Mesh    │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Principles

1. **Local First**: All sensitive processing on-premise
2. **Graceful Degradation**: Fallback chains for every capability
3. **Observable**: Every action logged, traced, measurable
4. **Self-Healing**: Automatic detection and remediation of failures
5. **Privacy-Preserving**: User data never leaves the cluster
6. **Continuously Learning**: Every interaction improves the system

---

## 3. PHASE 1: FOUNDATION HARDENING

**Objective:** Establish bulletproof infrastructure reliability
**Duration:** 2 weeks
**Effort:** 25 hours

### 3.1 Critical Fixes (Already Completed)

- [x] IP address drift remediation (5 files fixed)
- [x] VRAM alert thresholds (90%/95%)
- [x] Dual-format GPU alerts (DCGM + nvidia-smi)
- [x] PostgreSQL backup automation (pg_backup.sh)
- [x] Redis AOF persistence enabled
- [x] SOPS secrets deployed (.env.secrets)

### 3.2 Remaining Foundation Work

#### 3.2.1 Container Health Check Overhaul
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Audit all 63 containers for proper health checks
- [ ] Fix false positive unhealthy status (auditforecaster-backup)
- [ ] Add curl/wget to Alpine containers missing HTTP tools
- [ ] Extend timeout for slow-starting services (ComfyUI, TabbyAPI)
- [ ] Create unified healthcheck.yml snippet library
- [ ] Document health check patterns in runbook

#### 3.2.2 Network Segmentation
**Priority:** MEDIUM | **Effort:** 3 hours

- [ ] Create Docker networks: `hydra-inference`, `hydra-data`, `hydra-public`
- [ ] Migrate containers to appropriate networks
- [ ] Configure inter-network firewall rules
- [ ] Document network topology
- [ ] Test service communication across segments

#### 3.2.3 NixOS Permanent Configuration
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Migrate iptables rules to `/etc/nixos/firewall.nix`
- [ ] Configure both nodes to use AdGuard DNS (192.168.1.244)
- [ ] Add prometheus exporter ports permanently
- [ ] Test configuration with `nixos-rebuild dry-build`
- [ ] Apply and verify

#### 3.2.4 Secrets Migration Completion
**Priority:** HIGH | **Effort:** 3 hours

- [ ] Update docker-compose.yml to use `.env.secrets` references
- [ ] Remove plaintext credentials from version control
- [ ] Add SOPS pre-commit hook for secret detection
- [ ] Document secret rotation procedure
- [ ] Test service startup with encrypted secrets

#### 3.2.5 Backup Strategy Enhancement
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Extend pg_backup.sh to include Qdrant snapshots
- [ ] Configure Redis RDB + AOF backup schedule
- [ ] Create Neo4j backup script
- [ ] Store backups in MinIO with versioning
- [ ] Test restore procedures for all databases
- [ ] Document disaster recovery runbook
- [ ] Add backup verification to daily health digest

#### 3.2.6 Storage Optimization
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Analyze storage usage breakdown (91% utilized)
- [ ] Identify candidates for compression/archival
- [ ] Configure Loki 30-day retention policy
- [ ] Set up Docker image pruning schedule
- [ ] Create storage growth alerting (>95%)

#### 3.2.7 Uptime Kuma Configuration
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Run setup-uptime-kuma.py script
- [ ] Configure 40+ service monitors
- [ ] Set up webhook alerts to n8n
- [ ] Create public status page
- [ ] Configure maintenance windows

#### 3.2.8 Grafana Dashboard Import
**Priority:** LOW | **Effort:** 1 hour

- [ ] Import gpu-utilization-deep-dive.json
- [ ] Import inference-metrics.json updates
- [ ] Import cluster-overview.json updates
- [ ] Configure dashboard provisioning
- [ ] Set up dashboard auto-refresh

#### 3.2.9 Log Retention & Compliance
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Configure Loki retention policies (30/60/90 day tiers)
- [ ] Set up log compaction
- [ ] Enable audit logging for security-sensitive operations
- [ ] Configure log integrity protection
- [ ] Document compliance considerations

#### 3.2.10 Performance Baseline
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Run benchmark-inference.py on all models
- [ ] Document tokens/sec for each GPU configuration
- [ ] Establish latency SLOs (p50, p95, p99)
- [ ] Create performance regression alerts
- [ ] Document baseline in LEARNINGS.md

---

## 4. PHASE 2: INTELLIGENCE ACTIVATION

**Objective:** Enable the self-improving capabilities already coded
**Duration:** 2 weeks
**Effort:** 30 hours

### 4.1 Phase 11 Tools API Deployment

#### 4.1.1 Core Deployment
**Priority:** CRITICAL | **Effort:** 2 hours

- [ ] Deploy hydra-tools-api container (port 8700)
- [ ] Configure environment variables for cluster access
- [ ] Verify all endpoints responding:
  - `/health` - API health
  - `/aggregate/health` - Cluster health score
  - `/routing/classify` - Prompt classification
  - `/diagnosis/health` - Failure tracking
  - `/optimization/suggestions` - Resource recommendations
  - `/knowledge/metrics` - Knowledge health
  - `/capabilities/backlog` - Feature gaps
  - `/preferences/recommend` - Model recommendations

#### 4.1.2 RouteLLM Integration
**Priority:** HIGH | **Effort:** 4 hours

Current Issue: RouteLLM routes to `gpt-3.5-turbo` (external) instead of local models

- [ ] Update `src/hydra_tools/routellm.py` model mappings:
  ```python
  MODEL_TIERS = {
      "fast": "qwen2.5:7b",           # Ollama on hydra-compute
      "code": "codestral:22b",        # Or qwen2.5-coder:7b
      "quality": "deepseek-r1:70b",   # Via LiteLLM
      "creative": "midnight-miqu:70b" # TabbyAPI
  }
  ```
- [ ] Configure LiteLLM to accept RouteLLM decisions
- [ ] Add routing decision logging to Prometheus
- [ ] Create routing effectiveness dashboard
- [ ] Implement fallback chains for each tier
- [ ] Test routing accuracy with benchmark prompts

#### 4.1.3 Self-Diagnosis Activation
**Priority:** HIGH | **Effort:** 3 hours

- [ ] Configure diagnosis engine with cluster endpoints
- [ ] Define failure patterns for common issues:
  - Container OOM kills
  - GPU out of memory
  - Network timeouts
  - Database connection failures
  - Model loading failures
- [ ] Set up auto-remediation for known patterns:
  - Container restart with backoff
  - Model unload/reload
  - Cache clearing
  - Service dependency restart
- [ ] Configure diagnosis → n8n webhook integration
- [ ] Create failure pattern learning pipeline

#### 4.1.4 Resource Optimization Activation
**Priority:** MEDIUM | **Effort:** 3 hours

- [ ] Configure GPU monitoring integration
- [ ] Set up node resource collection (hydra-ai, hydra-compute)
- [ ] Enable model placement recommendations
- [ ] Configure power management suggestions
- [ ] Create optimization suggestion → n8n workflow

#### 4.1.5 Knowledge Optimization Activation
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Configure knowledge source connections (Qdrant, Neo4j)
- [ ] Define staleness thresholds by category
- [ ] Set up redundancy detection
- [ ] Enable archival recommendations
- [ ] Create knowledge refresh triggers

#### 4.1.6 Capability Expansion Tracking
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Configure capability gap webhook
- [ ] Set up priority scoring (frequency × impact)
- [ ] Enable automatic roadmap entry generation
- [ ] Create capability backlog dashboard
- [ ] Configure gap → research task pipeline

### 4.2 n8n Workflow Activation

#### 4.2.1 Import Existing Workflows
**Priority:** HIGH | **Effort:** 2 hours

- [ ] Import alertmanager-handler-v2.json (rate-limited restart)
- [ ] Import disk-cleanup-automation.json (daily 4AM)
- [ ] Import disk-cleanup-alert-handler.json (webhook)
- [ ] Import health-digest-clean.json (daily briefing)
- [ ] Import autonomous-research-clean.json
- [ ] Import learnings-capture-clean.json
- [ ] Import knowledge-refresh-clean.json
- [ ] Import letta-memory-update-clean.json
- [ ] Activate all imported workflows
- [ ] Test each workflow trigger

#### 4.2.2 Create New Automation Workflows
**Priority:** HIGH | **Effort:** 6 hours

**Morning Briefing Workflow:**
- [ ] Schedule: 8AM CST daily
- [ ] Gather: Prometheus metrics, calendar events, weather
- [ ] Generate: Natural language summary via LLM
- [ ] Deliver: Sonos TTS, mobile notification, email

**Container Health Workflow:**
- [ ] Trigger: Prometheus container_unhealthy alert
- [ ] Actions: Log context, attempt restart, escalate if failed
- [ ] Rate limit: Max 3 restarts/hour/container

**Model Performance Tracking Workflow:**
- [ ] Trigger: Every inference request (via LiteLLM callback)
- [ ] Capture: Model, latency, tokens, success/failure
- [ ] Store: PostgreSQL metrics table
- [ ] Analyze: Daily performance summary

**Research Task Queue Workflow:**
- [ ] Trigger: Webhook from capability expansion
- [ ] Actions: Queue research task, assign to CrewAI
- [ ] Monitor: Progress, completion, integration

**Cost Tracking Workflow:**
- [ ] Trigger: Daily at midnight
- [ ] Calculate: Token usage × model costs
- [ ] Store: PostgreSQL cost_tracking table
- [ ] Alert: If daily cost exceeds threshold

**Database Maintenance Workflow:**
- [ ] Schedule: Weekly Sunday 3AM
- [ ] Actions: VACUUM PostgreSQL, optimize Qdrant, compact Redis
- [ ] Report: Space reclaimed, duration

### 4.3 CrewAI Enhancement

#### 4.3.1 Monitoring Crew Enhancement
**Priority:** MEDIUM | **Effort:** 3 hours

Current agents: system_monitor, log_analyst, health_reporter

- [ ] Add `alert_correlator` agent - correlate related alerts
- [ ] Add `capacity_planner` agent - predict resource needs
- [ ] Create crew → Letta memory integration
- [ ] Set up scheduled monitoring runs (hourly)
- [ ] Configure anomaly detection thresholds

#### 4.3.2 Research Crew Implementation
**Priority:** HIGH | **Effort:** 4 hours

Existing stub: web_researcher, synthesizer, reporter

- [ ] Implement full web_researcher agent:
  - SearXNG integration
  - Firecrawl for deep scraping
  - Rate limiting for external APIs
- [ ] Implement synthesizer agent:
  - Multi-source information fusion
  - Citation tracking
  - Confidence scoring
- [ ] Implement reporter agent:
  - Markdown report generation
  - Executive summary creation
  - Qdrant storage for retrieval
- [ ] Create research templates:
  - Technology benchmark
  - Market analysis
  - Competitor research
  - Academic survey

#### 4.3.3 Maintenance Crew Implementation
**Priority:** MEDIUM | **Effort:** 3 hours

Existing stub: container_inspector, storage_analyst, maintenance_planner

- [ ] Implement container_inspector:
  - Docker stats collection
  - Log analysis for errors
  - Resource usage trending
- [ ] Implement storage_analyst:
  - Disk usage breakdown
  - Growth rate projection
  - Cleanup recommendations
- [ ] Implement maintenance_planner:
  - Maintenance window scheduling
  - Impact assessment
  - Rollback planning
- [ ] Create maintenance runbook executor

### 4.4 Letta Memory Enhancement

#### 4.4.1 Memory Block Enrichment
**Priority:** HIGH | **Effort:** 3 hours

Current blocks: persona, human, cluster_state, tasks, project_details, model_performance, system_learnings

- [ ] Add `interaction_patterns` block:
  - User query patterns
  - Time-of-day preferences
  - Common task types
- [ ] Add `failure_history` block:
  - Recent failures and resolutions
  - Recurring issues
  - Workarounds learned
- [ ] Add `optimization_history` block:
  - Optimizations applied
  - Performance improvements measured
  - Reverted changes and reasons
- [ ] Add `external_context` block:
  - Current weather
  - Calendar events today
  - Recent email summaries

#### 4.4.2 Memory Consolidation Pipeline
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Create daily memory consolidation workflow
- [ ] Implement memory summarization (condense old entries)
- [ ] Set up memory importance scoring
- [ ] Configure memory archival to Qdrant
- [ ] Create memory visualization dashboard

#### 4.4.3 Cross-Agent Memory Sharing
**Priority:** MEDIUM | **Effort:** 2 hours

- [ ] Configure shared memory space for all agents
- [ ] Implement memory sync between Letta and CrewAI
- [ ] Create memory conflict resolution
- [ ] Set up memory audit logging

---

## 5. PHASE 3: AUTONOMOUS OPERATIONS

**Objective:** System operates independently with minimal human intervention
**Duration:** 3 weeks
**Effort:** 35 hours

### 5.1 Self-Healing Infrastructure

#### 5.1.1 Failure Detection Enhancement
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Create comprehensive failure taxonomy:
  - **Infrastructure**: Network, storage, compute
  - **Application**: Container, service, model
  - **Data**: Database, cache, queue
  - **Integration**: External API, webhook, notification
- [ ] Implement multi-signal failure detection:
  - Prometheus metrics anomalies
  - Log error rate spikes
  - Health check failures
  - Response time degradation
- [ ] Configure correlation engine:
  - Related failure grouping
  - Root cause identification
  - Blast radius assessment

#### 5.1.2 Auto-Remediation Framework
**Priority:** HIGH | **Effort:** 5 hours

- [ ] Define remediation playbooks:
  ```yaml
  - trigger: container_unhealthy
    actions:
      - wait: 30s
      - restart_container
      - verify_health
      - if_failed: escalate

  - trigger: gpu_oom
    actions:
      - identify_model
      - reduce_batch_size
      - if_failed: unload_model
      - notify_user

  - trigger: disk_full_warning
    actions:
      - run_cleanup_workflow
      - notify_if_still_critical
  ```
- [ ] Implement remediation executor
- [ ] Add remediation rate limiting (prevent loops)
- [ ] Create remediation audit log
- [ ] Set up remediation effectiveness tracking

#### 5.1.3 Predictive Maintenance
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Implement trend analysis for:
  - Disk usage growth
  - Memory consumption patterns
  - GPU VRAM pressure
  - Container restart frequency
- [ ] Create predictive alerts:
  - "Disk will be full in 7 days at current rate"
  - "VRAM usage trending toward OOM"
  - "Container restart rate increasing"
- [ ] Implement proactive remediation triggers

### 5.2 Intelligent Scheduling

#### 5.2.1 Task Prioritization Engine
**Priority:** MEDIUM | **Effort:** 3 hours

- [ ] Create task queue with priority scoring:
  - Urgency (deadline proximity)
  - Importance (user-defined)
  - Resource requirements
  - Dependencies
- [ ] Implement task scheduling algorithm
- [ ] Configure queue visualization
- [ ] Add task progress tracking

#### 5.2.2 Resource-Aware Scheduling
**Priority:** MEDIUM | **Effort:** 3 hours

- [ ] Implement GPU-aware task routing:
  - Heavy inference → hydra-ai
  - Image generation → hydra-compute
  - Batch processing → off-peak hours
- [ ] Create time-of-day scheduling:
  - Research tasks → nighttime
  - User requests → immediate
  - Maintenance → weekends
- [ ] Configure resource reservation system

#### 5.2.3 Model Loading Optimization
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Implement intelligent model preloading:
  - Predict likely model needs
  - Pre-warm frequently used models
  - Unload idle models automatically
- [ ] Create model switching pipeline:
  - Graceful request draining
  - Hot-swap capability
  - Fallback during transition
- [ ] Optimize model loading time:
  - NVMe caching for hot models
  - Parallel layer loading
  - Progressive model availability

### 5.3 Learning Loop

#### 5.3.1 Feedback Collection
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Implement implicit feedback collection:
  - Response regeneration (negative signal)
  - Conversation continuation (positive signal)
  - Task completion rate
  - Session duration
- [ ] Create explicit feedback mechanism:
  - Thumbs up/down on responses
  - Correction acceptance
  - Rating prompts
- [ ] Store feedback in structured format

#### 5.3.2 Preference Learning Pipeline
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Enhance preference_learning.py:
  - Learn routing preferences per task type
  - Learn response style preferences
  - Learn time-of-day patterns
- [ ] Implement A/B testing framework:
  - Model comparison
  - Prompt variant testing
  - Parameter optimization
- [ ] Create preference dashboard

#### 5.3.3 Knowledge Graph Evolution
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Implement automatic knowledge extraction:
  - Entity extraction from conversations
  - Relationship inference
  - Fact verification
- [ ] Create knowledge graph update pipeline:
  - New node insertion
  - Relationship updates
  - Conflict resolution
- [ ] Configure knowledge graph queries

---

## 6. PHASE 4: HUMAN-MACHINE INTERFACE

**Objective:** Natural, intuitive interaction with the system
**Duration:** 4 weeks
**Effort:** 40 hours

### 6.1 Voice Interface

#### 6.1.1 Wake Word Detection
**Priority:** HIGH | **Effort:** 6 hours

- [ ] Deploy wake word model:
  - Options: Porcupine, OpenWakeWord, Snowboy
  - Configure for "Hey Hydra" activation
  - Multi-room microphone support
- [ ] Create audio capture pipeline:
  - Low-latency audio streaming
  - Noise cancellation
  - Voice activity detection
- [ ] Implement privacy controls:
  - Local processing only
  - Recording indicator
  - Wake word audit log

#### 6.1.2 Speech-to-Text Pipeline
**Priority:** HIGH | **Effort:** 5 hours

- [ ] Deploy faster-whisper on hydra-compute:
  - GPU-accelerated transcription
  - Streaming transcription mode
  - Multi-language support
- [ ] Create STT service:
  - WebSocket endpoint for streaming audio
  - Batch endpoint for recorded audio
  - Confidence scoring
- [ ] Optimize for latency:
  - Target: <500ms first word
  - Use small model for initial transcription
  - Large model for difficult audio

#### 6.1.3 Text-to-Speech Enhancement
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Enhance Kokoro TTS deployment:
  - Add more voice models
  - Implement emotion control
  - Configure speed/pitch adjustment
- [ ] Create multi-room audio routing:
  - Sonos integration
  - Room-aware responses
  - Volume adaptation
- [ ] Implement voice selection:
  - User preference storage
  - Context-aware voice selection
  - Character voices for Empire

#### 6.1.4 Conversation Management
**Priority:** HIGH | **Effort:** 5 hours

- [ ] Implement conversation context:
  - Multi-turn dialogue tracking
  - Context window management
  - Topic detection and switching
- [ ] Create interruption handling:
  - Barge-in support
  - Graceful response truncation
  - Priority override for urgent queries
- [ ] Add conversation memory:
  - Recent conversation recall
  - Reference resolution
  - User preference learning

### 6.2 Web Dashboard

#### 6.2.1 Control Plane UI Enhancement
**Priority:** MEDIUM | **Effort:** 6 hours

- [ ] Enhance hydra-control-plane-ui:
  - Real-time cluster status
  - Model management interface
  - Workflow triggering
  - Memory visualization
- [ ] Add dashboard widgets:
  - GPU utilization gauges
  - Token throughput graphs
  - Alert timeline
  - Task queue status
- [ ] Implement mobile-responsive design

#### 6.2.2 Conversational UI
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Create web chat interface:
  - Streaming responses
  - Markdown rendering
  - Code syntax highlighting
  - File upload support
- [ ] Add conversation features:
  - History sidebar
  - Search conversations
  - Export functionality
  - Sharing capabilities

### 6.3 Notification System

#### 6.3.1 Multi-Channel Notifications
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Configure notification channels:
  - **Sonos TTS**: Urgent alerts, briefings
  - **Mobile Push**: Status updates, completions
  - **Email**: Daily digests, reports
  - **Discord**: Optional community updates
- [ ] Implement notification routing:
  - Severity-based channel selection
  - Time-of-day awareness
  - Do Not Disturb support
- [ ] Create notification preferences UI

#### 6.3.2 Smart Summarization
**Priority:** MEDIUM | **Effort:** 3 hours

- [ ] Implement alert aggregation:
  - Group related alerts
  - Create summary notifications
  - Avoid notification fatigue
- [ ] Create intelligent briefings:
  - Personalized content
  - Priority-ordered items
  - Actionable summaries

### 6.4 Home Automation Integration

#### 6.4.1 Presence-Based Automation
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Configure person tracking:
  - Phone presence detection
  - Device tracker integration
  - Guest vs. resident differentiation
- [ ] Create presence modes:
  - **Away**: Eco GPU power, pause non-essential tasks
  - **Home**: Full capability, preference activation
  - **Sleep**: Quiet mode, overnight batch processing
  - **Focus**: DND, priority inference only
- [ ] Implement geofence triggers:
  - Arrival preparation
  - Departure cleanup
  - Location-aware reminders

#### 6.4.2 Smart Scenes
**Priority:** LOW | **Effort:** 3 hours

- [ ] Create scene definitions:
  - **Movie Night**: Dim lights, quiet fan, pause downloads
  - **Work Focus**: Optimal lighting, inference priority
  - **Party Mode**: Music routing, lighting effects
  - **Goodnight**: Security check, energy savings
- [ ] Implement scene activation:
  - Voice command
  - Schedule-based
  - Context-aware automatic

---

## 7. PHASE 5: EXTERNAL INTEGRATION

**Objective:** Connect system to external data sources and services
**Duration:** 4 weeks
**Effort:** 35 hours

### 7.1 Calendar Integration

#### 7.1.1 Google Calendar Connection
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Set up Google Calendar API:
  - OAuth 2.0 authentication
  - Calendar read access
  - Event creation capability
- [ ] Create calendar service:
  - Event fetching (next 7 days)
  - Free/busy checking
  - Event creation/modification
- [ ] Implement calendar features:
  - "What's on my schedule today?"
  - Meeting preparation automation
  - Conflict detection and alerting

#### 7.1.2 Meeting Intelligence
**Priority:** MEDIUM | **Effort:** 3 hours

- [ ] Create meeting preparation workflow:
  - Participant research
  - Agenda summarization
  - Relevant document retrieval
- [ ] Implement meeting reminders:
  - Pre-meeting briefing
  - Travel time calculation
  - Preparation checklist

### 7.2 Email Integration

#### 7.2.1 Gmail Connection
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Set up Gmail API:
  - OAuth 2.0 authentication
  - Read access to inbox
  - Send capability (optional)
- [ ] Create email service:
  - Important email detection
  - Thread summarization
  - Search functionality
- [ ] Implement email features:
  - "Any important emails?"
  - Email summarization on demand
  - Smart reply suggestions

#### 7.2.2 Email Digest
**Priority:** MEDIUM | **Effort:** 3 hours

- [ ] Create email digest workflow:
  - Morning email summary
  - Priority inbox analysis
  - Action item extraction
- [ ] Implement follow-up tracking:
  - Pending response detection
  - Follow-up reminders
  - Thread tracking

### 7.3 Research Integration

#### 7.3.1 News Monitoring
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Configure RSS/Atom feed monitoring:
  - Tech news sources
  - AI/ML research feeds
  - Domain-specific sources
- [ ] Implement article processing:
  - Automatic summarization
  - Relevance scoring
  - Qdrant storage
- [ ] Create research alerts:
  - Topic-based notifications
  - Competitor monitoring
  - Trend detection

#### 7.3.2 Academic Paper Integration
**Priority:** LOW | **Effort:** 4 hours

- [ ] Set up arXiv/Semantic Scholar integration
- [ ] Implement paper processing:
  - Abstract extraction
  - Citation analysis
  - Relevance filtering
- [ ] Create paper briefing workflow

### 7.4 Financial Integration

#### 7.4.1 Banking Integration (Plaid)
**Priority:** LOW | **Effort:** 4 hours

- [ ] Set up Plaid API connection
- [ ] Implement account monitoring:
  - Balance tracking
  - Transaction categorization
  - Spending pattern analysis
- [ ] Create financial alerts:
  - Large transaction notifications
  - Budget threshold warnings
  - Bill due reminders

#### 7.4.2 Cryptocurrency Tracking
**Priority:** LOW | **Effort:** 3 hours

- [ ] Connect to crypto APIs (CoinGecko, etc.)
- [ ] Implement portfolio tracking
- [ ] Create price alerts

### 7.5 Social Media Integration

#### 7.5.1 Twitter/X Monitoring
**Priority:** LOW | **Effort:** 3 hours

- [ ] Set up Twitter API connection
- [ ] Implement mention monitoring
- [ ] Create tweet scheduling capability

#### 7.5.2 Discord Integration
**Priority:** LOW | **Effort:** 3 hours

- [ ] Set up Discord bot
- [ ] Implement webhook notifications
- [ ] Create command interface

---

## 8. PHASE 6: CREATIVE PRODUCTION

**Objective:** Scalable content generation pipeline for "Empire of Broken Queens"
**Duration:** 4 weeks
**Effort:** 40 hours

### 8.1 Character Consistency

#### 8.1.1 InstantID Integration
**Priority:** HIGH | **Effort:** 6 hours

- [ ] Deploy InstantID on hydra-compute
- [ ] Create face embedding pipeline:
  - Character face extraction
  - Embedding generation
  - Qdrant storage (empire_faces)
- [ ] Implement face consistency workflow:
  - Reference image selection
  - InstantID conditioning
  - Quality verification

#### 8.1.2 Character LoRA Training
**Priority:** MEDIUM | **Effort:** 8 hours

- [ ] Set up LoRA training pipeline:
  - Dataset preparation
  - Training configuration
  - Model versioning
- [ ] Train character LoRAs:
  - Seraphina (queen)
  - Mira (advisor)
  - Lysander (knight)
  - Additional characters
- [ ] Create LoRA management:
  - Version control
  - A/B testing
  - Quality scoring

### 8.2 Image Generation Pipeline

#### 8.2.1 Chapter Processor Enhancement
**Priority:** HIGH | **Effort:** 6 hours

- [ ] Enhance chapter-processor workflow:
  - Scene extraction
  - Character identification
  - Emotion detection
- [ ] Create batch portrait generation:
  - Character consistency via InstantID
  - Style consistency via IP-Adapter
  - Quality verification step
- [ ] Implement background generation:
  - Scene description extraction
  - Style-consistent backgrounds
  - Asset organization

#### 8.2.2 Quality Assurance Pipeline
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Create visual consistency checker:
  - Character feature verification
  - Style consistency scoring
  - Anomaly detection
- [ ] Implement human feedback loop:
  - Quality rating interface
  - Feedback storage
  - Model fine-tuning triggers
- [ ] Create asset manifest generator

### 8.3 Voice Acting Pipeline

#### 8.3.1 Character Voice Profiles
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Expand voice profile database:
  - Additional Kokoro voices
  - Custom voice cloning (if available)
  - Emotion variants
- [ ] Create voice selection logic:
  - Character → voice mapping
  - Emotion → modulation mapping
  - Scene context awareness

#### 8.3.2 Audio Post-Processing
**Priority:** LOW | **Effort:** 4 hours

- [ ] Implement audio effects:
  - Room reverb simulation
  - Background ambiance mixing
  - Emotional emphasis
- [ ] Create lip-sync timing:
  - Phoneme extraction
  - Timing data generation
  - Live2D integration prep

### 8.4 Asset Management

#### 8.4.1 Asset Organization
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Create asset naming convention
- [ ] Implement automatic organization
- [ ] Create asset database (PostgreSQL)
- [ ] Build asset browser UI

#### 8.4.2 Production Tracking
**Priority:** LOW | **Effort:** 4 hours

- [ ] Create production dashboard
- [ ] Implement progress tracking
- [ ] Create quality metrics
- [ ] Build export pipeline

---

## 9. PHASE 7: MULTI-STAKEHOLDER OPERATIONS

**Objective:** Support multiple users with appropriate isolation and permissions
**Duration:** 3 weeks
**Effort:** 30 hours

### 9.1 Identity & Access Management

#### 9.1.1 User Identity System
**Priority:** HIGH | **Effort:** 6 hours

- [ ] Implement Tailscale identity integration:
  - User identification via Tailscale
  - Device tracking
  - Session management
- [ ] Create user profile system:
  - Preferences storage
  - Permission levels
  - Usage quotas
- [ ] Add authentication options:
  - PIN/password
  - Biometric (optional)
  - SSO integration

#### 9.1.2 Permission Model
**Priority:** HIGH | **Effort:** 4 hours

- [ ] Define permission levels:
  - **ADMIN**: Full access, system configuration
  - **STANDARD**: All features, limited config
  - **LIMITED**: Inference only, no admin
  - **GUEST**: Basic queries, rate limited
- [ ] Implement permission enforcement
- [ ] Create audit logging

### 9.2 Multi-Agent Architecture

#### 9.2.1 Per-User Agents
**Priority:** MEDIUM | **Effort:** 6 hours

- [ ] Create per-user Letta agents:
  - Separate memory spaces
  - User-specific preferences
  - Individual conversation history
- [ ] Implement agent switching:
  - User identification → agent selection
  - Context preservation
  - Seamless handoff

#### 9.2.2 Shared Resources
**Priority:** MEDIUM | **Effort:** 4 hours

- [ ] Create shared knowledge base:
  - Common information (cluster state, capabilities)
  - Access control for sensitive data
  - Update propagation
- [ ] Implement resource allocation:
  - Fair queuing for inference
  - Priority-based scheduling
  - Quota enforcement

### 9.3 Collaboration Features

#### 9.3.1 Shared Workspaces
**Priority:** LOW | **Effort:** 5 hours

- [ ] Create shared project spaces
- [ ] Implement collaborative editing
- [ ] Add real-time presence

#### 9.3.2 Handoff Protocol
**Priority:** LOW | **Effort:** 5 hours

- [ ] Define handoff triggers
- [ ] Implement context transfer
- [ ] Create handoff notification

---

## 10. PHASE 8: RESEARCH & EVOLUTION

**Objective:** Continuous improvement through research and experimentation
**Duration:** Ongoing
**Effort:** Continuous

### 10.1 Model Exploration

#### 10.1.1 New Model Evaluation
**Priority:** ONGOING | **Effort:** Continuous

- [ ] Evaluate Llama-3.3-70B when available
- [ ] Test DeepSeek-R1-Distill-70B
- [ ] Benchmark Qwen3-235B MoE
- [ ] Explore DeepSeek-V3 671B MoE
- [ ] Test ExLlamaV3 heterogeneous TP

#### 10.1.2 Quantization Research
**Priority:** ONGOING | **Effort:** Continuous

- [ ] Compare EXL2 vs GGUF performance
- [ ] Test new quantization methods
- [ ] Evaluate quality vs speed tradeoffs

### 10.2 Architecture Evolution

#### 10.2.1 Scalability Research
**Priority:** LOW | **Effort:** Research

- [ ] Evaluate Kubernetes migration
- [ ] Research multi-node inference
- [ ] Explore edge deployment
- [ ] Investigate federated learning

#### 10.2.2 New Capabilities
**Priority:** ONGOING | **Effort:** Research

- [ ] Video generation (Mochi, CogVideoX)
- [ ] Music generation (Stable Audio, MusicGen)
- [ ] 3D asset generation
- [ ] Real-time conversation

### 10.3 Performance Optimization

#### 10.3.1 Inference Optimization
**Priority:** ONGOING | **Effort:** Continuous

- [ ] Implement speculative decoding
- [ ] Optimize batch sizes dynamically
- [ ] Tune KV cache parameters
- [ ] Profile and optimize hot paths

#### 10.3.2 System Optimization
**Priority:** ONGOING | **Effort:** Continuous

- [ ] Network optimization
- [ ] Storage performance tuning
- [ ] Memory management
- [ ] Power efficiency

---

## 11. IMPLEMENTATION TIMELINE

### 11.1 Gantt Chart Overview

```
Week 1-2:   [████████████████████] Phase 1: Foundation Hardening
Week 3-4:   [████████████████████] Phase 2: Intelligence Activation
Week 5-7:   [██████████████████████████████] Phase 3: Autonomous Operations
Week 8-11:  [████████████████████████████████████████] Phase 4: Human-Machine Interface
Week 12-15: [████████████████████████████████████████] Phase 5: External Integration
Week 16-19: [████████████████████████████████████████] Phase 6: Creative Production
Week 20-22: [██████████████████████████████] Phase 7: Multi-Stakeholder
Week 23+:   [████████████████████████████████████████████████████] Phase 8: Ongoing Research
```

### 11.2 Milestone Schedule

| Milestone | Target Date | Key Deliverables |
|-----------|-------------|------------------|
| Foundation Complete | Week 2 | All critical fixes, secrets encrypted, backups verified |
| Intelligence Active | Week 4 | Phase 11 deployed, n8n workflows active, CrewAI enhanced |
| Self-Healing Operational | Week 7 | Auto-remediation working, predictive alerts, learning loop |
| Voice Interface MVP | Week 11 | Wake word, STT, TTS, basic commands working |
| External Integration v1 | Week 15 | Calendar + email connected, research pipeline active |
| Empire Pipeline v1 | Week 19 | Character consistency, chapter processing, voice acting |
| Multi-User Ready | Week 22 | Identity system, per-user agents, permissions |

### 11.3 Priority Order (First 30 Days)

**Days 1-2: Critical Activations**
1. Deploy hydra-tools-api (Phase 11)
2. Import n8n workflows
3. Import Grafana dashboards

**Days 3-7: Foundation Completion**
4. Container health check fixes
5. Secrets migration completion
6. Backup strategy verification

**Days 8-14: Intelligence Layer**
7. RouteLLM local model integration
8. Self-diagnosis activation
9. CrewAI research crew implementation

**Days 15-21: Automation Expansion**
10. Create morning briefing workflow
11. Implement container health workflow
12. Configure Uptime Kuma

**Days 22-30: Voice Interface Start**
13. Deploy wake word detection
14. Configure faster-whisper
15. Test basic voice commands

---

## 12. SUCCESS METRICS & KPIs

### 12.1 Infrastructure KPIs

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Container Health Rate | 98.4% (62/63) | 100% | Week 2 |
| Prometheus Targets UP | 100% | 100% | Maintain |
| Secrets Encrypted | ~30% | 100% | Week 2 |
| Backup Success Rate | N/A | 100% | Week 2 |
| Mean Time to Recovery | Manual | <5 min | Week 7 |

### 12.2 Intelligence KPIs

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Routing to Local Models | 0% | 95% | Week 4 |
| n8n Active Workflows | 1 | 15+ | Week 4 |
| Auto-Remediation Rate | 0% | 80% | Week 7 |
| Learning Feedback Collected | 0 | 100+/day | Week 8 |
| Capability Gaps Tracked | 0 | 20+ | Week 4 |

### 12.3 User Experience KPIs

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Voice Command Success | N/A | 90% | Week 11 |
| Response Latency p95 | ~2s | <1s | Week 7 |
| Daily Briefing Delivery | N/A | 100% | Week 4 |
| User Satisfaction | N/A | 4.5/5 | Ongoing |

### 12.4 Creative Production KPIs

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Character Consistency Score | N/A | 90% | Week 19 |
| Image Generation Success | N/A | 95% | Week 16 |
| Voice Acting Quality | N/A | 4/5 | Week 18 |
| Chapter Processing Time | N/A | <10 min | Week 17 |

---

## 13. RISK ANALYSIS

### 13.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GPU OOM during inference | Medium | High | VRAM monitoring, auto-unload, alerts |
| Model loading failures | Low | Medium | Fallback chains, health checks |
| Database corruption | Low | Critical | Automated backups, replication |
| Network partition | Low | High | Tailscale mesh, local fallback |
| Container orchestration failure | Low | Medium | Health checks, auto-restart |

### 13.2 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Credential exposure | Medium | Critical | SOPS encryption, rotation |
| Resource exhaustion | Medium | Medium | Monitoring, auto-scaling |
| Integration failures | Medium | Low | Circuit breakers, fallbacks |
| Update regressions | Medium | Medium | Staged rollouts, rollback |

### 13.3 Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Feature creep | High | Medium | Phased approach, prioritization |
| Scope expansion | High | Medium | Clear milestones, MVP focus |
| Technical debt | Medium | Medium | Regular refactoring time |

---

## 14. RESOURCE REQUIREMENTS

### 14.1 Compute Resources

**Current Capacity:**
- hydra-ai: RTX 5090 (32GB) + RTX 4090 (24GB) = 56GB VRAM
- hydra-compute: 2x RTX 5070 Ti (32GB) = 32GB VRAM
- hydra-storage: EPYC 7663 (64 cores), 256GB RAM, 164TB storage

**Utilization:**
- hydra-ai: 87.5% VRAM (running 70B model)
- hydra-compute: 33.8% VRAM (significant headroom)
- hydra-storage: 91% disk (monitoring needed)

**Recommendations:**
- Utilize idle hydra-compute GPU for parallel tasks
- Monitor storage growth, plan expansion if needed
- Consider NVMe cache for model hot-loading

### 14.2 Human Resources

**Effort Estimate by Phase:**
| Phase | Hours | Skills Required |
|-------|-------|-----------------|
| Phase 1: Foundation | 25 | DevOps, Docker, NixOS |
| Phase 2: Intelligence | 30 | Python, ML Ops, API design |
| Phase 3: Autonomous | 35 | Systems design, ML |
| Phase 4: Interface | 40 | Audio/Voice, Web dev |
| Phase 5: External | 35 | API integration, OAuth |
| Phase 6: Creative | 40 | ComfyUI, Audio engineering |
| Phase 7: Multi-user | 30 | Auth systems, Architecture |
| Phase 8: Research | Ongoing | ML research, Benchmarking |
| **Total** | **235+ hours** | |

### 14.3 External Dependencies

| Dependency | Blocking | Notes |
|------------|----------|-------|
| VPN Credentials | Yes | Gluetun deployment blocked |
| Google Calendar API | Yes | Calendar integration |
| Gmail API | Yes | Email integration |
| Plaid API | Optional | Financial integration |
| Home devices | Optional | Lutron, Bond, Nest setup |

---

## APPENDIX A: QUICK START CHECKLIST

### Today (2 hours)
- [ ] Deploy hydra-tools-api: `docker-compose -f hydra-tools-api.yml up -d`
- [ ] Import n8n workflows via web UI
- [ ] Import GPU dashboard to Grafana
- [ ] Verify Phase 11 endpoints: `curl http://192.168.1.244:8700/health`

### This Week (10 hours)
- [ ] Fix remaining container health checks
- [ ] Complete secrets migration
- [ ] Configure Uptime Kuma monitors
- [ ] Update RouteLLM for local models
- [ ] Create morning briefing workflow

### This Month (40 hours)
- [ ] Implement self-diagnosis auto-remediation
- [ ] Deploy wake word detection
- [ ] Connect calendar API
- [ ] Create research crew implementation
- [ ] Begin character consistency work

---

## APPENDIX B: COMMAND REFERENCE

### Phase 11 API Endpoints
```bash
# Health check
curl http://192.168.1.244:8700/health

# Aggregate cluster health
curl http://192.168.1.244:8700/aggregate/health

# Classify prompt
curl -X POST "http://192.168.1.244:8700/routing/classify?prompt=Hello"

# Get routing tiers
curl http://192.168.1.244:8700/routing/tiers

# Self-diagnosis health
curl http://192.168.1.244:8700/diagnosis/health

# Resource optimization suggestions
curl http://192.168.1.244:8700/optimization/suggestions

# Knowledge metrics
curl http://192.168.1.244:8700/knowledge/metrics
```

### Docker Commands
```bash
# Deploy Phase 11 API
docker-compose -f docker-compose/hydra-tools-api.yml up -d

# Check container health
docker ps --format 'table {{.Names}}\t{{.Status}}'

# View logs
docker logs -f hydra-tools-api --tail 100

# Restart service
docker restart hydra-litellm
```

### Cluster Status
```bash
# GPU status
ssh typhon@192.168.1.250 "nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv"
ssh typhon@192.168.1.203 "nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv"

# Container count
ssh root@192.168.1.244 "docker ps | wc -l"

# Prometheus targets
curl -s http://192.168.1.244:9090/api/v1/targets | jq '.data.activeTargets | length'
```

---

## APPENDIX C: DOCUMENT REFERENCES

| Document | Location | Purpose |
|----------|----------|---------|
| CLAUDE.md | `/hydra/CLAUDE.md` | Steward configuration |
| VISION.md | `/hydra/VISION.md` | System philosophy |
| ARCHITECTURE.md | `/hydra/ARCHITECTURE.md` | Technical blueprint |
| ROADMAP.md | `/hydra/ROADMAP.md` | 15-phase plan |
| LEARNINGS.md | `/hydra/LEARNINGS.md` | Operational wisdom |
| swift-baking-ocean.md | `/.claude/plans/` | 87-item improvement roadmap |
| STATE.json | `/hydra/STATE.json` | Current system state |

---

**Document Version:** 1.0.0
**Last Updated:** December 14, 2025
**Next Review:** January 14, 2026

---

*Generated by Hydra Autonomous Steward using ULTRATHINK analysis*
