# HYDRA LEARNINGS

> *Accumulated wisdom from building and operating Hydra*

This document captures insights, patterns, gotchas, and lessons learned. Claude Code should consult this when encountering similar situations and add new learnings after significant discoveries.

---

## How to Use This Document

**Reading:** Before attempting something complex, search this document for related keywords.

**Writing:** After resolving a non-trivial issue or discovering something useful, add an entry:
```markdown
### [Short Title]
**Date:** YYYY-MM-DD
**Context:** What you were trying to do
**Learning:** What you discovered
**Application:** How to apply this in the future
```

---

## Infrastructure Learnings

### ExLlamaV2 is the Only Option for Heterogeneous Tensor Parallelism
**Date:** 2025-12-09
**Context:** Trying to run 70B models across RTX 5090 (32GB) + RTX 4090 (24GB)
**Learning:** ExLlamaV2 + TabbyAPI is the only inference engine that supports tensor parallelism across GPUs with different VRAM sizes. vLLM, Aphrodite, and ExLlamaV3 all require matching GPU configurations.
**Application:** Always use ExLlamaV2 for the 5090+4090 setup. Don't waste time trying vLLM or other engines for this use case.

### 10GbE Changes Everything
**Date:** 2025-12-09
**Context:** Model loading times were frustrating development iteration
**Learning:** With 10GbE backbone achieving 1.1 GB/s NFS throughput, model loading dropped from 5+ minutes to ~30 seconds for 70B models. This transforms the development experience.
**Application:** Always complete network layer before optimizing other things. Fast iteration beats perfect optimization.

### NixOS Atomic Rollbacks are a Superpower
**Date:** 2025-12-08
**Context:** Broke CUDA configuration during driver update
**Learning:** `nixos-rebuild switch --rollback` instantly restored working state. No debugging required.
**Application:** On NixOS nodes, be aggressive with changes. Rollback is cheap. On Unraid (no atomic rollback), be more conservative.

### Unraid Docker vs NixOS Services
**Date:** 2025-12-07
**Context:** Deciding where to run services
**Learning:** 
- **Unraid Docker:** Better for always-on services, databases, things that need persistent storage. Web UI for manual intervention.
- **NixOS systemd:** Better for GPU services, things that need to restart cleanly, reproducible configuration.
**Application:** 
- Databases, orchestration, media → hydra-storage (Unraid)
- Inference, creative tools → hydra-ai/compute (NixOS)

### CUDA Version Mismatches are Silent Killers
**Date:** 2025-12-09
**Context:** TabbyAPI crashed with cryptic errors
**Learning:** PyTorch, ExLlamaV2, and CUDA driver versions must all be compatible. Blackwell GPUs (5090) need CUDA 12.8+. Check nvidia-smi first, then verify PyTorch CUDA version.
**Application:** When inference fails, first check: `nvidia-smi` (driver), `python -c "import torch; print(torch.version.cuda)"` (PyTorch CUDA).

---

## Operational Learnings

### Health Checks Need Timeouts
**Date:** 2025-12-08
**Context:** Health check script hung indefinitely when service was in bad state
**Learning:** Always use `--max-time` with curl: `curl -s --max-time 5 http://service/health`
**Application:** All health check commands should have 3-5 second timeouts.

### SSH Connection Reuse Speeds Everything Up
**Date:** 2025-12-07
**Context:** Running multiple SSH commands to same host was slow
**Learning:** SSH ControlMaster allows connection reuse:
```
# ~/.ssh/config
Host hydra-*
  ControlMaster auto
  ControlPath ~/.ssh/sockets/%r@%h-%p
  ControlPersist 600
```
**Application:** Ensure SSH config is set up on any machine running Claude Code.

### Log Locations Matter
**Date:** 2025-12-06
**Context:** Debugging service failure with no obvious errors
**Learning:**
- NixOS services: `journalctl -u service-name -f`
- Docker containers: `docker logs container-name -f`
- TabbyAPI: stdout in journalctl
- ComfyUI: stdout + `~/.comfyui/comfyui.log`
**Application:** First debug step is always checking logs in the right place.

---

## Model Learnings

### EXL2 Quantization Quality vs Size
**Date:** 2025-12-05
**Context:** Choosing quantization level for 70B model
**Learning:**
- 3.5bpw: Fits in 56GB VRAM with room for context, minimal quality loss
- 4.0bpw: Higher quality but tighter fit
- 2.5bpw: Noticeable quality degradation, only for fitting larger models
**Application:** Default to 3.5bpw for 70B models on this setup. Go to 4.0bpw only if quality issues observed.

### Model Loading Order Matters
**Date:** 2025-12-06
**Context:** TabbyAPI failed to load model after ComfyUI loaded diffusion model
**Learning:** GPU VRAM is first-come-first-served. Load large LLMs before starting image generation services.
**Application:** Service startup order: TabbyAPI → Ollama → ComfyUI

### Context Window vs VRAM Tradeoff
**Date:** 2025-12-05
**Context:** Running out of VRAM mid-conversation
**Learning:** With tensor parallelism, context uses VRAM on both GPUs. 8K context is safe. 16K possible but tight. 32K will OOM.
**Application:** Configure TabbyAPI with `expect_cache_tokens` based on expected context size. Don't promise more than 16K context.

---

## Creative Pipeline Learnings

### ComfyUI API Workflow
**Date:** 2025-12-04
**Context:** Automating image generation
**Learning:**
1. Export workflow from UI as `workflow_api.json` (not regular `workflow.json`)
2. POST to `/prompt` endpoint with workflow JSON
3. Poll `/history/{prompt_id}` for completion
4. Images saved to output directory with predictable naming
**Application:** Always export API format. Regular workflow format won't work with API.

### Character Consistency Techniques
**Date:** 2025-12-04
**Context:** Generating consistent character across multiple images
**Learning:**
- **Best:** Train LoRA with 15-30 reference images (1500-3000 steps)
- **Good:** IP-Adapter with face reference image
- **Quick:** InstantID for face-only consistency
- **Combine:** LoRA for body/style + InstantID for face
**Application:** For Empire of Broken Queens, train LoRAs for main queens, use InstantID for NPCs.

### TTS Voice Matching
**Date:** 2025-12-03
**Context:** Generating character voices
**Learning:**
- Kokoro: Fast (210x realtime) but limited voice control
- F5-TTS: Zero-shot cloning from seconds of audio
- Best workflow: Generate sample with F5-TTS from voice reference, use that for consistent voice
**Application:** Create voice reference clips for each queen, use F5-TTS for cloning consistency.

---

## Agent/Automation Learnings

### n8n Webhook Reliability
**Date:** 2025-12-08
**Context:** Alerts not triggering workflows
**Learning:** n8n webhooks can miss events if n8n restarts during delivery. Use Redis queue for critical alerts.
**Application:** For self-healing workflows, push alerts to Redis first, then have n8n poll Redis.

### Rate Limiting Remediation
**Date:** 2025-12-07
**Context:** Service restart loop
**Learning:** Without rate limiting, a flapping service can trigger remediation repeatedly, making things worse. 
**Application:** Always implement: max 3 remediations per hour per service, exponential backoff, human escalation after failures.

---

## Working with Claude Code Learnings

### Context Window Management
**Date:** 2025-12-10
**Context:** Long sessions losing early context
**Learning:** Claude Code has limited context. For long sessions:
- Update STATE.json frequently
- Add learnings to this file
- Reference documents by filename rather than including content
**Application:** At natural breakpoints, persist state to files.

### Batch Commands for Efficiency
**Date:** 2025-12-09
**Context:** Many small operations taking too long
**Learning:** Chain commands with `&&` for efficiency. Claude Code can run batches:
```bash
ssh host "cmd1 && cmd2 && cmd3"
```
**Application:** Prefer consolidated commands over many small ones.

### NixOS Rebuild Strategy
**Date:** 2025-12-08
**Context:** Testing NixOS configuration changes
**Learning:** 
- `nixos-rebuild test`: Activates config but doesn't make it boot default
- `nixos-rebuild switch`: Makes it permanent
- `nixos-rebuild build`: Just builds, doesn't activate (safe to verify)
**Application:** Use `build` first to catch errors, then `switch` when confident.

---

## Adding New Learnings

When Claude Code discovers something worth remembering:

1. Identify the category (Infrastructure, Operational, Model, Creative, Agent, Claude Code)
2. Add entry with Date, Context, Learning, Application
3. Keep entries concise but complete
4. Cross-reference other documents if relevant

**Template:**
```markdown
### [Descriptive Title]
**Date:** YYYY-MM-DD
**Context:** What situation led to this discovery
**Learning:** The key insight or fact discovered
**Application:** How to use this knowledge in the future
```

---

## Session Learnings: 2025-12-10

### NixOS Firewall: Temporary vs Permanent Rules
**Date:** 2025-12-10
**Context:** Prometheus couldn't reach node exporters after reboot
**Learning:** `iptables -I nixos-fw 1 -p tcp --dport PORT -j nixos-fw-accept` is temporary. For permanent rules, must edit `/etc/nixos/configuration.nix` and run `nixos-rebuild switch`.
**Application:** Always add ports to `networking.firewall.allowedTCPPorts` in NixOS config for persistence.

### User Systemd Services Die on SSH Disconnect
**Date:** 2025-12-10
**Context:** nvidia-metrics-exporter kept dying after SSH session ended
**Learning:** User systemd services (`~/.config/systemd/user/`) are killed when SSH session ends unless lingering is enabled: `sudo loginctl enable-linger username`
**Application:** Always run `enable-linger` when setting up user services that must persist.

### Python TCPServer Port Reuse
**Date:** 2025-12-10
**Context:** nvidia-metrics-exporter crashed with "Address already in use" on restart
**Learning:** `socketserver.TCPServer` doesn't set SO_REUSEADDR by default. Create subclass with `allow_reuse_address = True`. Also need to kill orphaned processes and wait ~70s for TIME_WAIT to clear.
**Application:** Always use `ReuseAddrTCPServer` for Python HTTP servers that may restart.

### Container Version Downgrade Schema Issues
**Date:** 2025-12-10
**Context:** Pinned Qdrant and Portainer to older versions, they crashed on startup
**Learning:** Services with persistent state (Qdrant, Portainer, AdGuard) may create data with schemas not compatible with older versions. Cannot downgrade these safely.
**Application:** For stateful services, either keep on latest or freeze early. Don't downgrade after data is created.

### LiteLLM Authentication Required
**Date:** 2025-12-10
**Context:** LiteLLM API calls failing with 401 Unauthorized
**Learning:** LiteLLM requires `Authorization: Bearer MASTER_KEY` header. Key found in container env vars or config.yaml. Master key: `sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7`
**Application:** Always include auth header when calling LiteLLM API.

### Qdrant Collection Dimensions Must Match
**Date:** 2025-12-10
**Context:** RAG pipeline failing to insert vectors
**Learning:** Qdrant collection dimensions must match embedding model output. nomic-embed-text produces 768-dim, not 1536-dim (OpenAI). Cannot change dimensions on existing collection - must delete and recreate.
**Application:** Check embedding model dimensions before creating Qdrant collections.

### Docker Network for Service Discovery
**Date:** 2025-12-10
**Context:** Prometheus couldn't reach internal Docker services after container recreate
**Learning:** Services on same Docker network can reach each other by container name. After recreating Prometheus, needed `docker network connect hydra-network hydra-prometheus`.
**Application:** Verify network membership after container recreation.

### Shell Escaping in SSH
**Date:** 2025-12-10
**Context:** For loops via SSH expanding variables incorrectly
**Learning:** Use single quotes for SSH commands with shell constructs: `ssh host 'for c in a b; do echo $c; done'`. Double quotes expand on the local side.
**Application:** Single-quote SSH command strings that contain shell variables.

### NixOS Python Path
**Date:** 2025-12-10
**Context:** User systemd service couldn't find python3
**Learning:** NixOS stores binaries in /nix/store. For systemd services, use full path: `/run/current-system/sw/bin/python3`
**Application:** Always use full paths in NixOS systemd services.

### Prometheus Alert Rules Volume Mount
**Date:** 2025-12-10
**Context:** Alert rules not loading in Prometheus
**Learning:** File-specific volume mounts (`-v file.yml:/etc/prometheus/file.yml`) require the source file to exist BEFORE container creation. Mount parent directory or ensure file exists first.
**Application:** Create config files before container, or mount directories.

### Blackwell GPU (sm_120) Exporter Issues
**Date:** 2025-12-10
**Context:** DCGM and nvidia_gpu_exporter crash on RTX 5070 Ti/5090
**Learning:** Blackwell GPUs use sm_120 compute capability. DCGM and nvidia_gpu_exporter don't support this yet. Must use custom nvidia-smi script exporter.
**Application:** For RTX 50 series, use nvidia-smi parsing until official exporters add support.

### Uptime Kuma API Setup
**Date:** 2025-12-10
**Context:** Needed to configure Uptime Kuma monitors programmatically
**Learning:** Use `uptime-kuma-api` Python package with `api.setup()` for first-time setup. Must run from within Docker network to reach service by container name.
**Application:** Use Python API client from container on same network for Uptime Kuma automation.

### Docker Image Pruning
**Date:** 2025-12-10
**Context:** Docker storage full preventing image pulls
**Learning:** `docker image prune -a -f --filter "until=24h"` removes unused images. `docker system df` shows space usage.
**Application:** Run image prune when "no space left on device" during pulls.

### Letta API Model Handles Require Full Format
**Date:** 2025-12-10
**Context:** Creating Letta agent failed with "embedding model not supported by ollama"
**Learning:** Letta embedding model handles need full format including tag: `ollama/nomic-embed-text:latest` not just `ollama/nomic-embed-text`. Check `/v1/models/embedding` endpoint for exact handles.
**Application:** Always query Letta models endpoint first to get exact handle format.

### Letta SECURE Mode Auth Behavior
**Date:** 2025-12-10
**Context:** Agent creation failed with 401 Unauthorized despite valid Bearer token
**Learning:** Letta with `SECURE=true` requires `Authorization: Bearer PASSWORD` header. Health endpoint works with auth but some endpoints may require different scopes. Temporarily disabling SECURE mode (`SECURE=false` in docker-compose) allows agent creation, then re-enable.
**Application:** For initial Letta agent setup, disable SECURE mode, create agent, then re-enable.

### Letta Agent Memory Blocks Persist in pgvector
**Date:** 2025-12-10
**Context:** Created Hydra Steward agent with custom memory blocks
**Learning:** Letta agents with `memory_blocks` parameter store persistent context. Block labels (persona, human, custom) become keys for core_memory tools. Agent ID persists across container restarts when using pgvector DB.
**Application:** Design memory blocks for the information the agent needs to remember. Use descriptive `description` fields - agent uses these to decide how to read/write blocks.

### Grafana API Shell Escaping with Special Characters
**Date:** 2025-12-10
**Context:** Dashboard creation via curl failed when password contained `!`
**Learning:** Bash heredocs with `!` in passwords cause expansion issues. Write JSON to temp file first, then use `curl -d @/tmp/file.json` instead of inline JSON.
**Application:** For API calls with complex auth, write payload to file and use `-d @file`.

### Open WebUI Functions Require Web UI Installation
**Date:** 2025-12-10
**Context:** Attempting to connect Letta to Open WebUI for persistent memory chat
**Learning:** Open WebUI functions/pipes are installed via the admin web UI at `/admin/functions`, not via filesystem. Community [Letta Agent Function](https://openwebui.com/f/haervwe/letta_agent) provides SSE streaming, tool call handling, and memory persistence. Configuration: `Agent_ID`, `API_URL` (http://192.168.1.244:8283), `API_Token`.
**Application:** For Letta-Open WebUI integration, user must manually install function via web UI and configure with hydra-steward agent ID.

### Neo4j APOC Plugin via Environment Variable
**Date:** 2025-12-10
**Context:** Deploying Neo4j with APOC procedures for graph algorithms
**Learning:** Neo4j 5.x community edition enables APOC via `NEO4J_PLUGINS=["apoc"]` environment variable. Also need `NEO4J_dbms_security_procedures_unrestricted=apoc.*` to allow all APOC procedures.
**Application:** Include both env vars in Neo4j docker-compose for full APOC functionality.

### CrewAI Container Pattern for Hydra
**Date:** 2025-12-10
**Context:** Deploying CrewAI as persistent container on hydra-storage
**Learning:** CrewAI works well as long-running container with `tail -f /dev/null` entrypoint, pip installing packages at startup. Use `docker exec` to run crews. Cron jobs in host for scheduling (not container cron). Connect via hydra-network to access LiteLLM, Qdrant, Neo4j.
**Application:** Pattern: persistent Python container + mounted scripts + exec for runs + host cron for scheduling.

### Knowledge Import Pattern: Qdrant + Neo4j
**Date:** 2025-12-10
**Context:** Building knowledge base from scratch for RAG
**Learning:** Two-tier approach: Qdrant for semantic search (vectors via Ollama nomic-embed-text), Neo4j for relationship queries (nodes, edges for dependencies). Import via Docker python container with network access. Run ephemeral containers for one-off scripts.
**Application:** Use `docker run --rm --network hydra-network -v script.py:/app/script.py python:3.11-slim` pattern for import scripts.

### MCP Server as Unified Control Plane
**Date:** 2025-12-10
**Context:** Creating unified API for Claude Code to interact with cluster
**Learning:** FastAPI-based MCP Server (:8600) aggregates Prometheus metrics, Letta memory, CrewAI crews, Qdrant search, and LiteLLM inference. Single endpoint `/cluster/status` provides comprehensive health view. Use `httpx.AsyncClient` for non-blocking service calls.
**Application:** MCP Server pattern: single entrypoint with async clients to backend services, env-based configuration for service URLs.

### Unraid Docker vdisk Size Limits
**Date:** 2025-12-11
**Context:** Unable to build new Docker images - "no space left on device" during npm install
**Learning:** Unraid Docker runs on a fixed-size vdisk (50GB default on /dev/loop2). With 52 containers and ~47GB of images, disk fills completely. Large images like docling-serve (12.9GB), kokoro-fastapi (5.6GB), open-webui (4.3GB) consume most space. `docker image prune -af` only reclaims unused images. Running images can't be removed.
**Application:** Either expand vdisk in Unraid settings, configure Docker to use alternate storage like NVMe (/mnt/hpc_nvme/docker already exists), or be strategic about which images to keep. Check `df -h /var/lib/docker` before building.

### Control Plane UI with Next.js App Router
**Date:** 2025-12-11
**Context:** Creating cyberpunk-themed dashboard for Hydra cluster control
**Learning:** Next.js 14 App Router with Tailwind CSS provides fast UI development. Key components: client-side data fetching with SWR/useEffect for real-time updates, Tailwind for rapid styling, environment variables for API URLs. Cyberpunk aesthetic: dark backgrounds (#0a0a0f), neon accents (cyan/magenta/green), glow effects via box-shadow, monospace fonts.
**Application:** Pattern: `globals.css` for base styles + custom colors in `tailwind.config.ts`, reusable components with status props, 5-second polling for real-time data.

---

*This document grows with experience. Consult it before repeating mistakes.*
*Last updated: December 2025*
