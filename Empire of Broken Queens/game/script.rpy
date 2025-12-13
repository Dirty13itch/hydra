# Empire of Broken Queens - Main Script
# Entry point and title screen

# Game title screen
label splashscreen:
    scene black
    with fade

    show text "Empire of Broken Queens" at truecenter with dissolve
    pause 2.0
    hide text with dissolve

    return

# Main menu
label main_menu:
    return

# Game start
label start:

    # Player name input
    python:
        player_name = renpy.input("What is your name?", default="Marcus")
        player_name = player_name.strip() or "Marcus"

    "You are [player_name], a man with ambitions beyond mere wealth."

    "In this city of power and beauty, you've discovered something extraordinary..."

    "The most powerful, beautiful women in the world—executives, artists, moguls—"
    "each one holds a key to ultimate influence."

    "But to possess their power, you must first possess their hearts."
    "And then... their complete surrender."

    call prologue from _call_prologue

    return

# Prologue
label prologue:
    scene bg city_night with fade

    "The city never sleeps. Neither do your ambitions."

    "Tonight marks the beginning of everything."

    "At the exclusive Nordic Innovations gala, you'll meet her—"
    "Emilie Ekström. CEO. Ice Queen. Your first conquest."

    call emilie_introduction from _call_emilie_intro

    return

# Placeholder for Emilie's introduction
label emilie_introduction:
    scene bg corporate_gala with dissolve

    "The ballroom glitters with Sweden's elite."
    "And there, commanding attention without trying—"

    show emilie professional neutral at center with dissolve

    "Emilie Ekström. Nordic Ice, they call her behind her back."
    "You understand why immediately."

    "5'10\" of elegant Swedish perfection. Brown hair cascading in waves."
    "Eyes that could freeze or burn, depending on her mood."

    e "You're staring, Mr. [player_name]."

    menu:
        "I'm admiring, not staring. There's a difference.":
            $ add_corruption("emilie", 3)
            e smirk "Is there? Enlighten me."
            jump emilie_intro_admiring

        "Everyone is. You command the room.":
            $ add_corruption("emilie", 1)
            e neutral "Flattery. Predictable."
            jump emilie_intro_flattery

        "My apologies. Your reputation precedes you.":
            $ add_corruption("emilie", 5)
            e cold "Does it? And what does my reputation say?"
            jump emilie_intro_reputation

label emilie_intro_admiring:
    e "Most men who 'admire' me want something."
    e "What do you want, Mr. [player_name]?"

    "Her Swedish accent is subtle—years of international business."
    "But when she's intrigued, it slips through."

    jump emilie_intro_continue

label emilie_intro_flattery:
    e "I've heard that line a hundred times."
    e "Try harder."

    "She starts to turn away."

    mc "Wait. I have a proposal."

    e "You have thirty seconds."

    jump emilie_intro_continue

label emilie_intro_reputation:
    e cold "My reputation says I'm cold. Ruthless. Untouchable."

    mc "Your reputation says you're brilliant."
    mc "The cold is just... packaging."

    "Something flickers in her eyes. Interest."

    e neutral "That's the first interesting thing anyone's said to me tonight."

    jump emilie_intro_continue

label emilie_intro_continue:
    "And so it begins."

    "The first crack in the ice."

    "To be continued..."

    return
