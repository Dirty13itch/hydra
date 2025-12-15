# Hydra Repository Structure

This document describes the organization of the Hydra cluster repository.

## Directory Overview

```
hydra/
├── src/                    # Production Python modules
│   ├── hydra_tools/       # Phase 11 self-improvement (23 modules)
│   │   ├── api.py         # FastAPI endpoints
│   │   ├── routellm.py    # Intelligent model routing
│   │   ├── preference_learning.py  # User preference tracking
│   │   ├── self_diagnosis.py  # Failure analysis
│   │   ├── resource_optimization.py  # GPU/CPU utilization
│   │   ├── knowledge_optimization.py  # Knowledge lifecycle
│   │   ├── capability_expansion.py  # Feature gap tracking
│   │   └── letta_memory.py  # Letta memory enhancement
│   ├── hydra_voice/       # Voice interface API (port 8850)
│   ├── hydra_stt/         # Speech-to-text service (port 9001)
│   ├── hydra_wakeword/    # Wake word detection (port 8860)
│   ├── hydra_crews/       # CrewAI multi-agent orchestration
│   │   ├── research_crew.py  # Web research & synthesis
│   │   ├── monitoring_crew.py  # Cluster health monitoring
│   │   └── maintenance_crew.py  # Automated maintenance
│   ├── hydra_health/      # Health check server
│   ├── hydra_alerts/      # Alert webhook handler
│   ├── hydra_cli/         # Command-line tools
│   ├── hydra_search/      # Hybrid search (Qdrant + embeddings)
│   └── hydra_reconcile/   # State reconciliation
│
├── ui/                     # React/Next.js control plane (Typhon Command)
│   └── src/
│       ├── app/           # Next.js app router
│       └── components/    # 35+ React components
│           └── domain-views/  # 8 specialized domain views
│
├── config/                 # Service configurations
│   ├── alertmanager/      # Alert routing
│   ├── grafana/           # Dashboards
│   ├── loki/              # Log aggregation (30-day retention)
│   ├── n8n/workflows/     # 37+ automation workflows
│   ├── nixos/             # NixOS module configs
│   ├── prometheus/        # Metrics & alerts
│   │   └── rules/         # Recording rules, 50+ alert rules
│   └── redis/             # Redis persistence (AOF + RDB)
│
├── docker-compose/         # Container orchestration
│   ├── hydra-stack.yml    # Main stack (60+ services)
│   ├── hydra-tools-api.yml # Phase 11 API (port 8700)
│   ├── voice-interface.yml # Voice pipeline (port 8850)
│   ├── stt-service.yml    # Speech-to-text (port 9001)
│   ├── wakeword-service.yml # Wake word detection (port 8860)
│   └── [others].yml       # Service-specific overrides
│
├── docker/                 # Dockerfiles
│
├── scripts/                # Operational scripts
│   ├── deploy-*.sh        # Deployment scripts
│   ├── backup-*.sh        # Backup scripts
│   ├── configure-*.py     # Configuration generators
│   │   └── configure-uptime-kuma.py  # Uptime Kuma monitor setup
│   ├── setup-sops.sh      # SOPS encryption setup
│   ├── *.py               # Python utilities
│   └── *.ps1              # PowerShell scripts (Windows)
│
├── knowledge/              # Operational knowledge base (quick reference)
│   ├── infrastructure.md  # Hardware, network, ports
│   ├── inference-stack.md # TabbyAPI, ExLlamaV2, LiteLLM
│   ├── databases.md       # PostgreSQL, Qdrant, Redis
│   └── [others].md
│
├── docs/                   # Technical documentation
│   ├── canonical/         # SOURCE OF TRUTH
│   │   ├── 00-system-reality/  # Current state snapshots
│   │   ├── 01-architecture-decisions/  # ADRs
│   │   ├── 02-runbooks/   # Operational procedures
│   │   ├── 03-network/    # DNS, ingress plans
│   │   ├── 04-storage/    # Backup/restore plans
│   │   ├── 05-observability/  # Monitoring
│   │   ├── 06-control-plane/  # Architecture
│   │   └── 07-security/   # Secrets management
│   ├── operations/        # Service dependencies
│   └── runbooks/          # Recovery procedures
│
├── mcp/                    # MCP server implementation
│   ├── mcp_server.py      # Main MCP server (PRODUCTION)
│   └── hydra_mcp_proxy.py # Local proxy for Claude Code
│
├── mcp-servers/            # MCP server packages
│
├── nixos-modules/          # NixOS module definitions
│   ├── tabbyapi.nix       # TabbyAPI service
│   ├── ollama.nix         # Ollama service
│   ├── comfyui.nix        # ComfyUI service
│   └── [others].nix
│
├── tests/                  # Test suite
│
├── legacy/                 # Archived/deprecated code
│   ├── patches/           # Applied patches
│   ├── prototypes/        # Experimental code
│   ├── mcp-archive/       # Old MCP versions
│   └── zips/              # Archived tarballs
│
├── plans/                  # Strategic planning docs
│
├── secrets/                # SOPS-encrypted secrets
│
├── data/                   # Data files
│   └── empire/            # Empire of Broken Queens data
│
├── homeassistant/          # Home Assistant configs
│
├── Empire of Broken Queens/ # Creative project (separate concern)
│
└── [Root files]
    ├── CLAUDE.md          # Steward instructions
    ├── ARCHITECTURE.md    # Technical overview → points to docs/canonical
    ├── VISION.md          # Strategic direction
    ├── ROADMAP.md         # Development roadmap
    ├── STATE.json         # Current cluster state snapshot
    ├── pyproject.toml     # Python package definition
    └── .mcp.json          # MCP configuration
```

## Key Principles

1. **Source of Truth**: `docs/canonical/` for architecture decisions
2. **Production Code**: `src/` for all Python modules
3. **Quick Reference**: `knowledge/` for operational docs
4. **Configuration**: `config/` for service configs
5. **Legacy**: `legacy/` for archived code (not production)

## Navigation

| Need | Location |
|------|----------|
| Understand the system | `ARCHITECTURE.md` → `docs/canonical/` |
| Quick operational reference | `knowledge/*.md` |
| Deploy services | `docker-compose/*.yml` |
| Configure services | `config/` |
| Run scripts | `scripts/` |
| Modify UI | `ui/src/components/` |
| Modify backend | `src/hydra_tools/` |
| Check current state | `STATE.json` |

## Voice Pipeline Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  hydra-wakeword │────▶│  hydra-voice    │────▶│  hydra-stt      │
│  (port 8860)    │     │  (port 8850)    │     │  (port 9001)    │
│  "Hey Hydra"    │     │  Orchestration  │     │  faster-whisper │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │ LiteLLM  │ │  Letta   │ │  Kokoro  │
             │ Gateway  │ │  Agent   │ │   TTS    │
             │ (4000)   │ │  (8283)  │ │  (8880)  │
             └──────────┘ └──────────┘ └──────────┘
```

## CrewAI Agent Crews

| Crew | Purpose | Agents |
|------|---------|--------|
| ResearchCrew | Autonomous web research | Researcher, Analyst, Reporter |
| MonitoringCrew | Cluster health surveillance | HealthMonitor, PerformanceAnalyst, AlertManager |
| MaintenanceCrew | Automated maintenance tasks | Planner, Executor, Validator |

## Key Port Reference

| Port | Service | Node |
|------|---------|------|
| 3000 | Open WebUI | hydra-ai |
| 4000 | LiteLLM | hydra-storage |
| 5000 | TabbyAPI | hydra-ai |
| 8188 | ComfyUI | hydra-compute |
| 8283 | Letta | hydra-storage |
| 8700 | Phase 11 API | hydra-storage |
| 8850 | Voice Interface | hydra-storage |
| 8860 | Wake Word | (device) |
| 8880 | Kokoro TTS | hydra-storage |
| 9001 | STT Service | hydra-compute |

## n8n Workflow Categories

| Category | Workflows | Purpose |
|----------|-----------|---------|
| Monitoring | health-digest, alertmanager-handler, resource-monitor, uptime-kuma-alert-handler | Cluster health surveillance |
| Automation | container-restart-ratelimit, disk-cleanup, gpu-thermal-handler, service-dependency-restart | Auto-remediation |
| Backups | postgres-backup, scheduled-database-backup, qdrant-maintenance | Data protection |
| Intelligence | model-performance-tracker, activity-logger, morning-briefing, model-benchmark-automation, usage-tracking-aggregator | Self-improvement |
| Integration | github-webhook-handler, email-digest-sender, discord-notification-bridge, rss-feed-processor | External systems |
| Voice | voice-command-processor | Voice pipeline routing |
| CrewAI | crewai-task-dispatcher | Multi-agent orchestration |
| Knowledge | knowledge-refresh, learnings-capture, letta-memory-update | Memory management |

## Phase 11 Self-Improvement API Endpoints

| Endpoint Prefix | Purpose |
|-----------------|---------|
| `/diagnosis/*` | Failure analysis, pattern detection |
| `/optimization/*` | Resource utilization analysis |
| `/knowledge/*` | Knowledge lifecycle management |
| `/capabilities/*` | Feature gap tracking |
| `/routing/*` | Intelligent model routing |
| `/preferences/*` | User preference learning |
| `/activity/*` | Unified activity logging |
| `/control/*` | System automation modes |
| `/hardware/*` | Live hardware discovery |

## Operational Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy-intelligence-layer.sh` | Deploy Phase 11 services | `./deploy-intelligence-layer.sh [all\|tools\|voice\|stt]` |
| `configure-uptime-kuma.py` | Setup Uptime Kuma monitors | `python configure-uptime-kuma.py --json -o config.json` |
| `setup-sops.sh` | Initialize SOPS encryption | `./setup-sops.sh` |
| `fix-container-healthchecks.sh` | Apply healthcheck fixes | `./fix-container-healthchecks.sh` |

---
*Last updated: December 14, 2025 - Phase 12 COMPLETE - Intelligence Layer Ready*
