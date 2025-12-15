# Hydra AI System Architecture v3.0
## Comprehensive Redesign with Corrected Hardware Specs

**Created:** December 2025
**Method:** ULTRATHINK deep analysis with live hardware discovery

---

## Executive Summary

This document represents a complete redesign of the Hydra AI system architecture based on:
1. **Live hardware discovery** (not outdated documentation)
2. **Corrected GPU inventory** (hydra-compute has 2x RTX 5070 Ti, not 5070 Ti + 3060)
3. **Proper utilization of 251GB RAM** on hydra-storage
4. **Optimal multi-GPU configuration strategies** based on 2025 research
5. **EPYC 7663 orchestration capabilities**

### Key Corrections from Previous Designs

| Component | Previous Understanding | **Actual (Verified Live)** |
|-----------|----------------------|---------------------------|
| hydra-compute GPUs | RTX 5070 Ti + RTX 3060 | **2x RTX 5070 Ti (32GB total)** |
| Total Cluster VRAM | 84GB | **88GB** |
| hydra-storage RAM | "Available" | **251GB (180GB free for caching)** |
| Arc A380 role | "Light inference" | **Dedicated Plex transcoding only** |

---

## Part 1: Hardware Topology (Verified)

### Live Discovery Endpoint
```bash
curl http://192.168.1.244:8700/hardware/summary
```

### Verified Hardware Specifications

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         HYDRA CLUSTER - VERIFIED SPECS                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ hydra-ai (192.168.1.250) - PRIMARY INFERENCE                                ││
│  │                                                                              ││
│  │ CPU: AMD Ryzen Threadripper 7960X                                           ││
│  │      24 cores / 48 threads @ 5.3GHz boost                                   ││
│  │                                                                              ││
│  │ RAM: 125GB DDR5                                                             ││
│  │                                                                              ││
│  │ GPU 0: NVIDIA GeForce RTX 5090                                              ││
│  │        32GB GDDR7, Blackwell, sm_120, compute 12.0                          ││
│  │        PCIe 5.0 x16                                                         ││
│  │                                                                              ││
│  │ GPU 1: NVIDIA GeForce RTX 4090                                              ││
│  │        24GB GDDR6X, Ada Lovelace, sm_89, compute 8.9                        ││
│  │        PCIe 4.0 x16                                                         ││
│  │                                                                              ││
│  │ Combined VRAM: 56GB (Tensor Parallel via ExLlamaV2)                         ││
│  │                                                                              ││
│  │ Storage: 4TB Samsung 990 PRO + 4TB Crucial T700 + 4TB Crucial P3 + 1TB EVO  ││
│  │ Network: 10GbE (confirmed 10000Mb/s full duplex)                            ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ hydra-compute (192.168.1.203) - SECONDARY INFERENCE + CREATIVE              ││
│  │                                                                              ││
│  │ CPU: AMD Ryzen 9 9950X                                                      ││
│  │      16 cores / 32 threads @ 5.7GHz boost                                   ││
│  │                                                                              ││
│  │ RAM: 60GB DDR5                                                              ││
│  │                                                                              ││
│  │ GPU 0: NVIDIA GeForce RTX 5070 Ti                                           ││
│  │        16GB GDDR7, Blackwell, sm_120, compute 12.0                          ││
│  │                                                                              ││
│  │ GPU 1: NVIDIA GeForce RTX 5070 Ti  ← IDENTICAL (enables TP=2 option)        ││
│  │        16GB GDDR7, Blackwell, sm_120, compute 12.0                          ││
│  │                                                                              ││
│  │ Combined VRAM: 32GB (can TP=2 for 14B+ or run separate for concurrency)     ││
│  │                                                                              ││
│  │ Storage: 3x 1TB Samsung 990 EVO Plus NVMe                                   ││
│  │ Network: 10GbE                                                              ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ hydra-storage (192.168.1.244) - ORCHESTRATION HUB                           ││
│  │                                                                              ││
│  │ CPU: AMD EPYC 7663                                                          ││
│  │      56 cores / 112 threads @ 3.5GHz boost                                  ││
│  │      256MB L3 Cache                                                         ││
│  │                                                                              ││
│  │ RAM: 251GB DDR4 ECC                                                         ││
│  │      ~70GB in use (containers)                                              ││
│  │      ~180GB available for KV cache tier                                     ││
│  │                                                                              ││
│  │ GPU: Intel Arc A380 (DEDICATED to Plex Quick Sync - NOT for AI)             ││
│  │                                                                              ││
│  │ Storage: 164TB array (90% full - 148TB used)                                ││
│  │          ~120TB media, ~2TB AI models, ~25TB other                          ││
│  │                                                                              ││
│  │ Network: Dual 10GbE bonded (LACP)                                           ││
│  │ Containers: 60+ Docker services                                             ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
│  CLUSTER TOTALS:                                                                 │
│  ├── CPU Cores: 96 physical (192 threads)                                       │
│  ├── RAM: 437GB total                                                           │
│  ├── VRAM: 88GB total (56GB hydra-ai + 32GB hydra-compute)                      │
│  └── Storage: 164TB + 13TB NVMe                                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Optimal GPU Configuration Strategy

Based on research from [DigitalOcean](https://www.digitalocean.com/community/tutorials/splitting-llms-across-multiple-gpus), [DatabaseMart](https://www.databasemart.com/blog/vllm-distributed-inference-optimization-guide), and [AMD ROCm Blog](https://rocm.blogs.amd.com/artificial-intelligence/tensor-parallelism/README.html):

### hydra-ai: Heterogeneous Tensor Parallelism (RTX 5090 + RTX 4090)

**Configuration:** ExLlamaV2 with `tensor_parallel: true`

ExLlamaV2 is the **only** inference engine that properly supports tensor parallelism across heterogeneous GPUs (different VRAM sizes). This is critical because:
- RTX 5090: 32GB GDDR7
- RTX 4090: 24GB GDDR6X
- Combined: 56GB addressable VRAM

```yaml
# /opt/tabbyapi/config.yml (optimal configuration)
network:
  host: 0.0.0.0
  port: 5000

model:
  model_dir: /mnt/models/exl2
  tensor_parallel: true
  gpu_split_auto: true  # Let ExLlamaV2 calculate optimal split
  max_seq_len: 32768
  cache_mode: FP16

# Model recommendations for 56GB:
# - 70B @ 4.0bpw (~52GB) - highest quality, 32K context
# - 70B @ 3.5bpw (~45GB) - good quality, 48K+ context possible
# - 70B @ 3.0bpw (~38GB) - acceptable, 64K+ context possible
```

**Why NOT vLLM or llama.cpp here:**
- vLLM requires identical GPUs for TP
- llama.cpp layer splitting is slower than ExLlamaV2 TP
- ExLlamaV2 specifically optimizes for heterogeneous consumer GPUs

### hydra-compute: Flexible Dual-GPU Strategy (2x RTX 5070 Ti)

Based on [research findings](https://www.databasemart.com/blog/vllm-gpu-benchmark-dual-rtx4090):

> "For 7B models, running separate inference instances per GPU yields better throughput than tensor parallelism due to PCIe communication overhead."

**Recommended Configuration: Dual Ollama Instances**

```bash
# Instance 1 on GPU 0 (port 11434)
CUDA_VISIBLE_DEVICES=0 ollama serve

# Instance 2 on GPU 1 (port 11435)
CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=0.0.0.0:11435 ollama serve
```

**Load Balancing via Nginx:**

```nginx
# /etc/nginx/conf.d/ollama-lb.conf
upstream ollama_backend {
    least_conn;
    server 127.0.0.1:11434 weight=1;
    server 127.0.0.1:11435 weight=1;
}

server {
    listen 11400;
    location / {
        proxy_pass http://ollama_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

**When to use TP=2 instead:**
- For 14B+ models that benefit from pooled VRAM
- For single-user scenarios where latency matters more than throughput
- For models like DeepSeek-R1-Distill-14B (benchmarked at 939 tok/s on 2x4090)

### Model Placement Strategy

| Model Size | Optimal Location | Configuration | Use Case |
|------------|------------------|---------------|----------|
| 70B+ | hydra-ai | ExLlamaV2 TP (5090+4090) | Complex reasoning, analysis |
| 14B-32B | hydra-compute | Ollama TP=2 or single GPU | Medium complexity |
| 7B-8B | hydra-compute | Dual Ollama instances | Fast responses, high concurrency |
| 3B | hydra-compute | Single GPU | Embeddings, classification |
| Embeddings | hydra-compute | Either GPU | nomic-embed-text, bge |

---

## Part 3: Memory Architecture & KV Cache Tier

Based on [NVIDIA's KV cache research](https://developer.nvidia.com/blog/accelerate-large-scale-llm-inference-and-kv-cache-offload-with-cpu-gpu-memory-sharing/):

> "The size of KV cache for 128K input tokens for Llama3-70B is about 40GB, and TTFT is about 19 seconds on 4x H100s."

### hydra-storage as KV Cache Tier

With 180GB+ RAM available, hydra-storage can serve as a distributed KV cache tier:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MEMORY HIERARCHY                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  L1: GPU VRAM (88GB total)                                                      │
│  ├── RTX 5090: 32GB - Active KV cache for current inference                    │
│  ├── RTX 4090: 24GB - Active KV cache (tensor parallel)                        │
│  └── 2x 5070 Ti: 32GB - Active contexts for 7B-14B models                      │
│                                                                                  │
│  L2: CPU RAM - KV Cache Overflow (hydra-storage: 180GB available)               │
│  ├── Semantic cache: Embeddings for common queries (~20GB)                      │
│  ├── KV cache tier: Evicted contexts for quick reload (~100GB)                  │
│  ├── Model weight staging: Pre-loaded model weights (~40GB)                     │
│  └── Buffer: System overhead (~20GB)                                            │
│                                                                                  │
│  L3: NVMe Storage (hydra-ai: 13TB, hydra-compute: 3TB)                          │
│  └── Cold model storage, context snapshots                                      │
│                                                                                  │
│  L4: Network Storage (hydra-storage: 164TB)                                     │
│  └── Model repository, datasets, archives                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Implementing CPU RAM as Cache Tier

**Option 1: LMCache (Recommended)**

```python
# LMCache configuration for hydra-storage
import os
os.environ["LMCACHE_CHUNK_SIZE"] = "256"
os.environ["LMCACHE_LOCAL_CPU"] = "True"
os.environ["LMCACHE_MAX_LOCAL_CPU_SIZE"] = "150.0"  # 150GB of 180GB available
```

**Option 2: Redis with Large Memory**

```yaml
# redis.conf for KV caching
maxmemory 100gb
maxmemory-policy allkeys-lru
appendonly yes
```

**Option 3: Semantic Cache Layer**

```python
# Semantic caching for repeated queries
from qdrant_client import QdrantClient

class SemanticCache:
    def __init__(self):
        self.client = QdrantClient("192.168.1.244:6333")
        self.collection = "query_cache"
        self.similarity_threshold = 0.92

    async def get_cached_response(self, query_embedding):
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            limit=1,
            score_threshold=self.similarity_threshold
        )
        if results:
            return results[0].payload["response"]
        return None
```

---

## Part 4: EPYC 7663 Orchestration Architecture

Based on [AMD's AI orchestration guidance](https://www.amd.com/en/blogs/2025/maximizing-ai-performance-the-role-of-amd-epyc-9575f-cpus.html):

> "The CPU plays a vital role in managing the control plane, facilitating communication between GPU nodes."

### Core Allocation Strategy

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    EPYC 7663 CORE ALLOCATION (56c/112t)                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  RESERVED FOR SYSTEM (8 cores / 16 threads)                                     │
│  ├── Cores 0-3: Unraid OS, kernel, interrupts                                   │
│  └── Cores 4-7: Docker daemon, container orchestration                          │
│                                                                                  │
│  RESERVED FOR CRITICAL SERVICES (12 cores / 24 threads)                         │
│  ├── Cores 8-11: PostgreSQL (4 cores)                                           │
│  ├── Cores 12-15: Redis + Qdrant (4 cores)                                      │
│  └── Cores 16-19: Prometheus + Loki + Grafana (4 cores)                         │
│                                                                                  │
│  AGENT ORCHESTRATION POOL (24 cores / 48 threads)                               │
│  ├── Cores 20-27: n8n workflow workers (8 cores, ~4 parallel workflows)         │
│  ├── Cores 28-35: CrewAI agent pool (8 cores, ~4 concurrent crews)              │
│  └── Cores 36-43: LangGraph executors (8 cores, ~4 graph executions)            │
│                                                                                  │
│  BURST/FLEXIBLE POOL (12 cores / 24 threads)                                    │
│  └── Cores 44-55: Overflow, batch processing, CPU inference fallback            │
│                                                                                  │
│  TOTAL AGENT CAPACITY:                                                          │
│  ├── Sustained: 12 parallel agents                                              │
│  └── Burst: 20+ parallel agents (using flexible pool)                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Docker CPU Pinning

```yaml
# docker-compose.yml example with CPU pinning
services:
  n8n:
    cpuset: "20-27"
    mem_limit: 8g

  crewai:
    cpuset: "28-35"
    mem_limit: 16g

  postgres:
    cpuset: "8-11"
    mem_limit: 32g
```

---

## Part 5: Inference Routing Architecture

### LiteLLM Configuration (Updated)

```yaml
# /mnt/user/appdata/hydra-stack/litellm/config.yaml
model_list:
  # === PRIMARY 70B INFERENCE (hydra-ai) ===
  - model_name: "gpt-4"
    litellm_params:
      model: "openai/default"
      api_base: "http://192.168.1.250:5000/v1"
    model_info:
      max_tokens: 32768
      description: "70B model on RTX 5090+4090 tensor parallel"

  - model_name: "llama-70b"
    litellm_params:
      model: "openai/default"
      api_base: "http://192.168.1.250:5000/v1"

  # === FAST 7B INFERENCE (hydra-compute, load balanced) ===
  - model_name: "gpt-3.5-turbo"
    litellm_params:
      model: "ollama/qwen2.5:7b"
      api_base: "http://192.168.1.203:11400"  # Nginx LB
    model_info:
      description: "7B model, load balanced across 2x RTX 5070 Ti"

  - model_name: "llama-7b"
    litellm_params:
      model: "ollama/llama3.2:latest"
      api_base: "http://192.168.1.203:11400"

  # === CODE MODELS ===
  - model_name: "codellama"
    litellm_params:
      model: "ollama/qwen2.5-coder:7b"
      api_base: "http://192.168.1.203:11434"  # GPU 0

  # === EMBEDDINGS ===
  - model_name: "text-embedding-ada-002"
    litellm_params:
      model: "ollama/nomic-embed-text"
      api_base: "http://192.168.1.203:11435"  # GPU 1

router_settings:
  routing_strategy: "usage-based-routing"
  enable_pre_call_checks: true
```

### RouteLLM Classification

```python
# Updated routing rules based on actual hardware
ROUTING_RULES = {
    "simple": {
        "model": "qwen2.5-7b",
        "backend": "http://192.168.1.203:11400",  # LB'd Ollama
        "description": "Greetings, simple questions, translations"
    },
    "complex": {
        "model": "midnight-miqu-70b",
        "backend": "http://192.168.1.250:5000",  # TabbyAPI
        "description": "Analysis, reasoning, long-form content"
    },
    "code": {
        "model": "qwen2.5-coder-7b",
        "backend": "http://192.168.1.203:11434",  # GPU 0
        "description": "Code generation, debugging, review"
    },
    "creative": {
        "model": "midnight-miqu-70b",
        "backend": "http://192.168.1.250:5000",
        "description": "Creative writing, roleplay, storytelling"
    }
}
```

---

## Part 6: Service Architecture

### Container Distribution

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SERVICE DISTRIBUTION                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  hydra-ai (192.168.1.250)                                                       │
│  ├── TabbyAPI (port 5000) - ExLlamaV2 inference                                 │
│  ├── Open WebUI (port 3000) - Chat interface                                    │
│  ├── Node Exporter (port 9100) - Metrics                                        │
│  └── DCGM Exporter (port 9835) - GPU metrics                                    │
│                                                                                  │
│  hydra-compute (192.168.1.203)                                                  │
│  ├── Ollama Instance 1 (port 11434) - GPU 0                                     │
│  ├── Ollama Instance 2 (port 11435) - GPU 1                                     │
│  ├── Nginx LB (port 11400) - Load balancer                                      │
│  ├── ComfyUI (port 8188) - Image generation                                     │
│  ├── Node Exporter (port 9100) - Metrics                                        │
│  └── nvidia-smi Exporter (port 9835) - GPU metrics                              │
│                                                                                  │
│  hydra-storage (192.168.1.244) - 60+ containers including:                      │
│  ├── ORCHESTRATION                                                              │
│  │   ├── n8n (port 5678) - Workflow automation                                  │
│  │   ├── hydra-tools-api (port 8700) - Self-improvement + hardware discovery    │
│  │   ├── LiteLLM (port 4000) - API gateway                                      │
│  │   └── Letta (port 8283) - Long-term memory                                   │
│  ├── DATABASES                                                                  │
│  │   ├── PostgreSQL (port 5432) - Primary database                              │
│  │   ├── Redis (port 6379) - Cache + pub/sub                                    │
│  │   ├── Qdrant (port 6333) - Vector database                                   │
│  │   └── MinIO (port 9000) - Object storage                                     │
│  ├── OBSERVABILITY                                                              │
│  │   ├── Prometheus (port 9090) - Metrics                                       │
│  │   ├── Grafana (port 3003) - Dashboards                                       │
│  │   ├── Loki (port 3100) - Logs                                                │
│  │   └── Alertmanager (port 9093) - Alerts                                      │
│  ├── AI SERVICES                                                                │
│  │   ├── SearXNG (port 8888) - Search                                           │
│  │   ├── Firecrawl (port 3005) - Web scraping                                   │
│  │   ├── Kokoro TTS (port 8880) - Voice synthesis                               │
│  │   └── Perplexica (port 3030) - AI search                                     │
│  ├── MEDIA (uses Arc A380 for transcoding)                                      │
│  │   ├── Plex (port 32400)                                                      │
│  │   ├── *Arr stack (Sonarr, Radarr, etc.)                                      │
│  │   └── Stash (port 9999)                                                      │
│  └── HOME AUTOMATION                                                            │
│      └── Home Assistant (port 8123)                                             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 7: Autonomous Agent Architecture

### Agent Orchestration Framework

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      AUTONOMOUS AGENT ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                          ┌─────────────────────┐                                │
│                          │  TYPHON ORCHESTRATOR │                                │
│                          │  (hydra-storage)     │                                │
│                          │  EPYC 7663 + 180GB   │                                │
│                          └──────────┬──────────┘                                │
│                                     │                                            │
│           ┌─────────────────────────┼─────────────────────────┐                  │
│           │                         │                         │                  │
│           ▼                         ▼                         ▼                  │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐          │
│  │  RESEARCH CREW  │      │ DEVELOPMENT CREW│      │  CREATIVE CREW  │          │
│  │  (CrewAI)       │      │  (LangGraph)    │      │  (CrewAI)       │          │
│  │                 │      │                 │      │                 │          │
│  │ • Web research  │      │ • Code gen      │      │ • Image gen     │          │
│  │ • Paper analysis│      │ • Testing       │      │ • Voice synth   │          │
│  │ • Trend detect  │      │ • Refactoring   │      │ • Character art │          │
│  │                 │      │                 │      │                 │          │
│  │ LLM: 7B (fast)  │      │ LLM: 70B        │      │ LLM: 70B + GPU  │          │
│  │ via Ollama LB   │      │ via TabbyAPI    │      │ via ComfyUI     │          │
│  └─────────────────┘      └─────────────────┘      └─────────────────┘          │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │                           MEMORY LAYER (Letta)                              ││
│  │                                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    ││
│  │  │   Working    │  │   Episodic   │  │   Semantic   │  │    Model     │    ││
│  │  │   Memory     │  │   Memory     │  │   Memory     │  │  Performance │    ││
│  │  │              │  │              │  │              │  │              │    ││
│  │  │ Current task │  │ Recent tasks │  │ Long-term    │  │ Which models │    ││
│  │  │ Active ctx   │  │ Outcomes     │  │ knowledge    │  │ work for what│    ││
│  │  │ Scratch pad  │  │ Feedback     │  │ Preferences  │  │ Benchmarks   │    ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Agent Concurrency Limits

Based on [parallel agent research](https://cobusgreyling.medium.com/orchestrating-parallel-ai-agents-dab96e5f2e61):

> "3-5 agents usually beats 8-10. Beyond that, merge complexity eats the gains."

| Agent Type | Max Concurrent | GPU Requirement | CPU Cores |
|------------|----------------|-----------------|-----------|
| Research | 4 | None (7B via Ollama LB) | 8 |
| Development | 2 | 70B on hydra-ai | 8 |
| Creative | 2 | GPU for image gen | 4 |
| Monitoring | 4 | None | 4 |

---

## Part 8: Voice Interface Architecture

Based on [Home Assistant Voice Chapter 11](https://www.home-assistant.io/blog/2025/10/22/voice-chapter-11) and [Picovoice](https://picovoice.ai/blog/on-device-llm-powered-voice-assistant/):

> "Streaming TTS reduced latency from 5s to 0.5s - a 10x improvement."

### Voice Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VOICE INTERFACE PIPELINE                                 │
│                         Target: <500ms first word                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  WAKE    │    │  STREAMING   │    │   ROUTELLM   │    │  STREAMING TTS   │   │
│  │  WORD    │───▶│    STT       │───▶│   + LLM      │───▶│  (Kokoro-Fast)   │   │
│  │          │    │              │    │              │    │                  │   │
│  │ Porcupine│    │faster-whisper│    │ 7B or 70B    │    │ Stream chunks    │   │
│  │ or Openwakeword    │              │ based on     │    │ as generated     │   │
│  │          │    │              │    │ complexity   │    │                  │   │
│  └──────────┘    └──────────────┘    └──────────────┘    └──────────────────┘   │
│       │                │                    │                     │              │
│       │                │                    │                     │              │
│       ▼                ▼                    ▼                     ▼              │
│   Satellite        hydra-storage      hydra-ai or           hydra-storage       │
│   (local CPU)      (EPYC 7663)       hydra-compute          (Kokoro:8880)        │
│                                                                                  │
│  LATENCY BREAKDOWN:                                                             │
│  ├── Wake word detection: ~50ms (local)                                         │
│  ├── Streaming STT: ~200ms (first words)                                        │
│  ├── LLM routing + first token: ~150ms (7B) or ~500ms (70B)                     │
│  └── Streaming TTS first audio: ~100ms                                          │
│                                                                                  │
│  TOTAL (simple query): ~500ms first word                                        │
│  TOTAL (complex query): ~850ms first word                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 9: Self-Improvement Loop

Based on [OpenAI's Self-Evolving Agents](https://cookbook.openai.com/examples/partners/self_evolving_agents/autonomous_agent_retraining):

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SELF-IMPROVEMENT LOOP                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. TASK EXECUTION                                                              │
│     └── Agent receives task, executes using current prompts/tools               │
│                                                                                  │
│  2. OUTCOME CAPTURE                                                             │
│     └── Result logged to Activity API with metadata                             │
│         curl POST http://192.168.1.244:8700/activity                            │
│                                                                                  │
│  3. QUALITY ASSESSMENT                                                          │
│     ├── Automated: QA agent reviews output (different model tier)               │
│     └── Human: User feedback (thumbs up/down, corrections)                      │
│                                                                                  │
│  4. LEARNING EXTRACTION                                                         │
│     ├── What worked? → Reinforce in Letta semantic memory                       │
│     ├── What failed? → Record in self-diagnosis engine                          │
│     └── User preference? → Update preference learner                            │
│                                                                                  │
│  5. PROMPT/TOOL REFINEMENT                                                      │
│     ├── Adjust prompt templates based on feedback                               │
│     ├── Update tool selection heuristics                                        │
│     └── Refine model routing rules                                              │
│                                                                                  │
│  6. NEXT ITERATION                                                              │
│     └── Apply learned improvements to next task                                 │
│                                                                                  │
│  FEEDBACK LOOPS:                                                                │
│  ├── Per-task: Immediate quality check                                          │
│  ├── Daily: Aggregate analysis, trend detection                                 │
│  └── Weekly: Major prompt/strategy revisions                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Part 10: Monitoring & Observability

### Key Dashboards

1. **Cluster Overview** - All nodes, GPU temps, VRAM usage
2. **Inference Performance** - Tokens/sec, latency percentiles, queue depth
3. **Agent Activity** - Concurrent agents, success rates, execution times
4. **Resource Allocation** - Policy compliance, utilization patterns

### Critical Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| VRAM Critical | >95% | Reduce context or switch model |
| GPU Temp High | >80°C | Check cooling, reduce power limit |
| Agent Failure Rate | >20% | Review logs, check model health |
| Storage Full | >95% | Cleanup or expand array |

### Prometheus Queries

```promql
# Cluster VRAM utilization
sum(DCGM_FI_DEV_FB_USED) / sum(DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE) * 100

# Inference throughput (TabbyAPI)
rate(tabbyapi_tokens_generated_total[5m])

# Agent success rate
sum(rate(activity_completed{status="success"}[1h])) /
sum(rate(activity_completed[1h])) * 100
```

---

## Part 11: Implementation Priorities

### Immediate (This Week)

1. **Configure dual Ollama instances on hydra-compute**
   - Pin GPU 0 to port 11434, GPU 1 to port 11435
   - Set up Nginx load balancer on port 11400
   - Update LiteLLM config

2. **Implement KV cache tier on hydra-storage**
   - Deploy LMCache or configure Redis with 100GB limit
   - Test semantic caching with Qdrant

3. **Deploy resource monitoring workflow**
   - Import `resource-monitor.json` to n8n
   - Verify alerts flow to Activity API

### Short-term (Next 2 Weeks)

4. **Optimize TabbyAPI configuration**
   - Benchmark different bpw quantizations
   - Find optimal context length for 70B model

5. **Implement voice pipeline MVP**
   - Deploy wake word detector
   - Configure streaming STT/TTS

6. **Complete Typhon Command UI**
   - Finish StatusBar, DomainTabs, CommandOverview integration
   - Add hardware discovery display

### Medium-term (This Month)

7. **Activate full agent orchestration**
   - Deploy CrewAI crews with proper resource limits
   - Implement LangGraph for development tasks

8. **Self-improvement loop**
   - Connect QA agent for automated review
   - Implement feedback capture in UI

---

## Sources

- [DigitalOcean: Splitting LLMs Across GPUs](https://www.digitalocean.com/community/tutorials/splitting-llms-across-multiple-gpus)
- [DatabaseMart: vLLM Optimization](https://www.databasemart.com/blog/vllm-distributed-inference-optimization-guide)
- [NVIDIA: KV Cache Offload](https://developer.nvidia.com/blog/accelerate-large-scale-llm-inference-and-kv-cache-offload-with-cpu-gpu-memory-sharing/)
- [AMD: EPYC for AI](https://www.amd.com/en/blogs/2025/unlocking-optimal-llm-performance-on-amd-epyc--cpus-with-vllm.html)
- [Home Assistant Voice](https://www.home-assistant.io/blog/2025/10/22/voice-chapter-11)
- [OpenAI: Self-Evolving Agents](https://cookbook.openai.com/examples/partners/self_evolving_agents/autonomous_agent_retraining)
- [Ollama Load Balancing](https://markaicode.com/load-balancing-ollama-instances-high-availability/)

---

*Hydra System Architecture v3.0 - December 2025*
*Created with ULTRATHINK deep analysis*
*Live hardware discovery: `curl http://192.168.1.244:8700/hardware/summary`*
