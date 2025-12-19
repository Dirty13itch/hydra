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

### ExLlamaV3 Status (Updated 2025-12-19)

**Current State**:
- **ExLlamaV3 version**: 0.0.15 (latest as of Dec 2025)
- **Current Hydra setup**: ExLlamaV2 0.3.2 on TabbyAPI
- **New EXL3 format**: Based on QTIP from Cornell RelaxML
- **Tensor parallelism**: Supported, experimental
- **Speculative decoding**: Yes, native support
- **TabbyAPI**: Official recommended backend for ExLlamaV3

**Key ExLlamaV3 Improvements**:
1. **EXL3 quantization** - Faster conversion (minutes vs hours for 70B)
2. **Speculative decoding** - Up to 2-4x inference speedup
3. **Tensor-parallel + Expert-parallel** - Better multi-GPU support
4. **2-8 bit cache quantization** - More VRAM efficient
5. **Multimodal support** - Vision models
6. **Continuous dynamic batching** - Better throughput

**Migration Readiness**:
| Criterion | Status | Notes |
|-----------|--------|-------|
| TabbyAPI support | Ready | Native backend |
| Tensor parallel | Experimental | Manual gpu_split config |
| Heterogeneous GPUs | Supported | 5090+4090 viable |
| EXL3 models | Limited | Need to convert or download |
| Stability | Experimental | Wait for v0.1.0 |

**Recommendation**: Migrate when ExLlamaV3 reaches v0.1.0 stable

## ExLlamaV3 Migration Guide

### Pre-Migration Checklist
```bash
# 1. Backup current config
ssh typhon@192.168.1.250 "cp /opt/tabbyapi/config.yml /opt/tabbyapi/config.yml.v2-backup"

# 2. Check VRAM availability
ssh typhon@192.168.1.250 "nvidia-smi --query-gpu=memory.total,memory.free --format=csv"

# 3. Verify current model performance as baseline
curl -s http://192.168.1.250:5000/v1/model | jq .
```

### Step 1: Install ExLlamaV3 (Parallel Test Environment)
```bash
# Create separate V3 environment
ssh typhon@192.168.1.250 << 'EOF'
cd /opt
python -m venv exllamav3-test
source exllamav3-test/bin/activate

# Install with CUDA 12.8
pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
pip install exllamav3
pip install tabbyapi  # Updated TabbyAPI with V3 support
EOF
```

### Step 2: Convert Model to EXL3 (or Download)
```bash
# Option A: Convert existing model
ssh typhon@192.168.1.250 << 'EOF'
source /opt/exllamav3-test/bin/activate
python -m exllamav3.convert \
    --input /mnt/models/Midnight-Miqu-70B-v1.5-exl2-2.5bpw \
    --output /mnt/models/Midnight-Miqu-70B-exl3-2.5bpw \
    --bits 2.5
EOF

# Option B: Download pre-converted EXL3 model
# Check HuggingFace for turboderp-org EXL3 releases
```

### Step 3: Test Configuration
```yaml
# /opt/tabbyapi-v3/config.yml
network:
  host: 0.0.0.0
  port: 5001  # Different port for testing

model:
  model_dir: /mnt/models
  model_name: Midnight-Miqu-70B-exl3-2.5bpw

  # V3 tensor parallelism
  tensor_parallel: true
  gpu_split: [28, 24]  # 5090 (32GB), 4090 (24GB), leave buffer

  # Speculative decoding (V3 feature)
  speculative_decoding:
    enabled: true
    draft_model: Llama-3.2-1B-exl3
    num_speculative_tokens: 5

  # V3 cache quantization
  cache_mode: Q4
  cache_size: 32768  # Larger context with efficient cache
  max_seq_len: 32768
```

### Step 4: Performance Comparison
```bash
# Run benchmark on both versions
# V2 (port 5000)
curl -s http://192.168.1.250:5000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a poem about AI", "max_tokens": 200}' | jq .usage

# V3 (port 5001)
curl -s http://192.168.1.250:5001/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a poem about AI", "max_tokens": 200}' | jq .usage
```

### Step 5: Full Migration (When Ready)
```bash
# Stop current TabbyAPI
ssh typhon@192.168.1.250 "sudo systemctl stop tabbyapi"

# Update systemd service to use V3
ssh typhon@192.168.1.250 << 'EOF'
sudo sed -i 's|/opt/tabbyapi/venv|/opt/tabbyapi-v3/venv|g' /etc/systemd/system/tabbyapi.service
sudo systemctl daemon-reload
sudo systemctl start tabbyapi
EOF

# Verify
curl -s http://192.168.1.250:5000/v1/model | jq .
```

### Rollback Procedure
```bash
# Restore V2 if issues
ssh typhon@192.168.1.250 << 'EOF'
sudo systemctl stop tabbyapi
sudo sed -i 's|/opt/tabbyapi-v3/venv|/opt/tabbyapi/venv|g' /etc/systemd/system/tabbyapi.service
cp /opt/tabbyapi/config.yml.v2-backup /opt/tabbyapi/config.yml
sudo systemctl daemon-reload
sudo systemctl start tabbyapi
EOF
```

**V3 Target Configuration**:
```yaml
# When TabbyAPI V3 is stable
tensor_parallel: true
gpu_split: [28, 24]  # 5090+4090 with buffer
autosplit_reserve: [4096, 2048]  # MB per GPU
speculative_decoding:
  enabled: true
  draft_model: Llama-3.2-1B-exl3
```

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

### Speculative Decoding (Hardware Limitation)

**Status**: Not feasible with current heterogeneous GPU setup (5090 + 4090)

Speculative decoding uses a small "draft" model to predict tokens, verified by the main model.
Can provide 30-100% speedup with minimal quality loss.

**Available Draft Models** (downloaded 2025-12-17):
- `/mnt/models/Llama-3.2-1B-Instruct-exl2-8.0bpw` (~1.7GB)
- `/mnt/models/Llama-3.2-1B-Instruct-exl2-4.0bpw` (~1.2GB)

**Why It Doesn't Work**:
With heterogeneous GPUs (32GB + 24GB = 56GB), ExLlamaV2's autosplit must distribute both
models across both GPUs. The 70B main model (~45GB) + draft model (~1.2GB) + KV cache
exceeds available VRAM when accounting for GPU split overhead.

Testing showed "Insufficient VRAM for model and cache" even with:
- Smallest main model: Midnight-Miqu-70B-v1.5-exl2-2.5bpw
- Smallest draft model: Llama-3.2-1B-Instruct-exl2-4.0bpw
- Minimal cache: 4096 tokens, Q4 mode
- Maximum reserve: 4GB per GPU

**Future Solutions**:
1. **Upgrade to matched GPUs** - Two 5090s (64GB total, tensor parallel)
2. **Use smaller main model** - 32B models would fit with draft
3. **Wait for ExLlamaV3 tensor parallel** - May handle this better

**Config for Reference** (when/if hardware allows):
```yaml
draft_model:
  draft_model_dir: /mnt/models
  draft_model_name: Llama-3.2-1B-Instruct-exl2-4.0bpw
  draft_cache_mode: Q4
  draft_gpu_split_auto: true
```

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

## Stability Improvements (Dec 2025)

### Pre-Start Script
TabbyAPI uses a pre-start script (`/opt/tabbyapi/prestart.sh`) that runs before each startup:
- Kills orphan processes holding ports 5000/5001
- Clears CUDA memory cache
- Checks VRAM availability
- Verifies model directory is mounted

### Systemd Service Configuration
The NixOS systemd service (`/etc/nixos/configuration.nix`) includes:
```nix
systemd.services.tabbyapi = {
  description = "TabbyAPI - OpenAI-compatible LLM API Server";
  after = [ "network.target" "mnt-models.mount" ];
  wantedBy = [ "multi-user.target" ];
  startLimitIntervalSec = 300;  # 5 min window
  startLimitBurst = 5;          # Max 5 restarts in window

  serviceConfig = {
    Type = "simple";
    User = "typhon";
    WorkingDirectory = "/opt/tabbyapi";
    ExecStartPre = "/opt/tabbyapi/prestart.sh";
    ExecStart = "/opt/tabbyapi/venv/bin/python /opt/tabbyapi/main.py";
    Restart = "on-failure";
    RestartSec = 30;            # Wait 30s between restarts
    TimeoutStartSec = 300;      # 5 min for model loading
    Environment = [
      "CUDA_DEVICE_ORDER=PCI_BUS_ID"
      "CUDA_VISIBLE_DEVICES=0,1"
      "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
    ];
  };
};
```

### Port Conflict Prevention
The prestart script prevents the common issue where TabbyAPI crashes, restarts, but the old process still holds port 5000, causing the new instance to start on 5001.

### VRAM Exhaustion Recovery
If TabbyAPI crashes due to insufficient VRAM:
1. Prestart script clears CUDA cache on next attempt
2. RestartSec of 30s gives time for GPU memory to release
3. StartLimitBurst prevents infinite restart loops

### Manual Recovery
```bash
# Force cleanup and restart
ssh typhon@192.168.1.250 "sudo systemctl stop tabbyapi && /opt/tabbyapi/prestart.sh && sudo systemctl start tabbyapi"

# Monitor startup
ssh typhon@192.168.1.250 "journalctl -u tabbyapi -f"
```
