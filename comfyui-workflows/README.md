# ComfyUI Workflows for Hydra

Pre-built workflow templates for image generation on the Hydra cluster.

## Available Workflows

### sdxl-basic.json
Basic SDXL image generation workflow.
- **Model:** sd_xl_base_1.0.safetensors
- **Resolution:** 1024x1024
- **Sampler:** euler_ancestral, 25 steps
- **CFG:** 7.5
- **VRAM:** ~8GB

### flux-simple.json
Simple FLUX.1 Dev workflow for high-quality generation.
- **Model:** flux1-dev.safetensors
- **Resolution:** 1024x1024
- **Sampler:** euler, 20 steps
- **CFG:** 1.0 (FLUX uses lower CFG)
- **VRAM:** ~24GB

## Usage

### Load in ComfyUI UI
1. Open ComfyUI at http://192.168.1.203:8188
2. Click "Load" button or drag workflow JSON onto canvas
3. Modify prompt text in CLIP Text Encode nodes
4. Click "Queue Prompt"

### API Usage
```python
import requests
import json

# Load workflow
with open('sdxl-basic.json') as f:
    workflow = json.load(f)

# Modify prompt
for node in workflow['nodes']:
    if node.get('title') == 'Positive Prompt':
        node['widgets_values'][0] = "Your custom prompt here"

# Queue prompt
response = requests.post(
    'http://192.168.1.203:8188/prompt',
    json={'prompt': workflow}
)
prompt_id = response.json()['prompt_id']
print(f"Queued: {prompt_id}")
```

### Using hydra-tools
```python
from hydra_tools import generate_image

result = generate_image(
    prompt="A beautiful sunset over mountains",
    negative_prompt="blurry, low quality",
    width=1024,
    height=1024,
    steps=25,
    workflow="default"  # Uses SDXL
)
print(result)
```

## Required Models

### For SDXL Workflow
Download to `/mnt/user/models/diffusion/`:
- `sd_xl_base_1.0.safetensors` - Base model

### For FLUX Workflow
Download to `/mnt/user/models/diffusion/`:
- `flux1-dev.safetensors` - Main model (~24GB)
- `t5xxl_fp16.safetensors` - Text encoder
- `clip_l.safetensors` - CLIP encoder
- `ae.safetensors` - VAE

## Customization

### Changing Resolution
Find the `EmptyLatentImage` or `EmptySD3LatentImage` node and modify:
- `widgets_values[0]` = width
- `widgets_values[1]` = height

Common resolutions:
- 1024x1024 (square)
- 1280x768 (landscape)
- 768x1280 (portrait)

### Changing Sampler
Find the `KSampler` node and modify:
- `widgets_values[3]` = CFG scale
- `widgets_values[4]` = sampler name (euler, euler_ancestral, dpm_2, etc.)
- `widgets_values[5]` = scheduler (normal, karras, simple, etc.)
- `widgets_values[2]` = steps

### Batch Generation
Change the batch size in `EmptyLatentImage`:
- `widgets_values[2]` = batch_size

## Performance Notes

- **SDXL** runs well on RTX 5070 Ti (16GB VRAM)
- **FLUX** requires at least 24GB VRAM (use hydra-ai 5090 or 4090)
- Set GPU power limits before heavy generation to manage thermals
- Use `/mnt/user/models/diffusion/` for model storage (NFS shared)

## Troubleshooting

### "Model not found"
Ensure model file is in ComfyUI's model directory:
```bash
ls /mnt/user/models/diffusion/
```

### Out of memory
1. Reduce resolution
2. Reduce batch size to 1
3. Use a smaller model (SDXL vs FLUX)
4. Clear VRAM: `nvidia-smi --gpu-reset` (caution: kills running jobs)

### Slow generation
1. Check GPU utilization: `nvidia-smi`
2. Verify using GPU not CPU
3. Consider reducing steps (20 is usually sufficient)
