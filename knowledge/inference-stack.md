# Inference Stack Knowledge Base

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Clients                                   │
│  (Open WebUI, SillyTavern, n8n, agents, API consumers)          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LiteLLM (hydra-storage:4000)                 │
│              OpenAI-compatible API gateway/router               │
└──────┬──────────────────┬───────────────────────┬───────────────┘
       │                  │                       │
       ▼                  ▼                       ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐
│   TabbyAPI   │  │    Ollama    │  │         Ollama (CPU)         │
│ hydra-ai:5000│  │hydra-compute │  │     hydra-storage:11434      │
│              │  │   :11434     │  │                              │
│  70B models  │  │ 7B-14B quick │  │      7B fallback             │
│  5090+4090   │  │  5070 Ti     │  │      EPYC 7663               │
└──────────────┘  └──────────────┘  └──────────────────────────────┘
```

## TabbyAPI + ExLlamaV2 (Primary)

### Why ExLlamaV2
- **Only** engine supporting tensor parallelism across heterogeneous GPUs
- Uses ALL available VRAM (32GB + 24GB = 56GB combined)
- True parallel execution, not sequential layer offloading
- ~85% faster than llama.cpp for generation
- EXL2 quantization format optimized for this engine

### ExLlamaV3 Status
- Released but **lacks tensor parallelism**
- Stay on V2 for heterogeneous GPU setups
- V3 is faster for single-GPU configs only

### Installation (NixOS)
```bash
# Create venv
python -m venv /opt/tabbyapi/venv
source /opt/tabbyapi/venv/bin/activate

# Install with CUDA 12.8 (Blackwell support)
pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/cu128
pip install exllamav2 tabbyapi

# Or clone and install
git clone https://github.com/theroyallab/tabbyAPI
cd tabbyAPI
pip install -e .
```

### Configuration
```yaml
# /opt/tabbyapi/config.yml
network:
  host: 0.0.0.0
  port: 5000

model:
  model_dir: /mnt/models/exl2
  
  # Tensor parallelism for heterogeneous GPUs
  tensor_parallel: true
  
  # Let it auto-calculate based on VRAM
  gpu_split_auto: true
  
  # Or manual split (optional)
  # gpu_split: [32, 24]  # 5090 first, 4090 second
  
  max_seq_len: 32768
  cache_mode: FP16
  
  # Pre-allocate cache for faster model switching
  # expect_cache_tokens: 16384

logging:
  level: INFO
```

### Systemd Service (NixOS)
```nix
# In configuration.nix
systemd.services.tabbyapi = {
  description = "TabbyAPI LLM Inference Server";
  after = [ "network.target" ];
  wantedBy = [ "multi-user.target" ];
  
  serviceConfig = {
    Type = "simple";
    User = "typhon";
    WorkingDirectory = "/opt/tabbyapi";
    ExecStart = "${pkgs.bash}/bin/bash -c 'source venv/bin/activate && python -m tabbyapi'";
    Restart = "always";
    RestartSec = 10;
    
    # GPU access
    Environment = [
      "CUDA_VISIBLE_DEVICES=0,1"
      "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
    ];
  };
};
```

### API Usage
```bash
# Check status
curl http://192.168.1.250:5000/health

# List available models
curl http://192.168.1.250:5000/v1/models

# Chat completion (OpenAI-compatible)
curl -X POST http://192.168.1.250:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'

# Load specific model
curl -X POST http://192.168.1.250:5000/v1/model/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "Llama-3.1-70B-EXL2-4.0bpw"}'

# Unload model
curl -X POST http://192.168.1.250:5000/v1/model/unload
```

### Model Requirements (56GB VRAM)
| Model | BPW | VRAM | Context | Notes |
|-------|-----|------|---------|-------|
| Llama-3.1-70B | 3.5 | ~45GB | 32K | Current daily driver |
| Llama-3.1-70B | 4.0 | ~52GB | 24K | Higher quality |
| Qwen3-72B | 3.5 | ~46GB | 32K | Strong reasoning |
| Dark Champion 70B | 3.5 | ~45GB | 32K | Uncensored |
| Qwen3-235B-A22B | 3.0 | ~50GB | 16K | MoE, 22B active |

## LiteLLM (API Gateway)

### Purpose
- Single OpenAI-compatible endpoint for all backends
- Request routing based on model name
- Fallback chains
- Usage tracking
- Cost estimation

### Docker Compose
```yaml
# /mnt/user/appdata/hydra-stack/docker-compose.yml
litellm:
  image: ghcr.io/berriai/litellm:main-latest
  container_name: litellm
  ports:
    - "4000:4000"
  volumes:
    - ./litellm/config.yaml:/app/config.yaml
  environment:
    - LITELLM_MASTER_KEY=${LITELLM_KEY}
  command: ["--config", "/app/config.yaml"]
  restart: unless-stopped
```

### Configuration
```yaml
# /mnt/user/appdata/hydra-stack/litellm/config.yaml
model_list:
  # Primary 70B on hydra-ai
  - model_name: "llama-70b"
    litellm_params:
      model: "openai/default"
      api_base: "http://192.168.1.250:5000/v1"
      api_key: "not-needed"
    model_info:
      max_tokens: 32768
      
  - model_name: "gpt-4"  # Alias for compatibility
    litellm_params:
      model: "openai/default"
      api_base: "http://192.168.1.250:5000/v1"
      api_key: "not-needed"

  # Fast models on hydra-compute
  - model_name: "llama-8b"
    litellm_params:
      model: "ollama/llama3.1:8b"
      api_base: "http://192.168.1.203:11434"
      
  - model_name: "qwen-14b"
    litellm_params:
      model: "ollama/qwen2.5:14b"
      api_base: "http://192.168.1.203:11434"

  # Embeddings
  - model_name: "text-embedding-nomic"
    litellm_params:
      model: "ollama/nomic-embed-text"
      api_base: "http://192.168.1.203:11434"

  # CPU fallback on Unraid
  - model_name: "llama-7b-cpu"
    litellm_params:
      model: "ollama/llama3.2:latest"
      api_base: "http://192.168.1.244:11434"

# Router settings
router_settings:
  routing_strategy: "simple-shuffle"  # or "least-busy"
  num_retries: 2
  timeout: 300

litellm_settings:
  drop_params: true
  set_verbose: false
```

### Usage
```bash
# Via LiteLLM
curl -X POST http://192.168.1.244:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LITELLM_KEY}" \
  -d '{
    "model": "llama-70b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Ollama (Secondary)

### hydra-compute (GPU - 5070 Ti)
```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Configure for external access
sudo systemctl edit ollama
# Add:
# [Service]
# Environment="OLLAMA_HOST=0.0.0.0"

# Pull models
ollama pull llama3.1:8b
ollama pull qwen2.5:14b
ollama pull nomic-embed-text
```

### hydra-storage (CPU Only)
```yaml
# docker-compose.yml
ollama:
  image: ollama/ollama:latest
  container_name: ollama
  ports:
    - "11434:11434"
  volumes:
    - /mnt/user/appdata/ollama:/root/.ollama
  environment:
    - OLLAMA_HOST=0.0.0.0
  restart: unless-stopped
```

### Why Separate Ollama Instances
- **hydra-compute:** Fast 7B-14B inference on 5070 Ti
- **hydra-storage:** CPU fallback when GPUs busy
- **Don't tensor-parallel** 5070 Ti + 3060 (VRAM mismatch inefficient)

## Speculative Decoding

Use small draft model to speed up large model:

```python
# Not natively in TabbyAPI yet, but conceptually:
# Draft model (7B) generates candidates
# Target model (70B) verifies in parallel

# Current best approach: Route simple queries to Ollama,
# complex queries to TabbyAPI via LiteLLM
```

## Model Loading Best Practices

1. **Pre-download models** to `/mnt/user/models/exl2/`
2. **Use consistent naming:** `<Model>-<Size>-EXL2-<BPW>bpw`
3. **Check VRAM before loading:**
   ```bash
   nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits
   ```
4. **Unload before switching:**
   ```bash
   curl -X POST http://192.168.1.250:5000/v1/model/unload
   ```

## Troubleshooting

### CUDA Out of Memory
```bash
# Check what's using VRAM
nvidia-smi

# Kill rogue processes
sudo fuser -v /dev/nvidia*

# Clear cache
python -c "import torch; torch.cuda.empty_cache()"
```

### Slow Model Loading
- Verify 10GbE is active: `ethtool eno1 | grep Speed`
- Check NFS mount options include `nconnect=8`
- Use EXL2 format (faster to load than GGUF)

### TabbyAPI Not Starting
```bash
# Check logs
journalctl -u tabbyapi -f

# Common issues:
# - CUDA driver mismatch
# - Model file corruption
# - Insufficient VRAM
```
