# Hydra Cluster - Claude Code Context

This repository is the canonical source of truth for the Hydra home cluster.

## Quick Reference

| Node | IP | Role |
|------|----|----|
| hydra-ai | 192.168.1.250 | Primary inference (TabbyAPI) |
| hydra-compute | 192.168.1.203 | Ollama, ComfyUI |
| hydra-storage | 192.168.1.244 | Docker services, NFS |

## Rules

Self-guarding rules are in `.claude/rules/`. Key rules:
- **Discovery before action** - Read knowledge files first
- **Canonical IPs only** - Never use 192.168.1.251, .175, or .100
- **NixOS is declarative** - Use configuration.nix, not direct installs
- **Test before commit** - Dry-run, then verify

## Knowledge Files

Read these BEFORE implementing changes:

| File | Domain |
|------|--------|
| `knowledge/infrastructure.md` | Hardware, network, ports |
| `knowledge/inference-stack.md` | TabbyAPI, ExLlamaV2, LiteLLM |
| `knowledge/databases.md` | PostgreSQL, Qdrant, Redis |
| `knowledge/models.md` | Model selection, downloads |
| `knowledge/observability.md` | Prometheus, Grafana, Loki |
| `knowledge/automation.md` | n8n, workflows |

## Current Phase

**Phase 11 COMPLETE** - Self-improvement tools at http://192.168.1.244:8700

See `docs/phase-11-self-improvement.md` for details.

## Key APIs

| Service | Endpoint |
|---------|----------|
| Hydra Tools API | http://192.168.1.244:8700 |
| TabbyAPI | http://192.168.1.250:5000 |
| Ollama | http://192.168.1.203:11434 |
| n8n | http://192.168.1.244:5678 |

## Reference Files (query on demand, not auto-loaded)

These files exist but are NOT auto-loaded due to size:
- `docs/canonical/00-system-reality/HYDRA_FILE_MANIFEST.csv` (124KB)
- `docs/canonical/00-system-reality/Hydra_Snapshot_*.txt` (16KB+)
- `docs/session-archive/` (historical session logs)

## Legacy

Prototypes and old code are in `/legacy/`. Do not deploy from `/legacy/`.
