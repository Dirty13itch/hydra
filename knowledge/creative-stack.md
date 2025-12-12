# Creative Stack Knowledge Base

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Creative Interfaces                              │
├──────────────────┬──────────────────┬──────────────────────────────────┤
│   SillyTavern    │    Open WebUI    │     Custom Apps (Ren'Py)         │
│     :8000        │      :3000       │                                   │
└────────┬─────────┴────────┬─────────┴─────────────────┬────────────────┘
         │                  │                           │
         ▼                  ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          LiteLLM (:4000)                                │
│                      (Routes to appropriate backend)                     │
└────────┬────────────────────┬───────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│    TabbyAPI     │  │     Ollama      │
│  (70B models)   │  │   (7B-14B)      │
└─────────────────┘  └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Image Generation                                 │
│                    ComfyUI (hydra-compute:8188)                         │
│                         RTX 5070 Ti                                      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                           Voice Pipeline                                 │
├─────────────────────────────┬───────────────────────────────────────────┤
│      TTS (Kokoro/Piper)     │        STT (faster-whisper)               │
│         :8880/:10200        │                                           │
└─────────────────────────────┴───────────────────────────────────────────┘
```

## ComfyUI (Image Generation)

### Location
- **Node:** hydra-compute
- **Port:** 8188
- **GPU:** RTX 5070 Ti (16GB VRAM)
- **Models:** `/mnt/models/diffusion/`

### Installation (NixOS)
```bash
# Clone
git clone https://github.com/comfyanonymous/ComfyUI /opt/comfyui
cd /opt/comfyui

# Create venv
python -m venv venv
source venv/bin/activate

# Install with CUDA 12.8
pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt

# Symlink models
ln -s /mnt/models/diffusion/checkpoints models/checkpoints
ln -s /mnt/models/diffusion/loras models/loras
ln -s /mnt/models/diffusion/controlnet models/controlnet
```

### Systemd Service
```nix
systemd.services.comfyui = {
  description = "ComfyUI Image Generation";
  after = [ "network.target" ];
  wantedBy = [ "multi-user.target" ];
  
  serviceConfig = {
    Type = "simple";
    User = "typhon";
    WorkingDirectory = "/opt/comfyui";
    ExecStart = "${pkgs.bash}/bin/bash -c 'source venv/bin/activate && python main.py --listen 0.0.0.0 --port 8188'";
    Restart = "always";
  };
};
```

### Recommended Checkpoints

| Model | Base | VRAM | Best For |
|-------|------|------|----------|
| Pony Diffusion V6 XL | SDXL | 8-10GB | Anime, stylized, NSFW |
| epiCRealism XL | SDXL | 8-10GB | Photorealistic, NSFW |
| RealVisXL | SDXL | 8-10GB | Realistic people |
| Juggernaut XL | SDXL | 8-10GB | General photorealistic |
| Flux.1-dev | Custom | 12-16GB | Best text, hands |

### Essential Custom Nodes
```bash
cd /opt/comfyui/custom_nodes

# Manager (install others via UI)
git clone https://github.com/ltdrdata/ComfyUI-Manager

# ControlNet
git clone https://github.com/Fannovel16/comfyui_controlnet_aux

# IPAdapter (character consistency)
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus

# Face tools
git clone https://github.com/Gourieff/comfyui-reactor-node
```

### API Usage
```python
import requests
import json

# Queue prompt
workflow = {...}  # Your workflow JSON
response = requests.post(
    "http://192.168.1.203:8188/prompt",
    json={"prompt": workflow}
)
prompt_id = response.json()["prompt_id"]

# Check status
status = requests.get(f"http://192.168.1.203:8188/history/{prompt_id}")

# Get images
images = requests.get(f"http://192.168.1.203:8188/view?filename=...")
```

## SillyTavern (RP Interface)

### Location
- **Port:** 8000 (hydra-storage Docker)
- **Purpose:** Roleplay, creative writing, character cards

### Docker Setup
```yaml
sillytavern:
  image: ghcr.io/sillytavern/sillytavern:latest
  container_name: sillytavern
  ports:
    - 8000:8000
  volumes:
    - /mnt/user/appdata/sillytavern/config:/home/node/app/config
    - /mnt/user/appdata/sillytavern/data:/home/node/app/data
  environment:
    - TZ=America/Chicago
  restart: unless-stopped
```

### Configuration

#### Connect to LiteLLM
1. Settings → API Connections
2. Select "Chat Completion (OpenAI)"
3. API URL: `http://192.168.1.244:4000/v1`
4. API Key: Your LiteLLM key
5. Model: `llama-70b` or as configured

#### Connect to ComfyUI (for character images)
1. Extensions → Image Generation
2. Enable ComfyUI
3. URL: `http://192.168.1.203:8188`
4. Import workflow for character generation

### Features
- **Character Cards:** TavernAI format (.png with embedded JSON)
- **World Info/Lorebooks:** Background knowledge
- **Instruct Mode:** Use proper chat templates
- **Group Chats:** Multiple characters
- **Extensions:** TTS, image gen, summarization

### Sampler Settings for RP
```
Temperature: 0.8
Top-P: 0.95
Top-K: 40
Repetition Penalty: 1.1
Min-P: 0.05
```

## Voice Pipeline

### Kokoro TTS (Recommended)
- **Port:** 8880
- **Model:** 82M parameters
- **License:** Apache 2.0
- **Speed:** ~210x realtime on GPU

```yaml
kokoro:
  image: ghcr.io/remsky/kokoro-fastapi:latest
  container_name: kokoro
  ports:
    - 8880:8880
  volumes:
    - /mnt/user/appdata/kokoro:/app/models
  deploy:
    resources:
      reservations:
        devices:
          - capabilities: [gpu]
  restart: unless-stopped
```

#### API (OpenAI-compatible)
```bash
curl -X POST http://192.168.1.244:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hello, how are you today?",
    "voice": "af_bella"
  }' --output speech.mp3
```

### Piper TTS (Alternative)
- **Port:** 10200
- **Faster:** CPU-friendly
- **More voices:** Many languages

```yaml
piper:
  image: rhasspy/piper:latest
  container_name: piper
  ports:
    - 10200:10200
  volumes:
    - /mnt/user/appdata/piper:/data
  restart: unless-stopped
```

### faster-whisper (STT)
- **Purpose:** Speech-to-text
- **Models:** tiny, base, small, medium, large-v3

```python
from faster_whisper import WhisperModel

model = WhisperModel("large-v3", device="cuda", compute_type="float16")
segments, info = model.transcribe("audio.mp3")

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

## Empire of Broken Queens Pipeline

### Character Art Workflow

1. **Design Phase**
   - Create character description
   - Generate concept art with ComfyUI
   - Iterate on design

2. **Consistency Training**
   - Collect 10-20 images of final design
   - Train LoRA for character (kohya_ss)
   - Test consistency across poses

3. **Production Generation**
   - Use LoRA + ControlNet for poses
   - Generate expression variants
   - Batch process with ComfyUI API

### ComfyUI Workflow for Character Sprites
```json
{
  "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "ponyDiffusionV6XL.safetensors"}},
  "2": {"class_type": "LoraLoader", "inputs": {"lora_name": "queen_victoria.safetensors", "strength": 0.8}},
  "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "1girl, queen_victoria, royal dress, standing, neutral expression"}},
  "4": {"class_type": "KSampler", "inputs": {"steps": 30, "cfg": 7, "sampler_name": "euler", "scheduler": "normal"}},
  "5": {"class_type": "VAEDecode"},
  "6": {"class_type": "SaveImage", "inputs": {"filename_prefix": "queen_victoria"}}
}
```

### Dynamic Dialogue Integration

```python
# Ren'Py integration with TabbyAPI
import requests

def get_llm_response(character, context, player_input):
    response = requests.post(
        "http://192.168.1.244:4000/v1/chat/completions",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        json={
            "model": "llama-70b",
            "messages": [
                {"role": "system", "content": character.system_prompt},
                {"role": "user", "content": f"Context: {context}\n\nPlayer: {player_input}"}
            ],
            "max_tokens": 500,
            "temperature": 0.8
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

### Live2D Integration (Future)
- **Software:** Live2D Cubism
- **Purpose:** Animate character sprites
- **Integration:** VTube Studio or custom Ren'Py module

## SillyTavern + ComfyUI Integration

### Enable Image Generation
1. Install SillyTavern extension: `Image Generation`
2. Configure ComfyUI connection
3. Import/create workflow for character images
4. Trigger via chat commands or auto-generate

### Character Card with Image Prompt
```json
{
  "name": "Queen Victoria",
  "description": "...",
  "personality": "...",
  "scenario": "...",
  "image_prompt": "1girl, queen_victoria, (masterpiece:1.2), royal dress, throne room, dramatic lighting"
}
```

## Best Practices

### Image Generation
1. Use SDXL for quality, SD 1.5 for speed
2. Train LoRAs for consistent characters
3. Use ControlNet for pose consistency
4. Batch generate with API for efficiency

### Voice
1. Use Kokoro for high quality
2. Use Piper for fast/CPU fallback
3. Create voice profiles per character
4. Pre-generate common phrases

### RP/Writing
1. Use 70B models for complex narratives
2. Use 7B-14B for quick responses
3. Set appropriate sampler settings
4. Use world info for lore consistency
