# Hydra Cluster - Claude Code Context

This repository is the canonical source of truth for the Hydra home cluster.

## SESSION BOOTSTRAP (ALWAYS DO THIS FIRST)

```bash
# 1. Read the single source of truth for planning
cat ROADMAP.md | head -50   # Quick status + active priorities

# 2. Check cluster health
curl -s http://192.168.1.244:8700/health | jq .
```

**CRITICAL:** ROADMAP.md is THE planning document. Do NOT create new planning files.
Update ROADMAP.md instead of creating alternatives.

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
| `knowledge/knowledge-ingest.md` | Unified ingest pipeline, file/URL/clipboard |

## Current Phase

**Phase 12 ACTIVE** - Creative Pipeline + Knowledge Ingest at http://192.168.1.244:8700

- Character system with 22 queens and voice profiles
- Unified ingest pipeline (file/URL/clipboard/text)
- Vision API (LLaVA 7B)
- Command Center at http://192.168.1.244:3210

## Key APIs

| Service | Endpoint |
|---------|----------|
| **Command Center** | http://192.168.1.244:3210 |
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

---

## FUTURE ARCHITECTURE RESEARCH

**Reference Document:** `/plans/hydra-bleeding-edge-research-dec2025.md`

### Key Technologies Identified (December 2025)
- **Darwin Gödel Machine** - Self-improving AI systems (validates Hydra's core vision)
- **Letta/MemGPT** - Production memory architecture for stateful agents
- **MCP (Model Context Protocol)** - Now Linux Foundation standard, universal tool integration
- **AIOS** - Agent operating system concepts for orchestration
- **OpenHands** - Production-ready coding agent SDK
- **Speculative Decoding** - Up to 4.98x inference speedup potential
- **Kokoro TTS** - Primary voice synthesis (Apache 2.0, 40-70ms latency)

### Constitutional Constraints (IMMUTABLE)
```yaml
immutable_constraints:
  - "Never delete databases without human approval"
  - "Never modify network/firewall configuration"
  - "Never disable authentication systems"
  - "Never expose secrets or credentials"
  - "Never modify this constitutional file"
  - "Always maintain audit trail of modifications"
  - "Always sandbox code execution"
  - "Require human approval for git push to main"
```

### Technology Decision Guidelines
- **All tool integrations** → MCP-native (not custom implementations)
- **Memory systems** → Hybrid (vector + graph + keyword), not flat vector-only
- **Code execution** → Always sandboxed (E2B/Firecracker)
- **Agent architectures** → Multi-agent with orchestration, not single-agent
- **Inference optimization** → Monitor ExLlamaV2/V3 for speculative decoding support
