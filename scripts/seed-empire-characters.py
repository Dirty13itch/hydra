#!/usr/bin/env python3
"""
Seed Empire of Broken Queens character data into Qdrant.

This script:
1. Loads character JSON files from data/empire/characters/
2. Creates text embeddings using Ollama (nomic-embed-text)
3. Stores character data in Qdrant empire_faces and empire_images collections

Usage:
    python scripts/seed-empire-characters.py
"""

import json
import uuid
from pathlib import Path
import httpx

# Configuration
OLLAMA_URL = "http://192.168.1.203:11434"
QDRANT_URL = "http://192.168.1.244:6333"
EMBEDDING_MODEL = "nomic-embed-text:latest"
CHARACTERS_DIR = Path(__file__).parent.parent / "data" / "empire" / "characters"


def get_embedding(text: str) -> list[float]:
    """Get embedding vector from Ollama."""
    response = httpx.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBEDDING_MODEL, "prompt": text},
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()["embedding"]


def create_character_description(char: dict) -> str:
    """Create a rich text description for embedding."""
    parts = [
        f"Character: {char['display_name']}",
        f"Role: {char.get('role', 'unknown')}",
        char.get('description', ''),
    ]

    appearance = char.get('appearance', {})
    if appearance:
        parts.append(f"Appearance: {appearance.get('hair_color', '')} hair, "
                    f"{appearance.get('eye_color', '')} eyes, "
                    f"{appearance.get('skin_tone', '')} skin")
        features = appearance.get('distinguishing_features', [])
        if features:
            parts.append(f"Features: {', '.join(features)}")

    traits = char.get('personality_traits', [])
    if traits:
        parts.append(f"Personality: {', '.join(traits)}")

    return "\n".join(parts)


def seed_character(char: dict, client: httpx.Client) -> None:
    """Seed a single character to Qdrant."""
    # Create embedding from character description
    description = create_character_description(char)
    embedding = get_embedding(description)

    # Pad/truncate to 768 dimensions for empire_images collection
    if len(embedding) < 768:
        embedding = embedding + [0.0] * (768 - len(embedding))
    elif len(embedding) > 768:
        embedding = embedding[:768]

    # Create point for Qdrant
    point = {
        "id": str(uuid.uuid4()),
        "vector": embedding,
        "payload": {
            "character_id": char["id"],
            "character_name": char["name"],
            "display_name": char["display_name"],
            "role": char.get("role", "unknown"),
            "description": char.get("description", ""),
            "appearance": char.get("appearance", {}),
            "wardrobe": char.get("wardrobe", {}),
            "personality_traits": char.get("personality_traits", []),
            "voice_profile": char.get("voice_profile", {}),
            "relationships": char.get("relationships", {}),
            "type": "character_profile"
        }
    }

    # Upsert to Qdrant
    response = client.put(
        f"{QDRANT_URL}/collections/empire_images/points",
        json={"points": [point]},
        timeout=30.0
    )

    if response.status_code in (200, 201):
        print(f"  Added: {char['display_name']}")
    else:
        print(f"  ERROR adding {char['display_name']}: {response.text}")


def main():
    print("Empire of Broken Queens - Character Seeder")
    print("=" * 50)

    # Find character files
    character_files = list(CHARACTERS_DIR.glob("*.json"))
    print(f"\nFound {len(character_files)} character files")

    if not character_files:
        print("No character files found in", CHARACTERS_DIR)
        return

    # Load and seed characters
    with httpx.Client() as client:
        for char_file in character_files:
            print(f"\nProcessing: {char_file.name}")
            try:
                with open(char_file) as f:
                    char = json.load(f)
                seed_character(char, client)
            except Exception as e:
                print(f"  ERROR: {e}")

    # Verify collection
    print("\n" + "=" * 50)
    print("Verifying Qdrant collection...")

    response = httpx.get(f"{QDRANT_URL}/collections/empire_images")
    if response.status_code == 200:
        data = response.json()
        points = data.get("result", {}).get("points_count", 0)
        print(f"empire_images collection: {points} points")

    print("\nSeeding complete!")


if __name__ == "__main__":
    main()
