# Empire of Broken Queens - Master Execution Strategy

## Philosophy: Quality Over Speed

Every asset must meet the attraction profile. No compromise on:
- Enhanced breasts (DD-F, high-set, prominent)
- Hourglass proportions (24-26" waist)
- European features (Nordic/German/Slavic)
- Mature beauty (30s, confident, powerful)
- Photorealistic quality (8K, Arri Alexa grade)

---

## Phase 1: Foundation Assets (CURRENT)

### 1.1 Alpha Queens - Portrait Generation
**Status**: IN PROGRESS

| Queen | Target | Current | Status |
|-------|--------|---------|--------|
| Emelie Ekström | 50 | ~20 | Generating |
| Jordan Night | 50 | ~15 | Generating |
| Nikki Benz | 50 | ~12 | Generating |

**Quality Gate**: Review first 10 of each queen for attraction profile alignment before continuing.

### 1.2 Scene Backgrounds
**Status**: PENDING

Required backgrounds:
- Corporate office (Emilie's domain)
- Tattoo studio (Jordan's domain)
- Luxury mansion (Nikki's domain)
- Penthouse bedroom
- Private jet interior
- Yacht deck
- Strip club VIP room
- Boardroom
- Hotel suite

### 1.3 UI Assets
**Status**: PENDING

- Main menu background
- Text boxes
- Choice buttons
- Phone interface
- Save/Load screens
- Corruption meter graphics

---

## Phase 2: Content Generation Pipeline

### 2.1 Dialogue Generation (TabbyAPI 70B)
**Approach**: Generate dialogue in batches per queen, per corruption level.

Structure per queen:
```
corruption_0-25/   # Cold, resistant
corruption_25-50/  # Curious, testing
corruption_50-75/  # Awakening, conflicted
corruption_75-100/ # Surrendered, devoted
```

**Quality Gate**: Each dialogue must include:
- Unique voice/accent markers
- DNA trait expression (from 19-trait system)
- Progression appropriate to corruption level
- Sexual tension building naturally

### 2.2 Scene Scripts (TabbyAPI 70B)
**Priority Order**:
1. Introduction scenes (21 queens × 1 scene)
2. First corruption scenes (21 × 1)
3. Awakening scenes (21 × 1)
4. Surrender scenes (21 × 1)
5. Endings (21 × 8 = 168 scenes)

### 2.3 Branching Story
**Structure**:
- Main path: Linear progression through acts
- Queen paths: Parallel tracks per queen
- Harem events: Procedural jealousy/alliance triggers
- SoulForge: Infinite generated daughters

---

## Phase 3: Advanced Asset Generation

### 3.1 LoRA Training (For Consistency)
**Purpose**: Create queen-specific LoRAs so every image of the same queen looks consistent.

**Process**:
1. Select best 20 generated portraits per queen
2. Train LoRA on those images (30 minutes per queen)
3. Re-generate all portraits using queen-specific LoRA
4. Result: 100% consistent character across all poses/expressions

**Hydra Resources**:
- Training: hydra-compute RTX 5070 Ti (16GB)
- Inference: Same

### 3.2 Expression Sheets
Per queen, generate systematic expression variations:
- Neutral
- Smirk/knowing
- Cold/icy
- Surprised
- Blushing
- Aroused
- Surrendered
- Ecstatic
- Crying (pleasure tears)
- Post-orgasm

### 3.3 Pose Sheets
Per queen, generate systematic pose variations:
- Standing (professional)
- Seated (commanding)
- Leaning (seductive)
- Kneeling (submissive)
- Lying (vulnerable)
- Arched (pleasure)
- Various states of undress (5 levels)

---

## Phase 4: Video Pipeline

### 4.1 AnimateDiff/Mochi Setup
**Status**: AnimateDiff model downloaded (v3_sd15_mm.ckpt)

**Video Types**:
1. **Idle animations** (2-3 seconds, looping)
   - Breathing
   - Blinking
   - Subtle sway

2. **Reaction clips** (3-5 seconds)
   - Gasp
   - Moan
   - Surrender moment

3. **Scene videos** (15-90 seconds)
   - Awakening cinematics
   - Surrender sequences
   - Endings

### 4.2 Video Generation Order
1. Idle loops for Alpha queens (quick wins)
2. Key reaction clips
3. Awakening cinematics (most impactful)
4. Full scene videos (resource intensive)

---

## Phase 5: Voice Pipeline

### 5.1 Voice Cloning (RVC v2.2)
**Deployment**: hydra-compute

**Per Queen Voice Profile**:
- Base accent (Swedish, German, Ukrainian, etc.)
- Emotional range samples
- Signature sounds (gasp, moan style)
- Unique verbal tics

### 5.2 Text-to-Speech (XTTS v2.1)
**Integration**: Generate voice lines from dialogue scripts

**Quality Requirements**:
- Natural prosody
- Emotional expression
- Accent consistency
- Breathing/pause insertion

---

## Phase 6: Game Integration

### 6.1 Ren'Py Implementation
**Structure**:
```
game/
├── script.rpy           # Main game flow
├── characters.rpy       # Character definitions
├── variables.rpy        # Game state
├── screens.rpy          # UI definitions
├── queens/
│   ├── emilie.rpy       # Emilie's complete path
│   ├── jordan.rpy       # Jordan's complete path
│   └── ...              # 21 queen files
├── systems/
│   ├── corruption.rpy   # Corruption mechanics
│   ├── harem.rpy        # Jealousy/alliance system
│   ├── phone.rpy        # Phone interface
│   └── soulforge.rpy    # Daughter generation
└── endings/
    └── ...              # 168 ending scripts
```

### 6.2 Save System
**PostgreSQL Integration**:
- Cloud saves (optional)
- Local saves (primary)
- Achievement tracking
- Gallery unlocks

### 6.3 Testing
**Automated**:
- Path completion testing
- Variable state verification
- Image/audio asset loading

**Manual**:
- Story coherence
- Pacing
- Emotional impact
- Sexual content quality

---

## Resource Allocation

### Hydra Cluster Usage (Updated for Dual 5070 Ti)

| Task | Node | GPU | VRAM Usage |
|------|------|-----|------------|
| Portrait Generation (Parallel) | hydra-compute | 2x RTX 5070 Ti | 2x 8GB |
| LoRA Training | hydra-compute | RTX 5070 Ti #1 | 12GB |
| Video Generation | hydra-compute | RTX 5070 Ti #2 | 12GB |
| Dialogue Generation | hydra-ai | RTX 5090 | 31GB (TabbyAPI) |
| Voice Cloning | hydra-compute | RTX 5070 Ti #2 | 4GB |
| TTS Generation | hydra-compute | RTX 5070 Ti #2 | 2GB |

**GPU Configuration:**
- hydra-compute: Dual RTX 5070 Ti (16GB each, 32GB total) - homogeneous setup
- hydra-ai: RTX 5090 (32GB) + RTX 4090 (24GB)

### Parallel Processing Strategy (Optimized for Dual GPU)
- **Dual Portrait Generation**: Split batches across GPU 0 and GPU 1 for 2x throughput
- **LoRA + Video**: Train LoRA on GPU 0 while generating video on GPU 1
- **Voice + Images**: Voice pipeline on GPU 1 while images on GPU 0
- **Zero Downtime**: Homogeneous GPUs allow seamless load balancing
- **Dialogue runs independently on hydra-ai**

---

## Quality Gates

### Gate 1: Portrait Review (After 10 per queen)
- Do breasts match attraction profile?
- Is hourglass evident?
- Are features European?
- Is age presentation correct?
- Is quality photorealistic?

### Gate 2: Dialogue Review (After 50 lines per queen)
- Is voice distinctive?
- Does corruption progression feel natural?
- Is content appropriately explicit?
- Are DNA traits expressed?

### Gate 3: Scene Integration (After 5 scenes per queen)
- Do assets load correctly?
- Is pacing right?
- Does emotion build properly?
- Are transitions smooth?

### Gate 4: Playtest (After Act 1 complete)
- Is it engaging?
- Is it arousing?
- Does the fantasy land?
- Are there technical issues?

---

## Timeline (Flexible - No Deadlines)

### Week 1: Foundation
- Complete Alpha queen portraits (150 total)
- Generate 10 backgrounds
- Create base UI

### Week 2: Content
- Generate dialogue for Alpha queens
- Train LoRAs for consistency
- Begin video idle loops

### Week 3: Integration
- Implement Ren'Py for Alpha queens
- Phone system
- Basic saves

### Week 4: Expansion
- Research and generate next 6 queens
- Voice cloning setup
- More video content

### Ongoing: Iteration
- Quality review and regeneration
- Additional queens
- SoulForge system
- Polish

---

## Success Metrics

The game is successful when:
1. Every queen looks consistent across all images
2. Every queen's personality is distinct and compelling
3. The corruption progression feels inevitable but earned
4. The sexual content is the hottest you've ever seen in a VN
5. The "blissful surrender" fantasy lands perfectly
6. You can't stop playing

---

*Strategy Version: 1.1*
*Updated: December 12, 2025*
*Changes: Updated for dual RTX 5070 Ti configuration on hydra-compute (replacing 5070 Ti + 3060)*
