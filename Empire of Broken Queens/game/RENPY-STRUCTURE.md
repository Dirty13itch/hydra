# Empire of Broken Queens - Ren'Py Game Structure

## Overview

Visual novel game following a male protagonist systematically seducing and corrupting powerful women ("queens"). Built with Ren'Py engine for multi-platform deployment.

---

## Project Structure

```
empire_of_broken_queens/
├── game/
│   ├── script.rpy              # Main entry, title screen, navigation
│   ├── definitions.rpy         # Character, variable, transform definitions
│   ├── screens.rpy             # Custom UI screens
│   ├── options.rpy             # Game settings
│   │
│   ├── systems/
│   │   ├── corruption.rpy      # Corruption mechanics and tracking
│   │   ├── harem.rpy           # Multi-queen jealousy/alliance system
│   │   ├── phone.rpy           # Phone interface for communication
│   │   ├── gallery.rpy         # CG gallery with unlock tracking
│   │   └── achievements.rpy    # Achievement system
│   │
│   ├── characters/
│   │   ├── player.rpy          # Player character definition
│   │   └── queens/
│   │       ├── emilie.rpy      # Emilie Ekström (Nordic Ice)
│   │       ├── jordan.rpy      # Jordan Night (Ink Queen)
│   │       ├── nikki.rpy       # Nikki Benz (Golden Empress)
│   │       └── ...             # Other queens
│   │
│   ├── story/
│   │   ├── prologue.rpy        # Game introduction
│   │   ├── act1/               # First act (discovery)
│   │   │   ├── chapter1.rpy
│   │   │   ├── chapter2.rpy
│   │   │   └── chapter3.rpy
│   │   ├── act2/               # Second act (expansion)
│   │   ├── act3/               # Third act (dominion)
│   │   └── endings/
│   │       ├── true_ending.rpy
│   │       ├── harem_endings.rpy
│   │       └── queen_endings/
│   │           ├── emilie_ending.rpy
│   │           └── ...
│   │
│   ├── scenes/
│   │   ├── common/             # Shared scene scripts
│   │   └── queens/
│   │       ├── emilie/
│   │       │   ├── introduction.rpy
│   │       │   ├── first_meeting.rpy
│   │       │   ├── corruption_path.rpy
│   │       │   ├── awakening.rpy
│   │       │   ├── surrender.rpy
│   │       │   └── intimate/
│   │       │       ├── scene_1.rpy
│   │       │       └── ...
│   │       └── ...
│   │
│   └── images/
│       ├── ui/                 # UI assets
│       ├── backgrounds/        # Scene backgrounds
│       ├── cg/                 # Full CG scenes
│       └── characters/
│           ├── emilie/
│           │   ├── neutral.png
│           │   ├── smirk.png
│           │   └── ...expressions
│           └── ...
│
├── audio/
│   ├── music/                  # Background music
│   ├── sfx/                    # Sound effects
│   └── voice/
│       ├── emilie/             # Voice lines per queen
│       └── ...
│
└── saves/                      # Save data location
```

---

## Core Systems

### 1. Corruption System (`systems/corruption.rpy`)

```renpy
# Corruption tracking per queen
default emilie_corruption = 0
default jordan_corruption = 0
default nikki_corruption = 0

# Corruption thresholds
define CORRUPTION_COLD = 0       # 0-25: Cold, resistant
define CORRUPTION_CURIOUS = 25   # 25-50: Curious, testing
define CORRUPTION_AWAKENING = 50 # 50-75: Awakening, conflicted
define CORRUPTION_SURRENDER = 75 # 75-100: Surrendered, devoted

# Function to increase corruption with bounds checking
init python:
    def add_corruption(queen, amount):
        current = getattr(store, f"{queen}_corruption")
        new_value = min(100, max(0, current + amount))
        setattr(store, f"{queen}_corruption", new_value)

        # Trigger threshold events
        if current < 25 <= new_value:
            renpy.call("on_threshold_curious", queen)
        elif current < 50 <= new_value:
            renpy.call("on_threshold_awakening", queen)
        elif current < 75 <= new_value:
            renpy.call("on_threshold_surrender", queen)

    def get_corruption_stage(queen):
        value = getattr(store, f"{queen}_corruption")
        if value < 25:
            return "cold"
        elif value < 50:
            return "curious"
        elif value < 75:
            return "awakening"
        else:
            return "surrendered"
```

### 2. Character Definitions (`definitions.rpy`)

```renpy
# Character voice definitions
define e = Character("Emilie", color="#9eb8d9", voice_tag="emilie")
define j = Character("Jordan", color="#4a6670", voice_tag="jordan")
define n = Character("Nikki", color="#d4af37", voice_tag="nikki")

# Player
define mc = Character("[player_name]", color="#ffffff")

# Narrator
define narrator = Character(None, kind=nvl)

# Character images with layered image system
layeredimage emilie:
    group base:
        attribute casual default
        attribute professional
        attribute lingerie
        attribute nude

    group expression:
        attribute neutral default
        attribute cold
        attribute smirk
        attribute surprised
        attribute blushing
        attribute aroused
        attribute surrendered

# Character positions
transform left_queen:
    xalign 0.2
    yalign 1.0

transform center_queen:
    xalign 0.5
    yalign 1.0

transform right_queen:
    xalign 0.8
    yalign 1.0
```

### 3. Phone System (`systems/phone.rpy`)

```renpy
# Phone UI for communicating with queens
screen phone_screen():
    modal True
    frame:
        style "phone_frame"
        has vbox

        # Contacts list
        text "Contacts" style "phone_header"
        for queen in available_queens:
            textbutton queen.name:
                action Show("phone_conversation", queen=queen)
                style "phone_contact"

        textbutton "Close" action Hide("phone_screen")

# Track messages and conversations
default phone_messages = {}

init python:
    def send_message(queen, message, is_player=True):
        if queen not in phone_messages:
            phone_messages[queen] = []
        phone_messages[queen].append({
            "sender": "player" if is_player else queen,
            "text": message,
            "timestamp": get_game_time()
        })
```

### 4. Harem System (`systems/harem.rpy`)

```renpy
# Track relationships between queens
default queen_relationships = {}

init python:
    class QueenRelationship:
        def __init__(self, queen1, queen2):
            self.jealousy = 0      # -100 to 100 (negative = rivalry)
            self.alliance = 0      # 0 to 100
            self.aware_of_each = False

        def trigger_jealousy_event(self):
            if self.jealousy < -50:
                return "confrontation"
            elif self.jealousy < -25:
                return "tension"
            else:
                return None

        def check_alliance_possibility(self):
            return self.alliance > 50 and self.jealousy > -25
```

---

## Scene Flow

### Scene Template
```renpy
# Template for a queen scene
label emilie_first_meeting:

    # Set up scene
    scene bg corporate_office with fade
    play music "audio/music/tension.ogg" fadeout 1.0 fadein 1.0

    # Show character
    show emilie professional neutral at center_queen with dissolve

    # Corruption stage affects dialogue
    $ stage = get_corruption_stage("emilie")

    if stage == "cold":
        e "I've reviewed your proposal. It's... adequate."
        e cold "Though I wonder if you expect me to be impressed by competence alone."

    # Player choice
    menu:
        "Compliment her business acumen":
            $ add_corruption("emilie", 2)
            jump emilie_compliment_business

        "Comment on her appearance":
            $ add_corruption("emilie", -5)
            jump emilie_comment_appearance

        "Stay professional":
            $ add_corruption("emilie", 5)
            jump emilie_stay_professional
```

---

## Save/Load Integration

```renpy
# Custom save metadata
init python:
    config.save_json_callbacks = [save_metadata]

    def save_metadata():
        return {
            "total_corruption": sum_all_corruption(),
            "queens_surrendered": count_surrendered_queens(),
            "chapter": current_chapter,
            "playtime": get_playtime()
        }

# Save screen with preview
screen save_slot(slot):
    button:
        action FileAction(slot)
        has vbox

        add FileScreenshot(slot)
        text FileTime(slot, format="%m/%d %H:%M")
        text "Corruption: [save_metadata['total_corruption']]%"
```

---

## Gallery System

```renpy
# Track unlocked CG images
default unlocked_gallery = set()

init python:
    def unlock_cg(cg_id):
        unlocked_gallery.add(cg_id)
        renpy.save_persistent()

    def is_unlocked(cg_id):
        return cg_id in unlocked_gallery

# Gallery screen
screen gallery():
    grid 4 4:
        for cg_id in all_cgs:
            if is_unlocked(cg_id):
                imagebutton:
                    idle cg_id
                    action Show("cg_viewer", cg=cg_id)
            else:
                null width 200 height 200
```

---

## Build Configuration (`options.rpy`)

```renpy
# Game metadata
define config.name = "Empire of Broken Queens"
define config.version = "1.0.0"

# Window settings
define config.screen_width = 1920
define config.screen_height = 1080
define config.window_title = "Empire of Broken Queens"

# Save settings
define config.save_directory = "EmpireOfBrokenQueens"
define config.savedir = "save"

# Build targets
init python:
    build.name = "EmpireOfBrokenQueens"

    # Archives for distribution
    build.archive("scripts", "game")
    build.archive("images", "images")
    build.archive("audio", "audio")

    # Classify files
    build.classify("game/**.rpy", "scripts")
    build.classify("game/**.png", "images")
    build.classify("audio/**", "audio")

    # Platform builds
    build.classify("**.py", None)
    build.classify("**.txt", None)
```

---

## Development Workflow

### 1. Asset Integration
```bash
# Copy generated images to game/images
cp /path/to/generated/portraits/* game/images/characters/

# Organize by queen
mv emilie_*.png game/images/characters/emilie/
mv jordan_*.png game/images/characters/jordan/
```

### 2. Dialogue Import
```python
# Script to convert generated dialogue to .rpy format
def convert_dialogue_to_rpy(dialogue_json, output_file):
    with open(dialogue_json) as f:
        dialogue = json.load(f)

    with open(output_file, 'w') as f:
        for line in dialogue:
            f.write(f'{line["speaker"]} "{line["text"]}"\n')
```

### 3. Testing
```bash
# Launch in developer mode
renpy . --developer
```

---

## Performance Considerations

1. **Image Compression**: Use .webp for backgrounds, .png for characters
2. **Audio**: 128kbps MP3 for music, 96kbps for voice
3. **Prediction**: Use `renpy.predict()` for smoother transitions
4. **Memory**: Unload unused images with `renpy.free_memory()`

---

*Ren'Py Structure v1.0*
*December 12, 2025*
