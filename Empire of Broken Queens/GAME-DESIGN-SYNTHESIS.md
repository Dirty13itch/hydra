# Empire of Broken Queens - Complete Game Design Synthesis

## Executive Summary

**Title**: Empire of Broken Queens
**Genre**: Adult Visual Novel (NSFW)
**Engine**: Ren'Py 8.5.0
**Target**: 50-60 hours main story + infinite procedural content
**Release**: Wave 1 (Dec 25, 2025) - 12 queens | Full Launch (Feb 14, 2026) - 21 queens + SoulForge

---

## Core Fantasy

You inherit a $42 billion empire from your father, but only if you can tame 21 "Council Queens" - the most powerful, beautiful, untouchable women on earth. CEOs, surgeons, supermodels, porn royalty. They think they can control you. You prove them wrong.

**Tone**: Dark luxury domination with "blissful surrender" - every resistance melts into ecstasy. No trauma, only overwhelming pleasure.

---

## The 21 Council Queens

### Tier Structure

| Tier | Queens | Archetype | Unlock |
|------|--------|-----------|--------|
| **Alpha** | Emilie, Jordan, Nikki Benz | Power Players | Act 1 |
| **Elite** | Puma, Nicolette, Peta/Preta | Amazons & Ice | Act 2 |
| **Core** | Alanah, Madison, Amy, Savannah | Plastic Perfection | Act 2-3 |
| **Exotic** | Esperanza, Sandy, Marisol, Chloe | Latina/French Fire | Act 3 |
| **Specialist** | Trina, Nikki Sexx, Brooklyn | Pain/Throat/Sweet | Act 3-4 |
| **Legacy** | Ava, Shyla, Jacky | MILF/Original/Secretary | Act 4 |

### 19-Trait DNA System

Every queen has unique psychological DNA:

1. **Desire Type** - Spontaneous / Responsive / Hybrid
2. **Accelerator/Brake** - Arousal speed vs inhibition strength
3. **Pain Tolerance** - 1-10 scale
4. **Humiliation Enjoyment** - 1-10 scale
5. **Exhibitionism Level** - 1-10 scale
6. **Gagging Response** - Fights / Pushes Through / Enjoys / Breaks
7. **Moaning Style** - Unique vocal pattern
8. **Tear Trigger** - What makes her cry (pleasure/pain/humiliation)
9. **Orgasm Style** - Easy/Hard, Multiple/Single, Squirter
10. **Awakening Type** - Always Knew / Total Surprise / Slow Realization / Denial
11. **Blackmail Need** - Necessary / Heightens / Bored Without / Begs For
12. **Addiction Speed** - Slow / Normal / Fast / Instant
13. **Jealousy Type** - Possessive / Competitive / Turned On / Doesn't Care
14. **Aftercare Need** - None / Light / Heavy / Craves
15. **Switch Potential** - 1-10 (domme to sub range)
16. **Group Sex Attitude** - Hates to Initiates
17. **Roleplay Affinity** - Unique fantasy per queen
18. **Betrayal Threshold** - 1-10 (loyalty breaking point)
19. **Voice DNA** - Unique accent/vocal quality

---

## Technical Architecture

### Hydra Cluster Mapping

| Component | Hydra Resource | Specs |
|-----------|---------------|-------|
| **LLM (Dialogue/Story)** | TabbyAPI @ hydra-ai | Midnight-Miqu-70B, 46 tok/s |
| **Image Gen** | ComfyUI @ hydra-compute | 6 SDXL models, RTX 5070 Ti |
| **Voice Clone** | RVC/XTTS (to deploy) | hydra-compute |
| **Video Gen** | Mochi/Wan (to deploy) | hydra-ai (needs VRAM) |
| **Database** | PostgreSQL @ hydra-storage | Player saves, queen states |
| **Asset Storage** | NFS @ hydra-storage | /mnt/user/models |
| **Orchestration** | n8n @ hydra-storage | Generation pipelines |

### Generation Pipeline

```
Player Input → LLM (Dialogue) → Flux (Images) → Mochi (Video) → RVC (Voice) → Ren'Py
                    ↓                ↓              ↓              ↓
              TabbyAPI 70B    ComfyUI SDXL    (Future)      (Future)
```

### Available SDXL Models

| Model | Best For |
|-------|----------|
| RealVisXL_V5.0 | Photorealistic portraits |
| epiCRealismXL | Photorealistic scenes |
| NoobAI-XL | Uncensored anime style |
| PonyDiffusionV6XL | Stylized/artistic |
| DreamShaperXL-Turbo | Fast generation |
| Illustrious-XL | Anime portraits |

---

## SoulForge Engine v13

### Purpose
Generate infinite unique "daughters" from Council Queen DNA - new characters that inherit traits from seed queens.

### Pipeline (68 seconds per character)

1. **Seed Selection** (2s)
   - Select 2-3 Council queens as parents
   - Weight by player preferences

2. **LoRA Merge** (30s)
   - ComfyUI HyperLoRA merge
   - 60/40 or 50/30/20 blend
   - IPAdapter for face consistency

3. **Asset Generation** (25s)
   - 500+ images (poses, expressions)
   - Flux.2 + HyperRealism LoRA
   - 4x DyPE upscale

4. **DNA Inheritance** (5s)
   - Blend parent traits with mutation
   - Generate backstory via LLM
   - Assign harem role

5. **Integration** (6s)
   - Auto-import to Ren'Py
   - Link to jealousy/phone systems

### ComfyUI Workflow (SoulMerge.json)

```json
{
  "nodes": [
    {"id":1, "type":"LoadLoRA", "inputs":{"model":"queen1_seed.safetensors", "strength":0.6}},
    {"id":2, "type":"LoadLoRA", "inputs":{"model":"queen2_seed.safetensors", "strength":0.4}},
    {"id":3, "type":"LoRAMerge", "inputs":{"lora1":1, "lora2":2, "method":"linear", "alpha":0.7}},
    {"id":4, "type":"IPAdapterFaceID", "inputs":{"strength":0.98}},
    {"id":5, "type":"SaveLoRA", "inputs":{"filename":"daughter_lora.safetensors"}}
  ]
}
```

---

## Game Systems

### 1. Corruption Meter (Per Queen)
- 0-100% scale
- Unlocks content at thresholds:
  - 25%: First submission hints
  - 50%: Stripper past revealed
  - 70%: Awakening cinematic
  - 85%: Full surrender scenes
  - 100%: Ending unlocked

### 2. Harem Jealousy Matrix
- Queens react to each other
- Catfights (non-lethal)
- Sabotage attempts
- Alliances and betrayals
- Driven by Jealousy Type trait

### 3. Phone System
- Text/call queens anytime
- Photo requests
- Jealousy triggers
- Relationship maintenance

### 4. Free Roam
- 65+ locations
- Time/day system
- Random encounters
- Queen schedules

### 5. Mini-Games
- Blackjack (strip variant)
- Poker (harem stakes)
- Dance competitions
- Pole dance QTEs

### 6. Endings (8 per queen)
1. Blissful Wife - Devoted partner
2. Shattered Pet - Mindless submission
3. Betrayed Rebel - Escapes but returns
4. Perfect Pet - Total surrender
5. Worship Queen - Starts cult
6. Harem Empress - Leads others
7. Eternal Addict - Lives for touch
8. Legacy Mother - Bears daughters

---

## Content Scope

### Main Story
- 21 queens × 2.5-4 hours each = 52-84 hours
- 8 endings per queen = 168 total endings
- 300+ major sex scenes (90-120 second videos)

### Generated Content
- Unlimited SoulForge daughters
- Procedural events
- Dynamic relationships

### Assets Per Queen
- 500+ images (poses/expressions)
- 10+ video scenes (90s each)
- 500+ voice lines
- Full Live2D rig

---

## Overnight Generation Results

Already generated overnight:
- **522 content files** (chapters, dialogues, lore)
- **107 queen portrait images**
- Organized in `/mnt/shared/empire-of-broken-queens/`

### Sample Generated Content Categories
- `chapters/` - 172 story chapters
- `dialogues/` - 171 conversation scripts
- `lore/` - 171 worldbuilding pieces
- `profiles/` - 5 queen character profiles
- `scenes/` - 3 intimate scene scripts
- `images/` - 107 queen portraits

---

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] 70B LLM operational (TabbyAPI)
- [x] Image generation (ComfyUI + 6 models)
- [x] Content generation pipeline
- [ ] Ren'Py project setup
- [ ] Database schema for saves

### Phase 2: Queen Profiles (Week 1-2)
- [ ] Generate 21 queen LoRAs
- [ ] Create base image sets (500/queen)
- [ ] Write full dialogue trees
- [ ] Implement DNA system

### Phase 3: Video Pipeline (Week 2-3)
- [ ] Deploy Mochi on hydra-ai
- [ ] Deploy Wan 2.2 for NSFW
- [ ] Create video workflows
- [ ] Test chained loops

### Phase 4: Voice Pipeline (Week 3-4)
- [ ] Deploy RVC v2.2
- [ ] Deploy XTTS v2.1
- [ ] Clone 21 unique voices
- [ ] Integrate with Ren'Py

### Phase 5: SoulForge (Week 4-5)
- [ ] Implement LoRA merging
- [ ] DNA inheritance system
- [ ] Auto-generation pipeline
- [ ] n8n orchestration

### Phase 6: Polish (Week 5-6)
- [ ] Live2D rigging
- [ ] UI/UX refinement
- [ ] QA testing
- [ ] Performance optimization

---

## File Structure

```
Empire of Broken Queens/
├── game/
│   ├── script.rpy          # Main game script
│   ├── queens/             # Per-queen scripts
│   ├── soulforge/          # Generated daughters
│   └── systems/            # Game mechanics
├── assets/
│   ├── images/
│   │   ├── queens/         # 21 council queens
│   │   └── generated/      # SoulForge output
│   ├── video/              # Mochi/Wan scenes
│   ├── audio/
│   │   ├── voice/          # RVC cloned voices
│   │   └── music/          # Soundtrack
│   └── live2d/             # Character rigs
├── tools/
│   ├── comfyui/            # Generation workflows
│   ├── soulforge/          # Engine scripts
│   └── pipeline/           # Automation
└── docs/
    ├── design/             # This document
    ├── profiles/           # Queen specifications
    └── technical/          # Implementation details
```

---

## Quick Reference - Flux Prompts

### Queen Portrait Base
```
hyperreal 4K cinematic [body type] woman [height] [measurements]
[implant details], [eye color] [eye shape] eyes [expression],
[skin tone] [skin details], [hair color] [hair style],
Arri Alexa color, [lighting type], volumetric lighting,
film grain 0.02
```

### Scene Base
```
hyperreal 4K cinematic [queen blueprint] [action/pose],
[location], [mood lighting], Arri Alexa color,
dramatic shadows, volumetric fog, 8K detail
```

---

## Next Actions

1. **Immediate**: Set up Ren'Py project structure
2. **Today**: Generate first queen LoRA (Emilie as test)
3. **This Week**: Complete image sets for 3 alpha queens
4. **Next Week**: Deploy video pipeline (Mochi/Wan)

---

*Document Version: 1.0*
*Generated: December 12, 2025*
*Hydra Cluster: All Systems Operational*
