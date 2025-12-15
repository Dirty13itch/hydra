# Phase 12: Character Consistency System

**Status:** IN PROGRESS
**Project:** Empire of Broken Queens visual novel asset pipeline

## Overview

Character consistency system for generating visual novel assets with consistent character appearances and voices.

## Components

### Character Management (`character_consistency.py`)

- CharacterManager for loading/querying character profiles
- ScriptParser for extracting dialogue with emotions
- Stores character embeddings in Qdrant (empire_faces, empire_images)

### Image Generation (`comfyui_client.py`)

- Submits workflows to ComfyUI API
- Tracks generation progress
- Downloads completed images

### Voice Synthesis (`tts_synthesis.py`)

- VoiceProfileManager for character voice mapping
- TTSSynthesizer for dialogue audio generation
- Emotion modifiers (speed, pitch adjustments)

## Configuration Files

### Workflow Templates

Located in `config/comfyui/workflows/`:
- `character_portrait_template.json` - Character portraits with style control
- `background_template.json` - Scene backgrounds for visual novel

### Voice Profiles

Located in `config/kokoro/empire_voice_profiles.json`:

| Character | Voice |
|-----------|-------|
| seraphina | af_bella |
| mira | af_sarah |
| lysander | am_michael |

## n8n Workflows

- **Empire Chapter Processor** - Parses script, generates TTS + images
- **Letta Memory Update** - Stores character interactions

## Integration Points

| Service | Endpoint | Purpose |
|---------|----------|---------|
| ComfyUI | http://192.168.1.203:8188 | Image generation |
| Kokoro TTS | http://192.168.1.244:8880 | Voice synthesis |
| Qdrant | http://192.168.1.244:6333 | Character embeddings |
