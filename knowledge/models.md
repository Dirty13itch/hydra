# AI Models Knowledge Base

## Model Selection Philosophy

1. **Apache 2.0 or MIT license preferred** for commercial flexibility
2. **EXL2 format** for TabbyAPI (fastest loading, best VRAM efficiency)
3. **GGUF format** for Ollama/llama.cpp fallback
4. **Uncensored models** for creative/RP work - no refusals

## Primary LLM Models (hydra-ai, 56GB VRAM)

### General Purpose

| Model | Size | BPW | VRAM | Context | License | Notes |
|-------|------|-----|------|---------|---------|-------|
| Qwen3-235B-A22B | 235B MoE | 3.0 | ~50GB | 16K | Apache 2.0 | Best overall, 22B active params |
| Qwen3-72B | 72B | 3.5-4.0 | 46-52GB | 32K | Apache 2.0 | Dense, deterministic |
| Llama-3.1-70B | 70B | 3.5-4.5 | 45-55GB | 32K | Llama 3.1 | Proven, balanced |
| DeepSeek-V3 | 671B MoE | 2.5 | ~55GB | 16K | MIT | Strong reasoning |

### Uncensored / Abliterated

| Model | Size | BPW | VRAM | Notes |
|-------|------|-----|------|-------|
| **Dark Champion 70B** | 70B | 3.5 | ~45GB | Abliterated Llama-3.2, zero refusals, MMLU 82% |
| **Nous Hermes 3** | 70B | 3.5 | ~45GB | Strong reasoning + uncensored |
| **Dolphin 3.0 Llama-70B** | 70B | 3.5 | ~45GB | Cognitive liberty, no filters |
| **Midnight Miqu** | 70B | 3.5 | ~45GB | Uncensored Mistral derivative |
| **Goliath 120B** | 120B | 2.5 | ~50GB | Merged model, very capable |
| **Huihui-GLM-4.5-Abliterated** | 110B | 2.5 | ~55GB | Chinese model, abliterated |

### Coding Focused

| Model | Size | BPW | VRAM | Notes |
|-------|------|-----|------|-------|
| Qwen2.5-Coder-72B | 72B | 3.5 | ~46GB | Best open coding model |
| DeepSeek-Coder-V2 | 236B MoE | 2.5 | ~50GB | Strong at complex code |
| CodeLlama-70B | 70B | 3.5 | ~45GB | Meta's code specialist |

## Secondary Models (hydra-compute)

### Ollama on 5070 Ti (16GB)

| Model | VRAM | Purpose |
|-------|------|---------|
| Llama-3.1-8B | ~8GB | Fast general queries |
| Qwen2.5-14B | ~12GB | Better reasoning, still fast |
| Qwen2.5-Coder-7B | ~8GB | Quick code completions |
| Mistral-7B | ~6GB | Very fast, decent quality |

### Embeddings on 3060 (12GB)

| Model | Dimensions | Context | Notes |
|-------|------------|---------|-------|
| **nomic-embed-text-v1.5** | 768 | 8K | Best balance, recommended |
| bge-large-en-v1.5 | 1024 | 512 | High quality, short context |
| e5-large-v2 | 1024 | 512 | Good for semantic search |
| mxbai-embed-large | 1024 | 512 | Strong retrieval |

## RP/ERP Specialized Models

### Large Models (70B+)

| Model | Size | Specialty | Notes |
|-------|------|-----------|-------|
| **Lumimaid 70B** | 70B | High quality RP/ERP | Community favorite |
| **EVA-Llama-3.3-70B** | 70B | Uncensored storytelling | For Mac/local setups |
| **Euryale 70B** | 70B | Immersive narratives | Llama 3.3 based |
| **Midnight Miqu** | 70B | Bold, uncensored | Mistral derivative |

### Medium Models (7B-14B)

| Model | Size | Specialty | Notes |
|-------|------|-----------|-------|
| **Rocinante 12B** | 12B | ERP specialist | Recent, very good |
| **MN Violet Lotus 12B** | 12B | Emotional RP | High EQ |
| **Noromaid-Mixtral** | 47B MoE | Smooth RP dialogue | Community favorite |
| **Fimbulvetr 11B** | 11B | MythoMax derivative | Classic RP |

### Small Models (<7B)

| Model | Size | Specialty | Notes |
|-------|------|-----------|-------|
| **Pygmalion 7B** | 7B | OG waifu model | Classic |
| **Undi95 DPO Mistral 7B** | 7B | Adult RP | Bold, runs on low-end |
| **Psyfighter 2-13B** | 13B | Classic RP | Still popular |

## Where to Find Models

### Hugging Face Collections
- [TheBloke](https://huggingface.co/TheBloke) - GGUF quantizations
- [turboderp](https://huggingface.co/turboderp) - EXL2 quantizations
- [bartowski](https://huggingface.co/bartowski) - High quality quants
- [mradermacher](https://huggingface.co/mradermacher) - Various formats

### Search Tags
- `nsfw` - Adult content capable
- `uncensored` - No refusals
- `abliterated` - Refusal mechanisms removed
- `roleplay` - RP optimized
- `erp` - Adult roleplay

## Image Generation Models

### Stable Diffusion Checkpoints

| Model | Base | VRAM | Specialty |
|-------|------|------|-----------|
| **Pony Diffusion V6 XL** | SDXL | 8-10GB | Anime, furry, trained on e621 |
| **epiCRealism XL** | SDXL | 8-10GB | NSFW photorealistic |
| **RealVisXL** | SDXL | 8-10GB | Realistic, good anatomy |
| **Juggernaut XL** | SDXL | 8-10GB | Photorealistic |
| **URPM** | SDXL | 8-10GB | Explicit realism |
| **Abyss OrangeMix** | SD 1.5 | 4-6GB | Anime NSFW |
| **CyberRealistic** | SD 1.5 | 4-6GB | Photorealistic |
| **Hassanblend** | SD 1.5 | 4-6GB | Realistic NSFW |

### Flux Models

| Model | VRAM | Notes |
|-------|------|-------|
| **Flux.1-dev** | 12-16GB | Best text/hands, open weights |
| **Flux.1-schnell** | 8-12GB | Fast, 4-step generation |

### LoRAs (Style/Character)

- **Anatomy correction** - Fix hands, feet, poses
- **Style LoRAs** - Specific artists, aesthetics
- **Character LoRAs** - Consistency across images
- **Pose LoRAs** - Specific positions

### Where to Find
- [CivitAI](https://civitai.com) - Largest repository, filter by NSFW
- [Hugging Face](https://huggingface.co/models?other=stable-diffusion)

## Video Generation

| Model | Notes |
|-------|-------|
| AnimateDiff | Animation from SD checkpoints, works with NSFW |
| Stable Video Diffusion | Image-to-video |
| Wan2.1 | Recent, good motion |
| CogVideoX | Text-to-video |
| Mochi | Open weights |

## Model Format Guide

### EXL2 (Preferred for TabbyAPI)
- Fastest loading on ExLlamaV2
- Best VRAM efficiency
- Calibrated quantization
- BPW (bits per weight): 2.0-6.0 common

### GGUF (Ollama/llama.cpp)
- Universal format
- CPU + GPU offloading
- Quantizations: Q2_K, Q3_K, Q4_K, Q5_K, Q6_K, Q8_0

### AWQ (Alternative)
- Good for vLLM
- Activation-aware quantization

## Abliteration Explained

**What it is:** Surgical removal of refusal mechanisms from model weights

**How it works:**
1. Identify activation patterns that cause refusals
2. Calculate "refusal direction" vector
3. Project weights to remove this direction
4. Result: Model closer to base behavior, no refusals

**vs Fine-tuning:**
- Fine-tuning: Teaches new behaviors (slower, needs data)
- Abliteration: Removes existing behaviors (faster, surgical)

**Models to look for:**
- `*-abliterated` suffix
- `*-uncensored` suffix
- Dolphin family (designed uncensored from start)

## Model Download Commands

```bash
# Using huggingface-cli
pip install huggingface_hub
huggingface-cli download bartowski/Llama-3.1-70B-EXL2-4.0bpw \
  --local-dir /mnt/user/models/exl2/Llama-3.1-70B-EXL2-4.0bpw

# Using git lfs
git lfs install
git clone https://huggingface.co/bartowski/Llama-3.1-70B-EXL2-4.0bpw \
  /mnt/user/models/exl2/Llama-3.1-70B-EXL2-4.0bpw

# For Ollama
ollama pull llama3.1:70b
```

## SillyTavern Model Settings

### Recommended Samplers
```
Temperature: 0.7-0.9 (higher for creativity)
Top-P: 0.9-0.95
Top-K: 40
Repetition Penalty: 1.05-1.15
Min-P: 0.05
```

### Context Template
- Use `ChatML` or `Llama-3` format
- Enable `Instruct Mode`
- Set `Context Size` to match model (32K for most)

## Empire of Broken Queens Models

### Recommended for Dynamic Dialogue
1. **Primary:** Dark Champion 70B (uncensored, good prose)
2. **Backup:** Nous Hermes 3 70B (balanced)
3. **Fast draft:** Rocinante 12B on Ollama

### Recommended for Character Art
1. **Primary:** PonyXL (anime style) or epiCRealism XL (realistic)
2. **Character consistency:** Train LoRA per queen
3. **Poses:** Use ControlNet + pose LoRAs
