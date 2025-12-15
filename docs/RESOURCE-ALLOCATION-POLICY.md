# Hydra Cluster Resource Allocation Policy

## Live Hardware Discovery

Query live hardware status at any time:
```bash
# Full inventory
curl http://192.168.1.244:8700/hardware/inventory

# Quick summary
curl http://192.168.1.244:8700/hardware/summary

# GPU status only
curl http://192.168.1.244:8700/hardware/gpus
```

---

## Node Roles & Resource Allocation

### hydra-ai (192.168.1.250) - Primary Inference

| Resource | Total | Allocated For | Reserved |
|----------|-------|---------------|----------|
| CPU | 24c/48t | LLM inference preprocessing | 100% available |
| RAM | 125GB | Model loading, KV cache | 100% available |
| RTX 5090 | 32GB VRAM | 70B model primary | 100% for inference |
| RTX 4090 | 24GB VRAM | 70B model tensor parallel | 100% for inference |

**Policy:**
- TabbyAPI runs here exclusively
- No other GPU workloads
- ExLlamaV2 tensor parallelism across both GPUs
- Models: midnight-miqu-70B, Llama-3.1-70B, etc.

---

### hydra-compute (192.168.1.203) - Secondary Inference + Creative

| Resource | Total | Allocated For | Reserved |
|----------|-------|---------------|----------|
| CPU | 16c/32t | ComfyUI, Ollama | 100% available |
| RAM | 60GB | Image gen, model cache | 100% available |
| RTX 5070 Ti #0 | 16GB VRAM | ComfyUI / Ollama | Shared |
| RTX 5070 Ti #1 | 16GB VRAM | Ollama overflow / Batch | Flexible |

**Policy:**
- Ollama runs 7B-14B models for fast inference
- ComfyUI for image generation (SDXL, Flux)
- Two separate GPUs = can run inference + image gen simultaneously
- NO tensor parallelism (keep GPUs independent for flexibility)

---

### hydra-storage (192.168.1.244) - Orchestration Hub

| Resource | Total | Allocated For | Reserved |
|----------|-------|---------------|----------|
| CPU | 56c/112t | Container orchestration, agents | 90% for AI workloads |
| RAM | 251GB | Containers (~70GB), KV cache tier (~150GB) | 30GB for Unraid OS |
| Arc A380 | 6GB | Plex transcoding (Quick Sync) | 100% dedicated to Plex |
| Storage | 164TB | Media (120TB), Models (2TB), Other (42TB) | N/A |

**Policy:**
- Arc A380 is EXCLUSIVELY for Plex transcoding
- EPYC cores available for n8n, CrewAI, LangGraph agents
- 150GB+ RAM available for KV cache offloading tier
- All Docker containers run here (60+)

---

## Resource Boundaries (Do NOT Cross)

| Boundary | Reason |
|----------|--------|
| Don't run GPU inference on hydra-storage | Arc A380 is for transcoding only |
| Don't run containers on hydra-ai | Dedicated to TabbyAPI inference |
| Don't run containers on hydra-compute | Dedicated to Ollama/ComfyUI |
| Don't tensor-parallel on hydra-compute | Keep GPUs independent for flexibility |

---

## Monitoring & Alerts

### Key Metrics to Watch

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| hydra-ai VRAM usage | >90% | >95% | Reduce context length or switch model |
| hydra-storage RAM | >200GB | >230GB | Review container memory limits |
| hydra-storage CPU | >80% sustained | >95% | Reduce agent parallelism |
| Storage array | >90% | >95% | Cleanup or expand |

### Prometheus Queries

```promql
# VRAM usage on hydra-ai
(DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)) * 100

# RAM usage on hydra-storage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# CPU usage on hydra-storage
100 - (avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

---

## Capacity Planning

### Current Utilization (Live)
Query: `curl http://192.168.1.244:8700/hardware/inventory`

### Growth Headroom

| Resource | Current | Max Capacity | Headroom |
|----------|---------|--------------|----------|
| Total VRAM | 88GB | 88GB | 0% (maxed) |
| Total RAM | 437GB | 437GB | 0% (maxed) |
| CPU Threads | 192 | 192 | 0% (maxed) |
| Storage | 148TB used | 164TB | 10% (add drives) |

### Upgrade Priorities
1. **Storage** - 90% full, add 20TB+ drives
2. **hydra-compute RAM** - 60GB limits larger models, upgrade to 128GB
3. **hydra-ai RAM** - 125GB is good, but 256GB enables larger KV cache

---

## Agent Orchestration Guidelines

### Recommended Parallelism

| Agent Type | Max Concurrent | Where |
|------------|----------------|-------|
| Research agents | 8 | hydra-storage (EPYC) |
| Development agents | 4 | hydra-storage (EPYC) |
| Creative agents | 2 | hydra-compute (GPU) |
| Monitoring agents | 4 | hydra-storage (EPYC) |

### Resource Limits per Agent

```yaml
# n8n workflow agent limits
agent_limits:
  research:
    max_memory_mb: 2048
    max_cpu_cores: 4
    timeout_minutes: 30
  development:
    max_memory_mb: 4096
    max_cpu_cores: 8
    timeout_minutes: 60
  creative:
    max_memory_mb: 8192  # Needs GPU memory for image gen
    max_cpu_cores: 4
    timeout_minutes: 120
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HYDRA RESOURCE ALLOCATION                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  hydra-ai              hydra-compute         hydra-storage          │
│  ═════════             ═════════════         ═════════════          │
│                                                                      │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐        │
│  │   TabbyAPI  │       │   Ollama    │       │   Docker    │        │
│  │   70B LLMs  │       │   7B-14B    │       │   60+ svcs  │        │
│  │             │       │             │       │             │        │
│  │ RTX 5090+   │       │ 5070Ti x2   │       │ EPYC 7663   │        │
│  │ RTX 4090    │       │ (separate)  │       │ 56 cores    │        │
│  │ 56GB VRAM   │       │ 32GB VRAM   │       │ 251GB RAM   │        │
│  └─────────────┘       └─────────────┘       └─────────────┘        │
│                                                                      │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐        │
│  │  DEDICATED  │       │   ComfyUI   │       │  Arc A380   │        │
│  │   to LLM    │       │  Image Gen  │       │  Plex QSV   │        │
│  │  Inference  │       │             │       │  DEDICATED  │        │
│  └─────────────┘       └─────────────┘       └─────────────┘        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: December 2025*
*Auto-refresh via: `curl http://192.168.1.244:8700/hardware/summary`*
