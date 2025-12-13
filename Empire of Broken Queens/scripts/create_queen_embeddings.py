#!/usr/bin/env python3
"""
Create face embeddings for queens and upload to Qdrant.
Run this on hydra-compute where InsightFace is installed.
"""

import os
import cv2
import numpy as np
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# Config
QDRANT_URL = "http://192.168.1.244:6333"
REFERENCE_DIR = "/home/typhon/comfyui/input/references"
COLLECTION_NAME = "empire_faces"
EMBEDDING_DIM = 512  # ArcFace embedding dimension

# Queen slug to reference folder mapping
QUEEN_MAPPINGS = {
    "emilie": ["emilie", "emilie_ekstrom"],
    "jordan": ["jordan", "jordan_night"],
    "nikki": ["nikki", "nikki_benz"],
    "puma": ["puma", "puma_swede"],
    "nicolette": ["nicolette", "nicolette_shea"],
    "alanah": ["alanah", "alanah_rae"],
    "madison": ["madison", "madison_ivy"],
    "savannah": ["savannah", "savannah_bond"],
    "esperanza": ["esperanza"],
    "trina": ["trina", "trina_michaels"],
    "brooklyn": ["brooklyn"],
    "ava": ["ava"],
    "shyla": ["shyla", "shyla_stylez"],
}

def setup_insightface():
    """Initialize InsightFace app"""
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        app.prepare(ctx_id=0)
        return app
    except Exception as e:
        print(f"Error initializing InsightFace: {e}")
        print("Install with: pip install insightface onnxruntime-gpu")
        return None

def get_face_embedding(face_app, image_path):
    """Extract face embedding from an image"""
    img = cv2.imread(str(image_path))
    if img is None:
        return None

    faces = face_app.get(img)
    if not faces:
        return None

    # Get largest face
    face = max(faces, key=lambda x: x.bbox[2] * x.bbox[3])
    return face.embedding

def get_reference_images(queen_slug):
    """Get all reference images for a queen"""
    images = []
    folders = QUEEN_MAPPINGS.get(queen_slug, [queen_slug])

    for folder in folders:
        folder_path = Path(REFERENCE_DIR) / folder
        if folder_path.exists():
            for img_file in folder_path.glob("*"):
                if img_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                    images.append(img_file)

    return images

def create_queen_embedding(face_app, queen_slug):
    """Create averaged embedding from multiple reference images"""
    images = get_reference_images(queen_slug)
    if not images:
        print(f"  No reference images found for {queen_slug}")
        return None

    embeddings = []
    for img_path in images[:10]:  # Use up to 10 images
        embedding = get_face_embedding(face_app, img_path)
        if embedding is not None:
            embeddings.append(embedding)
            print(f"    Processed: {img_path.name}")

    if not embeddings:
        print(f"  No faces detected in any images for {queen_slug}")
        return None

    # Average all embeddings
    avg_embedding = np.mean(embeddings, axis=0)
    # Normalize
    avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)

    print(f"  Created embedding from {len(embeddings)} images")
    return avg_embedding

def upload_to_qdrant(client, embeddings_data):
    """Upload embeddings to Qdrant"""
    # Create collection if it doesn't exist
    try:
        client.get_collection(COLLECTION_NAME)
        print(f"Collection {COLLECTION_NAME} exists")
    except:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE)
        )
        print(f"Created collection {COLLECTION_NAME}")

    # Upload points
    points = []
    for i, (queen_slug, embedding) in enumerate(embeddings_data.items()):
        points.append(PointStruct(
            id=i + 1,
            vector=embedding.tolist(),
            payload={
                "queen_slug": queen_slug,
                "type": "reference_embedding"
            }
        ))

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Uploaded {len(points)} embeddings to Qdrant")

def main():
    print("=== Empire of Broken Queens - Face Embedding Creation ===\n")

    # Initialize
    print("Initializing InsightFace...")
    face_app = setup_insightface()
    if not face_app:
        return

    print("Connecting to Qdrant...")
    client = QdrantClient(url=QDRANT_URL)

    # Create embeddings for each queen
    embeddings = {}
    for queen_slug in QUEEN_MAPPINGS.keys():
        print(f"\nProcessing {queen_slug}...")
        embedding = create_queen_embedding(face_app, queen_slug)
        if embedding is not None:
            embeddings[queen_slug] = embedding

    # Upload to Qdrant
    if embeddings:
        print(f"\nUploading {len(embeddings)} embeddings to Qdrant...")
        upload_to_qdrant(client, embeddings)
        print("\nDone!")
    else:
        print("\nNo embeddings created!")

if __name__ == "__main__":
    main()
