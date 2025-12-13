# Hydra AI Control Plane Architecture

This document describes the unified AI system architecture for the Hydra cluster.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HYDRA AI CONTROL PLANE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        USER INTERFACES                               │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │Open WebUI│  │SillyTav  │  │ Claude   │  │   API Clients    │    │   │
│  │  │  :3000   │  │  :8000   │  │  Code    │  │  (curl, Python)  │    │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │   │
│  └───────┼─────────────┼─────────────┼─────────────────┼──────────────┘   │
│          │             │             │                 │                   │
│          ▼             ▼             ▼                 ▼                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      LiteLLM PROXY (:4000)                          │   │
│  │  - Unified OpenAI-compatible API                                    │   │
│  │  - Model routing (tabby/*, ollama/*, etc.)                          │   │
│  │  - Rate limiting, request logging                                   │   │
│  │  - Fallback chains                                                  │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│          ┌────────────────────┼────────────────────┐                       │
│          ▼                    ▼                    ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                 │
│  │   TabbyAPI   │    │   Ollama     │    │  External    │                 │
│  │ hydra-ai     │    │hydra-compute │    │   APIs       │                 │
│  │   :5000      │    │   :11434     │    │ (OpenAI,etc) │                 │
│  │              │    │              │    │              │                 │
│  │ 70B EXL2     │    │ 7B-14B GGUF  │    │ Fallback     │                 │
│  │ RTX 5090+4090│    │ RTX 5070 Ti  │    │              │                 │
│  └──────────────┘    └──────────────┘    └──────────────┘                 │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         SUPPORT SERVICES                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Qdrant   │  │PostgreSQL│  │  Redis   │  │ SearXNG  │  │Firecrawl │    │
│  │  :6333   │  │  :5432   │  │  :6379   │  │  :8888   │  │  :3005   │    │
│  │ Vectors  │  │ Metadata │  │  Cache   │  │  Search  │  │  Crawl   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         AUTOMATION LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         n8n (:5678)                                  │  │
│  │  - Health monitoring workflows                                       │  │
│  │  - Model switching automation                                        │  │
│  │  - Alert handling                                                    │  │
│  │  - Scheduled maintenance                                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Inference Layer

| Component | Location | Purpose | Models |
|-----------|----------|---------|--------|
| TabbyAPI | hydra-ai:5000 | Primary inference | 70B EXL2 (Llama 3.3, DeepSeek) |
| Ollama | hydra-compute:11434 | Secondary inference | 7B-14B GGUF (Qwen, Mistral) |
| ComfyUI | hydra-compute:8188 | Image generation | SDXL, Flux |
| Kokoro TTS | hydra-storage:8880 | Text-to-speech | Kokoro voices |

### Routing Layer

| Component | Location | Purpose |
|-----------|----------|---------|
| LiteLLM | hydra-storage:4000 | API gateway, routing, logging |

**Model Routing Rules:**

```yaml
# LiteLLM model configuration
model_list:
  # Primary: TabbyAPI 70B
  - model_name: "gpt-4"  # Alias for compatibility
    litellm_params:
      model: "openai/tabby-70b"
      api_base: "http://192.168.1.250:5000/v1"

  # Fast: Ollama 7B
  - model_name: "gpt-3.5-turbo"  # Alias for fast model
    litellm_params:
      model: "ollama/qwen2.5:7b"
      api_base: "http://192.168.1.203:11434"

  # Coding: Ollama Codestral
  - model_name: "codestral"
    litellm_params:
      model: "ollama/codestral:22b"
      api_base: "http://192.168.1.203:11434"
```

### Storage Layer

| Component | Location | Purpose | Data |
|-----------|----------|---------|------|
| Qdrant | hydra-storage:6333 | Vector search | Embeddings, RAG |
| PostgreSQL | hydra-storage:5432 | Relational data | Conversations, metadata |
| Redis | hydra-storage:6379 | Caching | Sessions, rate limits |
| MinIO | hydra-storage:9002 | Object storage | Files, artifacts |

### Augmentation Layer

| Component | Location | Purpose |
|-----------|----------|---------|
| SearXNG | hydra-storage:8888 | Web search |
| Firecrawl | hydra-storage:3005 | Web scraping |
| Docling | hydra-storage:5001 | Document parsing |
| Miniflux | hydra-storage:8180 | RSS aggregation |

## Data Flow

### Chat Request Flow

```
1. User → Open WebUI (http://192.168.1.250:3000)
2. Open WebUI → LiteLLM (http://192.168.1.244:4000/v1/chat/completions)
3. LiteLLM routes based on model:
   - "gpt-4" → TabbyAPI (hydra-ai:5000)
   - "gpt-3.5-turbo" → Ollama (hydra-compute:11434)
4. Inference engine processes request
5. Response returns through chain
6. LiteLLM logs to PostgreSQL
```

### RAG Flow

```
1. Document ingested via Firecrawl/Docling
2. Text chunked and embedded (via TabbyAPI or Ollama)
3. Embeddings stored in Qdrant
4. Query time:
   a. User query embedded
   b. Qdrant similarity search
   c. Top-k chunks retrieved
   d. Context injected into prompt
   e. LLM generates response
```

## Model Management

### Current Model Inventory

| Model | Format | Size | Location | Use Case |
|-------|--------|------|----------|----------|
| Llama-3.3-70B-Instruct | EXL2 4bpw | ~35GB | hydra-ai | General, reasoning |
| DeepSeek-R1-Distill-70B | EXL2 4bpw | ~35GB | hydra-ai | Coding, math |
| Qwen2.5-7B-Instruct | GGUF Q8 | ~8GB | hydra-compute | Fast responses |
| Codestral-22B | GGUF Q6 | ~14GB | hydra-compute | Code generation |
| nomic-embed-text | GGUF | ~300MB | hydra-compute | Embeddings |

### Model Switching

**Via TabbyAPI:**
```bash
# Check current model
curl -s http://192.168.1.250:5000/v1/model | jq .

# Load different model (requires config change + restart)
ssh typhon@hydra-ai "sudo sed -i 's/model_name: .*/model_name: DeepSeek-R1-70B-exl2/' /opt/tabbyapi/config.yml && sudo systemctl restart tabbyapi"
```

**Via Ollama:**
```bash
# List available models
curl -s http://192.168.1.203:11434/api/tags | jq '.models[].name'

# Pull new model
curl -X POST http://192.168.1.203:11434/api/pull -d '{"name": "llama3.2:3b"}'
```

## API Reference

### LiteLLM Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/completions` | POST | Chat inference |
| `/v1/completions` | POST | Text completion |
| `/v1/embeddings` | POST | Generate embeddings |
| `/v1/models` | GET | List available models |
| `/health` | GET | Health check |

### TabbyAPI Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/chat/completions` | POST | Chat inference |
| `/v1/completions` | POST | Text completion |
| `/v1/model` | GET | Current model info |
| `/v1/model/load` | POST | Load model |
| `/v1/model/unload` | POST | Unload model |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

### Example Requests

**Chat Completion:**
```bash
curl -X POST http://192.168.1.244:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

**Embedding:**
```bash
curl -X POST http://192.168.1.203:11434/api/embeddings \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "The quick brown fox"
  }'
```

## Automation Workflows

### n8n Workflows

| Workflow | Trigger | Action |
|----------|---------|--------|
| Health Digest | Daily 8 AM | Check all services, send summary |
| Auto-Recovery | On failure | Restart failed containers |
| Disk Cleanup | Weekly | Prune Docker, clean logs |
| Model Metrics | Hourly | Collect inference stats |

### Planned Automations

| Automation | Priority | Status |
|------------|----------|--------|
| Automatic model switching based on VRAM | Medium | Planned |
| Query routing based on complexity | Medium | Planned |
| Proactive disk space alerts | High | Alert rules exist |
| Model download queue | Low | Planned |

## Scaling Considerations

### Current Capacity

| Resource | Available | Used | Headroom |
|----------|-----------|------|----------|
| GPU VRAM (hydra-ai) | 56GB | ~40GB | ~16GB |
| GPU VRAM (hydra-compute) | 28GB | ~16GB | ~12GB |
| RAM (cluster total) | ~192GB | ~64GB | ~128GB |
| Storage (models) | 500GB | ~200GB | ~300GB |

### Expansion Options

1. **Add GPU to hydra-compute** - Second slot available
2. **Tensor Parallelism** - ExLlamaV3 supports TP (same GPU types only)
3. **Pipeline Parallelism** - For heterogeneous GPUs (5090+4090)
4. **Quantization** - Lower bpw for larger models

## Security

### Network Isolation

- All services on private LAN (192.168.1.0/24)
- Tailscale for remote access
- No public exposure without VPN

### Authentication

| Service | Auth Method |
|---------|-------------|
| LiteLLM | API key (master key) |
| TabbyAPI | None (internal only) |
| Open WebUI | User accounts |
| Grafana | Local accounts |
| n8n | Local accounts |

### Secrets Management

- Infrastructure secrets in docker-compose.yml (migrate to SOPS)
- Application secrets in respective config files
- Vaultwarden for password management

---

*Last updated: 2025-12-13*
