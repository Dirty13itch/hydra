# Empire of Broken Queens - Definitions
# Characters, variables, and transforms

# ==============================================================================
# Player Variables
# ==============================================================================

default player_name = "Marcus"

# ==============================================================================
# Corruption Tracking
# ==============================================================================

# Alpha Queens
default emilie_corruption = 0
default jordan_corruption = 0
default nikki_corruption = 0

# Elite Queens
default puma_corruption = 0
default nicolette_corruption = 0
default alanah_corruption = 0

# Core Queens
default madison_corruption = 0
default savannah_corruption = 0
default esperanza_corruption = 0

# Exotic Queens
default trina_corruption = 0
default brooklyn_corruption = 0
default ava_corruption = 0

# Legacy Queens
default shyla_corruption = 0

# ==============================================================================
# Corruption Functions
# ==============================================================================

init python:
    def add_corruption(queen, amount):
        """Add corruption to a queen (clamped 0-100)"""
        var_name = f"{queen}_corruption"
        current = getattr(store, var_name, 0)
        new_value = min(100, max(0, current + amount))
        setattr(store, var_name, new_value)

        # Check for threshold triggers
        if current < 25 <= new_value:
            renpy.notify(f"{queen.title()}'s interest is growing...")
        elif current < 50 <= new_value:
            renpy.notify(f"{queen.title()} is awakening...")
        elif current < 75 <= new_value:
            renpy.notify(f"{queen.title()} has surrendered...")

    def get_corruption(queen):
        """Get current corruption level"""
        return getattr(store, f"{queen}_corruption", 0)

    def get_corruption_stage(queen):
        """Get corruption stage name"""
        value = get_corruption(queen)
        if value < 25:
            return "cold"
        elif value < 50:
            return "curious"
        elif value < 75:
            return "awakening"
        else:
            return "surrendered"

    def sum_all_corruption():
        """Total corruption across all queens"""
        queens = ["emilie", "jordan", "nikki", "puma", "nicolette",
                  "alanah", "madison", "savannah", "esperanza",
                  "trina", "brooklyn", "ava", "shyla"]
        return sum(get_corruption(q) for q in queens)

    def count_surrendered():
        """Count queens at surrender stage"""
        queens = ["emilie", "jordan", "nikki", "puma", "nicolette",
                  "alanah", "madison", "savannah", "esperanza",
                  "trina", "brooklyn", "ava", "shyla"]
        return sum(1 for q in queens if get_corruption(q) >= 75)

# ==============================================================================
# Character Definitions
# ==============================================================================

# Alpha Queens
define e = Character("Emilie",
    color="#9eb8d9",
    who_suffix="",
    what_prefix="\"",
    what_suffix="\"")

define j = Character("Jordan",
    color="#4a6670",
    who_suffix="",
    what_prefix="\"",
    what_suffix="\"")

define n = Character("Nikki",
    color="#d4af37",
    who_suffix="",
    what_prefix="\"",
    what_suffix="\"")

# Player Character
define mc = Character("[player_name]",
    color="#ffffff",
    who_suffix="",
    what_prefix="\"",
    what_suffix="\"")

# Narrator
define narrator = Character(None)

# ==============================================================================
# Transforms
# ==============================================================================

# Character positions
transform left_pos:
    xalign 0.2
    yalign 1.0

transform center:
    xalign 0.5
    yalign 1.0

transform right_pos:
    xalign 0.8
    yalign 1.0

# Close-up for intimate scenes
transform closeup:
    xalign 0.5
    yalign 0.5
    zoom 1.5

# Breathing animation for idle
transform breathing:
    yoffset 0
    ease 2.0 yoffset 5
    ease 2.0 yoffset 0
    repeat

# Expression change
transform emotion_shift:
    alpha 1.0
    ease 0.3 alpha 0.0
    ease 0.3 alpha 1.0

# ==============================================================================
# Layered Images (Placeholder structure)
# ==============================================================================

# Emilie - layered image for outfit/expression combinations
# layeredimage emilie:
#     group base:
#         attribute casual default
#         attribute professional
#         attribute lingerie
#         attribute nude
#
#     group expression:
#         attribute neutral default
#         attribute cold
#         attribute smirk
#         attribute surprised
#         attribute blushing
#         attribute aroused
#         attribute surrendered

# ==============================================================================
# Sound Definitions
# ==============================================================================

# define audio.tension = "audio/music/tension.ogg"
# define audio.seduction = "audio/music/seduction.ogg"
# define audio.surrender = "audio/music/surrender.ogg"

# ==============================================================================
# Persistent Data
# ==============================================================================

default persistent.gallery_unlocked = set()
default persistent.achievements = set()
default persistent.total_playtime = 0

# ==============================================================================
# Configuration
# ==============================================================================

init python:
    # Quick menu settings
    config.quick_menu = True

    # Text speed
    preferences.text_cps = 50

    # Auto-forward time
    preferences.afm_time = 15
