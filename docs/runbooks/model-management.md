# Model Management Runbook

Step-by-step procedures for managing AI models on the Hydra cluster.

## Load a New Model on TabbyAPI

### Prerequisites
- SSH access to hydra-ai (192.168.1.250)
- Model downloaded to `/mnt/models/exl2/`

### Procedure

1. **Check current model and VRAM**
   ```bash
   curl -s http://192.168.1.250:5000/v1/model | jq .
   ssh typhon@192.168.1.250 "nvidia-smi --query-gpu=memory.free --format=csv"
   ```

2. **Unload current model (if needed)**
   ```bash
   curl -X POST http://192.168.1.250:5000/v1/model/unload
   ```
   Wait ~30 seconds for VRAM to clear.

3. **Load new model**
   ```bash
   curl -X POST http://192.168.1.250:5000/v1/model/load \
     -H "Content-Type: application/json" \
     -d '{
       "model_name": "MODEL_FOLDER_NAME",
       "max_seq_len": 8192,
       "gpu_split": [0.65, 0.35]
     }'
   ```

   Common gpu_split values:
   - 70B models: `[0.65, 0.35]` (32GB + 24GB)
   - 34B models: `[0.6, 0.4]`
   - 8B models: `[1.0]` (single GPU)

4. **Verify model loaded**
   ```bash
   curl -s http://192.168.1.250:5000/v1/model | jq .model_name
   ```

5. **Test inference**
   ```bash
   curl -X POST http://192.168.1.250:5000/v1/completions \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, my name is", "max_tokens": 20}'
   ```

### Troubleshooting

**Model fails to load (OOM)**
- Check VRAM: `nvidia-smi`
- Use smaller max_seq_len
- Adjust gpu_split to use more of GPU 0 (5090)

**Model loads but inference errors**
- Check TabbyAPI logs: `journalctl -u tabbyapi -f`
- Verify EXL2 format matches ExLlamaV2 version
- Restart TabbyAPI: `sudo systemctl restart tabbyapi`

---

## Download a New Model

### Procedure

1. **Find model on HuggingFace**
   - Search for EXL2 quantizations
   - Recommended sources: turboderp, bartowski, LoneStriker

2. **Download to models directory**
   ```bash
   ssh typhon@192.168.1.250
   cd /mnt/models/exl2

   # Using huggingface-cli (recommended)
   huggingface-cli download turboderp/Llama-3.3-70B-Instruct-exl2 \
     --revision 4.0bpw \
     --local-dir Llama-3.3-70B-Instruct-exl2-4.0bpw

   # Or using git lfs
   git lfs install
   git clone https://huggingface.co/turboderp/Llama-3.3-70B-Instruct-exl2 \
     --branch 4.0bpw \
     Llama-3.3-70B-Instruct-exl2-4.0bpw
   ```

3. **Verify download**
   ```bash
   ls -la /mnt/models/exl2/Llama-3.3-70B-Instruct-exl2-4.0bpw/
   # Should contain: config.json, model.safetensors, tokenizer files
   ```

4. **Add to model presets (optional)**
   Edit `scripts/model-presets.yaml` to add preset configuration.

---

## Switch Model Presets

### Available Presets

| Preset | Model | Use Case |
|--------|-------|----------|
| `llama-70b-default` | Llama-3.3-70B @ 4bpw | General use |
| `llama-70b-long` | Llama-3.3-70B @ 4bpw | Long context (32k) |
| `llama-8b-fast` | Llama-3.1-8B @ 6bpw | Quick responses |
| `deepseek-coder` | DeepSeek-Coder-V2 | Coding tasks |
| `qwen-72b` | Qwen2.5-72B @ 4bpw | Multilingual |
| `creative` | Model varies | Creative writing |

### Procedure

```bash
# Using model-loader script
python scripts/model-loader.py preset llama-70b-default

# Or via curl
curl -X POST http://192.168.1.250:5000/v1/model/load \
  -H "Content-Type: application/json" \
  -d @<(python scripts/model-loader.py preset llama-70b-default --json)
```

---

## Load Model on Ollama

### Procedure

1. **Check available models**
   ```bash
   curl http://192.168.1.203:11434/api/tags | jq '.models[].name'
   ```

2. **Pull new model (if needed)**
   ```bash
   ssh typhon@192.168.1.203 "ollama pull qwen2.5:14b"
   ```

3. **Generate with model (auto-loads)**
   ```bash
   curl http://192.168.1.203:11434/api/generate \
     -d '{"model": "qwen2.5:14b", "prompt": "Hello"}'
   ```

### Ollama Model Size Limits
- hydra-compute: 28GB VRAM (16GB + 12GB)
- Max model size: ~20B parameters at full precision
- Recommended: Up to 14B models

---

## Emergency Model Recovery

If TabbyAPI is unresponsive:

1. **Force restart TabbyAPI**
   ```bash
   ssh typhon@192.168.1.250 "sudo systemctl restart tabbyapi"
   ```

2. **If still stuck, kill and restart**
   ```bash
   ssh typhon@192.168.1.250 "sudo pkill -9 -f tabbyapi && sudo systemctl start tabbyapi"
   ```

3. **Check for GPU memory leak**
   ```bash
   ssh typhon@192.168.1.250 "nvidia-smi"
   # If VRAM high but no model loaded, restart GPU services
   ssh typhon@192.168.1.250 "sudo nvidia-smi --gpu-reset -i 0"
   ```

4. **Last resort: Reboot node**
   ```bash
   ssh typhon@192.168.1.250 "sudo reboot"
   ```
   Wait 3-5 minutes, then verify services started.
