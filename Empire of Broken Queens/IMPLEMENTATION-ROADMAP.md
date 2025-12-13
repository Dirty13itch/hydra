# Empire of Broken Queens - Implementation Roadmap

## Current Hydra Cluster Status

### Operational Now
| Service | Location | Status | Use Case |
|---------|----------|--------|----------|
| TabbyAPI 70B | hydra-ai:5000 | **RUNNING** | Dialogue, story, DNA generation |
| ComfyUI | hydra-compute:8188 | **RUNNING** | Queen portraits, scene images |
| PostgreSQL | hydra-storage:5432 | **RUNNING** | Save games, queen states |
| Redis | hydra-storage:6379 | **RUNNING** | Session cache |
| n8n | hydra-storage:5678 | **RUNNING** | Pipeline orchestration |

### Needs Deployment
| Service | Target | Priority | Use Case |
|---------|--------|----------|----------|
| Mochi 1 | hydra-ai | HIGH | Video generation |
| Wan 2.2 | hydra-ai | HIGH | NSFW video effects |
| RVC v2.2 | hydra-compute | MEDIUM | Voice cloning |
| XTTS v2.1 | hydra-compute | MEDIUM | Text-to-speech |
| Live2D Runtime | hydra-dev | LOW | Character animation |

---

## Phase 1: Foundation (Days 1-3)

### Day 1: Project Setup
```bash
# Create Ren'Py project
mkdir -p /mnt/shared/empire-of-broken-queens/game
cd /mnt/shared/empire-of-broken-queens/game
renpy.sh --new-project "Empire of Broken Queens"
```

**Tasks:**
- [ ] Initialize Ren'Py 8.5.0 project
- [ ] Set up Git repository
- [ ] Configure asset directories
- [ ] Create database schema

### Day 2: Database Schema
```sql
-- PostgreSQL schema for Empire of Broken Queens
CREATE TABLE queens (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    dna JSONB,  -- 19-trait DNA
    corruption INTEGER DEFAULT 0,
    relationship_level INTEGER DEFAULT 0,
    unlocked_scenes TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE player_saves (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(100),
    current_chapter INTEGER,
    money BIGINT,
    queens_tamed INTEGER[],
    flags JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE generated_daughters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    parent_queens INTEGER[],
    dna JSONB,
    lora_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Day 3: Base Asset Pipeline
```python
# ComfyUI workflow for queen portrait generation
# Save as: queen_portrait_workflow.json

PORTRAIT_PROMPT = """
hyperreal 4K cinematic {body_type} woman {height}
{measurements}, {eye_color} {eye_shape} eyes,
{skin_tone} skin, {hair_color} {hair_style} hair,
Arri Alexa color, studio lighting, 8K detail
"""
```

---

## Phase 2: Alpha Queens (Days 4-10)

### Priority Queens for Wave 1
1. **Emilie Ekstrom** - Nordic Ice Queen (Profile 1)
2. **Jordan Night** - German Tattoo Queen (Profile 2)
3. **Nikki Benz** - Eastern European Royal (Profile 4)

### Per-Queen Generation Pipeline

```
For each queen:
1. Generate 50 base portraits (ComfyUI)
2. Generate 20 expression variations
3. Generate 10 pose variations
4. Write 100+ dialogue lines (TabbyAPI)
5. Create scene scripts (TabbyAPI)
6. Compile to Ren'Py assets
```

### ComfyUI Batch Script
```bash
# Generate queen portraits
ssh typhon@192.168.1.203 "cd /tmp && cat > generate_queen.py << 'EOF'
import requests
import json

COMFY_URL = "http://localhost:8188"
QUEENS = [
    {
        "name": "emilie",
        "prompt": "hyperreal 4K cinematic athletic Nordic woman 5'10\" 34DD high-set implants, hazel almond eyes, porcelain freckled skin, chestnut long hair, Arri Alexa, studio lighting",
        "model": "RealVisXL_V5.0.safetensors"
    },
    # ... more queens
]

# Queue generation for each queen
for queen in QUEENS:
    workflow = create_workflow(queen)
    requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow})
EOF
python3 generate_queen.py"
```

---

## Phase 3: Content Generation (Days 11-20)

### Dialogue Generation via TabbyAPI

```bash
# Generate queen dialogue
ssh typhon@192.168.1.250 "curl -s http://localhost:5000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    \"model\": \"Midnight-Miqu-70B-v1.5-exl2-2.5bpw\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": \"Write 10 flirtatious dialogue lines for Queen Emilie, an ice queen CEO with a hidden stripper past. She has a cold Swedish accent. Include her slowly warming to the player. Be explicit with innuendo.\"
    }],
    \"max_tokens\": 1500
  }'"
```

### Scene Script Structure
```renpy
# Example scene script structure
label emilie_office_pole:
    scene bg office_night
    show emilie business_suit

    mc "Dance for the board, Emilie."

    emilie "You can't be serious..."
    show emilie blush

    emilie "...Sir."

    # Video cutscene (future)
    # renpy.movie_cutscene("emilie_pole.mp4")

    show emilie surrender_pose
    emilie "I... I shouldn't want this..."

    return
```

---

## Phase 4: Video Pipeline (Days 21-30)

### Deploy Mochi on hydra-ai

```bash
# Deploy Mochi video generation
ssh typhon@192.168.1.250 "
# Clone Mochi
git clone https://github.com/genmo/mochi-1-preview /opt/mochi

# Install dependencies
cd /opt/mochi
pip install -r requirements.txt

# Download model
python scripts/download_model.py

# Test generation
python generate.py --prompt 'elegant woman pole dancing' --output test.mp4
"
```

### Video Workflow
```
Image → Mochi (base motion) → Wan (NSFW effects) → Output
                                    ↓
                              - Fluid physics
                              - Jiggle effects
                              - Tear trails
```

---

## Phase 5: Voice Pipeline (Days 31-40)

### Deploy RVC + XTTS

```bash
# Deploy voice cloning
ssh typhon@192.168.1.203 "
# Clone RVC
git clone https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI /opt/rvc

# Clone XTTS
pip install TTS

# Test voice clone
python -m TTS.api --model_name tts_models/multilingual/multi-dataset/xtts_v2
"
```

### Voice DNA Mapping
| Queen | Accent | Characteristics |
|-------|--------|-----------------|
| Emilie | Swedish | Cold, breath catches on "Sir" |
| Jordan | German | Smoky Hamburg, laugh-gasp |
| Nikki Benz | Eastern European | Royal, commanding |
| Chloe | French | Husky, delayed explosive |
| Esperanza | Spanish | Loud, passionate |

---

## Phase 6: SoulForge Integration (Days 41-50)

### n8n Workflow: Daughter Generation

```json
{
  "name": "SoulForge Daughter Generator",
  "nodes": [
    {
      "type": "webhook",
      "name": "Trigger",
      "parameters": {"path": "/generate-daughter"}
    },
    {
      "type": "httpRequest",
      "name": "Select Parents",
      "parameters": {
        "url": "http://192.168.1.244:5432/select_parents",
        "method": "POST"
      }
    },
    {
      "type": "httpRequest",
      "name": "Merge LoRAs",
      "parameters": {
        "url": "http://192.168.1.203:8188/prompt",
        "method": "POST"
      }
    },
    {
      "type": "httpRequest",
      "name": "Generate DNA",
      "parameters": {
        "url": "http://192.168.1.250:5000/v1/chat/completions",
        "method": "POST"
      }
    },
    {
      "type": "httpRequest",
      "name": "Generate Assets",
      "parameters": {
        "url": "http://192.168.1.203:8188/prompt",
        "method": "POST"
      }
    }
  ]
}
```

---

## Resource Allocation

### GPU VRAM Budget

**hydra-ai (RTX 5090 32GB + RTX 4090 24GB = 56GB)**
- TabbyAPI 70B: ~31GB (current)
- Mochi video: ~8GB (when deployed)
- Headroom: ~17GB

**hydra-compute (RTX 5070 Ti 16GB + RTX 3060 12GB = 28GB)**
- ComfyUI SDXL: ~8GB
- RVC voice: ~4GB
- XTTS: ~2GB
- Headroom: ~14GB

### Storage Budget
- Queen assets (21 × 2GB): 42GB
- Video scenes: 100GB
- Voice lines: 10GB
- Generated daughters: Unlimited (prune old)

---

## Milestones

### Wave 1 (December 25, 2025)
- [ ] 12 playable queens
- [ ] Full image assets
- [ ] Dialogue trees complete
- [ ] Basic Ren'Py build
- [ ] Save system working

### Full Launch (February 14, 2026)
- [ ] All 21 queens
- [ ] Video scenes integrated
- [ ] Voice acting complete
- [ ] SoulForge operational
- [ ] All 168 endings

---

## Quick Commands

```bash
# Check cluster status
ssh typhon@192.168.1.250 "curl -s http://localhost:5000/v1/model"
ssh typhon@192.168.1.203 "curl -s http://localhost:8188/system_stats"

# Generate content
ssh root@192.168.1.244 "/mnt/user/hydra_shared/overnight/quick-content.sh"

# View generated assets
ls /mnt/shared/empire-of-broken-queens/

# Monitor generation
tail -f /tmp/overnight-content/continuous.log
```

---

*Roadmap Version: 1.0*
*Last Updated: December 12, 2025*
