# Hydra Documentation Package

This package contains the complete documentation system for the Hydra autonomous AI operating system.

## Installation

1. **Copy all files to your Hydra project directory:**
   ```
   C:\Users\shaun\projects\hydra\
   ```

2. **Merge with existing structure:**
   - Replace `CLAUDE.md` with the new version
   - Add new files alongside existing `knowledge/` folder
   - Keep your existing `knowledge/*.md` files

3. **Final structure should be:**
   ```
   C:\Users\shaun\projects\hydra\
   ├── CLAUDE.md              ← NEW (replace existing)
   ├── VISION.md              ← NEW
   ├── ARCHITECTURE.md        ← NEW
   ├── ROADMAP.md             ← NEW
   ├── STATE.json             ← NEW
   ├── LEARNINGS.md           ← NEW
   ├── HYDRA-MASTER-SYNTHESIS.md    (existing)
   ├── HYDRA-SETUP-GUIDE.md         (existing)
   └── knowledge/                    (existing)
       ├── infrastructure.md
       ├── inference-stack.md
       └── ... etc
   ```

## How It Works

1. **Start Claude Code:**
   ```bash
   cd C:\Users\shaun\projects\hydra
   claude --dangerously-skip-permissions
   ```

2. **Claude Code automatically:**
   - Reads CLAUDE.md (bootstrap instructions)
   - Loads STATE.json (current state)
   - Checks ROADMAP.md (what to work on)
   - Runs health check
   - Reports status and suggests priorities

3. **After each session:**
   - Claude Code updates STATE.json
   - Adds learnings to LEARNINGS.md
   - Marks completed tasks in ROADMAP.md

## Files Overview

| File | Purpose | Update Frequency |
|------|---------|------------------|
| CLAUDE.md | Bootstrap instructions | Rarely |
| VISION.md | North star, principles | Rarely |
| ARCHITECTURE.md | Technical blueprint | When architecture changes |
| ROADMAP.md | Implementation plan | When completing milestones |
| STATE.json | Current state | Every session |
| LEARNINGS.md | Accumulated wisdom | When discovering patterns |

## Self-Improvement Loop

This system is designed to improve over time:

1. **STATE.json** keeps track of what's running, what's broken, what's next
2. **LEARNINGS.md** captures insights so mistakes aren't repeated
3. **ROADMAP.md** ensures work advances toward the vision
4. **Claude Code updates these files** as it works

The more you use it, the smarter it gets.
