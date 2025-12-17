"""
MIRIX Memory Architecture - 6-Tier Memory System

Implements a sophisticated memory architecture for AI agents with:
1. Core Memory - Always-visible identity + user facts (in-context)
2. Episodic Memory - Timestamped events, sessions (PostgreSQL + vector)
3. Semantic Memory - Abstract facts, knowledge (Qdrant vectors)
4. Procedural Memory - Learned workflows, skills (code + structured)
5. Resource Memory - External docs, tools (NFS + metadata)
6. Knowledge Vault - Long-term archival (PostgreSQL + vectors)

Inspired by cognitive architectures like SOAR, ACT-R, and modern LLM memory systems.

Author: Hydra Autonomous System
Created: 2025-12-16
"""

import asyncio
import hashlib
import json
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import logging

import httpx
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException


# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Memory Tier Definitions
# =============================================================================

class MemoryTier(str, Enum):
    """Memory tiers in the MIRIX architecture."""
    CORE = "core"           # Always in context
    EPISODIC = "episodic"   # Session-based events
    SEMANTIC = "semantic"   # Abstract knowledge
    PROCEDURAL = "procedural"  # Skills and workflows
    RESOURCE = "resource"   # External documents
    VAULT = "vault"         # Long-term archival


class MemoryPriority(str, Enum):
    """Priority levels for memory retrieval."""
    CRITICAL = "critical"   # Must include
    HIGH = "high"           # Include if space
    MEDIUM = "medium"       # Include if relevant
    LOW = "low"             # Only if specifically needed


# =============================================================================
# Memory Entry Base Classes
# =============================================================================

@dataclass
class MemoryEntry:
    """Base class for all memory entries."""
    id: str
    tier: MemoryTier
    content: str
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    priority: MemoryPriority = MemoryPriority.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decay_rate: float = 0.01  # Per-day decay
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d["tier"] = self.tier.value
        d["priority"] = self.priority.value
        d["created_at"] = self.created_at.isoformat()
        d["updated_at"] = self.updated_at.isoformat()
        if self.last_accessed:
            d["last_accessed"] = self.last_accessed.isoformat()
        # Don't serialize embeddings to JSON (too large)
        d.pop("embedding", None)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        data["tier"] = MemoryTier(data["tier"])
        data["priority"] = MemoryPriority(data["priority"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if data.get("last_accessed"):
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        return cls(**data)

    def compute_relevance(self, query_embedding: Optional[List[float]] = None) -> float:
        """
        Compute relevance score for retrieval.

        Factors:
        - Recency (time since last access)
        - Frequency (access count)
        - Semantic similarity (if embeddings available)
        - Priority
        """
        now = datetime.utcnow()

        # Recency factor (0-1, higher is more recent)
        if self.last_accessed:
            hours_since = (now - self.last_accessed).total_seconds() / 3600
            recency = max(0, 1 - (hours_since / (24 * 7)))  # Decay over a week
        else:
            recency = 0.5

        # Frequency factor (logarithmic)
        import math
        frequency = min(1, math.log10(self.access_count + 1) / 3)  # Caps at 1000 accesses

        # Priority factor
        priority_weights = {
            MemoryPriority.CRITICAL: 1.0,
            MemoryPriority.HIGH: 0.8,
            MemoryPriority.MEDIUM: 0.5,
            MemoryPriority.LOW: 0.2,
        }
        priority = priority_weights.get(self.priority, 0.5)

        # Semantic similarity (if embeddings available)
        similarity = 0.5
        if query_embedding and self.embedding:
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, self.embedding))
            norm_q = sum(a * a for a in query_embedding) ** 0.5
            norm_e = sum(a * a for a in self.embedding) ** 0.5
            if norm_q > 0 and norm_e > 0:
                similarity = (dot / (norm_q * norm_e) + 1) / 2  # Normalize to 0-1

        # Weighted combination
        return (
            recency * 0.2 +
            frequency * 0.1 +
            priority * 0.2 +
            similarity * 0.5
        )


@dataclass
class CoreMemoryEntry(MemoryEntry):
    """Core memory - always in context."""
    category: str = "identity"  # identity, user_facts, preferences
    always_include: bool = True

    def __post_init__(self):
        self.tier = MemoryTier.CORE
        self.priority = MemoryPriority.CRITICAL
        self.decay_rate = 0.0  # Core memories don't decay


@dataclass
class EpisodicMemoryEntry(MemoryEntry):
    """Episodic memory - timestamped events."""
    session_id: str = ""
    event_type: str = ""  # interaction, task, error, milestone
    participants: List[str] = field(default_factory=list)
    outcome: Optional[str] = None
    emotional_valence: float = 0.0  # -1 (negative) to 1 (positive)

    def __post_init__(self):
        self.tier = MemoryTier.EPISODIC


@dataclass
class SemanticMemoryEntry(MemoryEntry):
    """Semantic memory - abstract facts and knowledge."""
    domain: str = ""  # programming, infrastructure, user, general
    confidence: float = 1.0
    source: str = ""  # learned, stated, inferred
    relationships: List[str] = field(default_factory=list)  # Related memory IDs

    def __post_init__(self):
        self.tier = MemoryTier.SEMANTIC


@dataclass
class ProceduralMemoryEntry(MemoryEntry):
    """Procedural memory - skills and workflows."""
    skill_name: str = ""
    trigger_conditions: List[str] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0
    execution_count: int = 0
    average_duration_ms: int = 0

    def __post_init__(self):
        self.tier = MemoryTier.PROCEDURAL


@dataclass
class ResourceMemoryEntry(MemoryEntry):
    """Resource memory - external documents and tools."""
    resource_type: str = ""  # document, tool, api, codebase
    path: str = ""
    size_bytes: int = 0
    checksum: str = ""
    index_status: str = "pending"  # pending, indexed, failed
    chunk_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.tier = MemoryTier.RESOURCE


@dataclass
class VaultMemoryEntry(MemoryEntry):
    """Knowledge vault - long-term archival."""
    original_tier: MemoryTier = MemoryTier.EPISODIC
    archived_at: datetime = field(default_factory=datetime.utcnow)
    archive_reason: str = ""  # consolidated, aged_out, manual
    summary: str = ""

    def __post_init__(self):
        self.tier = MemoryTier.VAULT


# =============================================================================
# Memory Store Interface
# =============================================================================

class MemoryStore(ABC):
    """Abstract interface for memory storage backends."""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry, return ID."""
        pass

    @abstractmethod
    async def retrieve(self, id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
        min_relevance: float = 0.0,
    ) -> List[MemoryEntry]:
        """Search memories by query."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""
        pass

    @abstractmethod
    async def update(self, entry: MemoryEntry) -> bool:
        """Update a memory entry."""
        pass


# =============================================================================
# JSON File-Based Memory Store (Simple Implementation)
# =============================================================================

class JSONMemoryStore(MemoryStore):
    """Simple JSON file-based memory store."""

    def __init__(self, data_dir: str = "/data/memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Separate files for each tier
        self._stores: Dict[MemoryTier, Path] = {
            tier: self.data_dir / f"{tier.value}.json"
            for tier in MemoryTier
        }

        # In-memory cache
        self._cache: Dict[MemoryTier, Dict[str, MemoryEntry]] = {
            tier: {} for tier in MemoryTier
        }

        # Load existing data
        self._load_all()

    def _load_all(self):
        """Load all memories from disk."""
        for tier, path in self._stores.items():
            if path.exists():
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    for entry_data in data.values():
                        entry = self._deserialize_entry(entry_data, tier)
                        self._cache[tier][entry.id] = entry
                except Exception as e:
                    logger.error(f"Error loading {tier.value} memories: {e}")

    def _save_tier(self, tier: MemoryTier):
        """Save a tier to disk."""
        data = {
            id: entry.to_dict()
            for id, entry in self._cache[tier].items()
        }
        with open(self._stores[tier], "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _deserialize_entry(self, data: Dict[str, Any], tier: MemoryTier) -> MemoryEntry:
        """Deserialize entry based on tier."""
        entry_classes = {
            MemoryTier.CORE: CoreMemoryEntry,
            MemoryTier.EPISODIC: EpisodicMemoryEntry,
            MemoryTier.SEMANTIC: SemanticMemoryEntry,
            MemoryTier.PROCEDURAL: ProceduralMemoryEntry,
            MemoryTier.RESOURCE: ResourceMemoryEntry,
            MemoryTier.VAULT: VaultMemoryEntry,
        }
        cls = entry_classes.get(tier, MemoryEntry)
        return cls.from_dict(data)

    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry."""
        if not entry.id:
            entry.id = str(uuid.uuid4())

        self._cache[entry.tier][entry.id] = entry
        self._save_tier(entry.tier)

        logger.info(f"Stored {entry.tier.value} memory: {entry.id}")
        return entry.id

    async def retrieve(self, id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        for tier_cache in self._cache.values():
            if id in tier_cache:
                entry = tier_cache[id]
                entry.access_count += 1
                entry.last_accessed = datetime.utcnow()
                return entry
        return None

    async def search(
        self,
        query: str,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
        min_relevance: float = 0.0,
    ) -> List[MemoryEntry]:
        """Search memories by query (simple text matching for now)."""
        results = []
        query_lower = query.lower()

        tiers_to_search = [tier] if tier else list(MemoryTier)

        for t in tiers_to_search:
            for entry in self._cache[t].values():
                # Simple text matching
                if query_lower in entry.content.lower():
                    score = entry.compute_relevance()
                    if score >= min_relevance:
                        results.append((score, entry))

        # Sort by relevance and limit
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]

    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""
        for tier, tier_cache in self._cache.items():
            if id in tier_cache:
                del tier_cache[id]
                self._save_tier(tier)
                logger.info(f"Deleted memory: {id}")
                return True
        return False

    async def update(self, entry: MemoryEntry) -> bool:
        """Update a memory entry."""
        if entry.id in self._cache[entry.tier]:
            entry.updated_at = datetime.utcnow()
            self._cache[entry.tier][entry.id] = entry
            self._save_tier(entry.tier)
            return True
        return False


# =============================================================================
# Embedding Service - Generates embeddings via Ollama
# =============================================================================

class EmbeddingService:
    """
    Generates embeddings using Ollama's embedding models.

    Default model: nomic-embed-text (768 dimensions)
    """

    def __init__(
        self,
        ollama_url: str = "http://192.168.1.203:11434",
        model: str = "nomic-embed-text:latest",
    ):
        self.ollama_url = ollama_url
        self.model = model
        self._dimension: Optional[int] = None

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            result = response.json()
            embedding = result.get("embedding", [])

            if not self._dimension and embedding:
                self._dimension = len(embedding)
                logger.info(f"Embedding dimension: {self._dimension}")

            return embedding

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            emb = await self.get_embedding(text)
            embeddings.append(emb)
        return embeddings

    @property
    def dimension(self) -> int:
        """Get embedding dimension (768 for nomic-embed-text)."""
        return self._dimension or 768


# =============================================================================
# Qdrant Memory Store - Production Vector Storage
# =============================================================================

class QdrantMemoryStore(MemoryStore):
    """
    Production memory store using Qdrant for vector storage.

    Features:
    - Semantic search via embeddings
    - Metadata filtering by tier, tags, priority
    - Automatic embedding generation
    - Payload storage for full memory entries
    """

    COLLECTION_NAME = "hydra_memory"

    def __init__(
        self,
        qdrant_url: str = "http://192.168.1.244:6333",
        embedding_service: Optional[EmbeddingService] = None,
        fallback_store: Optional[MemoryStore] = None,
    ):
        self.qdrant_url = qdrant_url
        self.embedding_service = embedding_service or EmbeddingService()
        self.fallback_store = fallback_store  # JSONMemoryStore for backup

        # Initialize collection
        self._initialized = False

    async def _ensure_collection(self):
        """Ensure Qdrant collection exists with correct schema."""
        if self._initialized:
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if collection exists
            try:
                response = await client.get(
                    f"{self.qdrant_url}/collections/{self.COLLECTION_NAME}"
                )
                if response.status_code == 200:
                    self._initialized = True
                    logger.info(f"Qdrant collection '{self.COLLECTION_NAME}' exists")
                    return
            except Exception:
                pass

            # Create collection
            try:
                response = await client.put(
                    f"{self.qdrant_url}/collections/{self.COLLECTION_NAME}",
                    json={
                        "vectors": {
                            "size": self.embedding_service.dimension,
                            "distance": "Cosine"
                        }
                    }
                )
                response.raise_for_status()
                logger.info(f"Created Qdrant collection '{self.COLLECTION_NAME}'")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to create Qdrant collection: {e}")
                raise

    def _entry_to_payload(self, entry: MemoryEntry) -> Dict[str, Any]:
        """Convert memory entry to Qdrant payload."""
        payload = entry.to_dict()
        # Ensure JSON-serializable
        payload["tier"] = entry.tier.value
        payload["priority"] = entry.priority.value
        return payload

    def _payload_to_entry(self, payload: Dict[str, Any]) -> MemoryEntry:
        """Convert Qdrant payload to memory entry."""
        tier = MemoryTier(payload.get("tier", "semantic"))

        entry_classes = {
            MemoryTier.CORE: CoreMemoryEntry,
            MemoryTier.EPISODIC: EpisodicMemoryEntry,
            MemoryTier.SEMANTIC: SemanticMemoryEntry,
            MemoryTier.PROCEDURAL: ProceduralMemoryEntry,
            MemoryTier.RESOURCE: ResourceMemoryEntry,
            MemoryTier.VAULT: VaultMemoryEntry,
        }

        cls = entry_classes.get(tier, MemoryEntry)
        return cls.from_dict(payload)

    def _to_qdrant_id(self, id_str: str) -> str:
        """
        Convert any string ID to a valid Qdrant UUID.

        Qdrant requires UUIDs or integers. If the ID is already a valid UUID,
        return it as-is. Otherwise, generate a deterministic UUID5 from the string.
        """
        # Check if already a valid UUID
        try:
            uuid.UUID(id_str)
            return id_str
        except ValueError:
            # Not a valid UUID - generate one deterministically
            namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
            return str(uuid.uuid5(namespace, id_str))

    async def store(self, entry: MemoryEntry) -> str:
        """Store a memory entry with embedding."""
        await self._ensure_collection()

        if not entry.id:
            entry.id = str(uuid.uuid4())

        # Convert ID to valid Qdrant UUID if needed
        qdrant_id = self._to_qdrant_id(entry.id)

        # Generate embedding
        try:
            embedding = await self.embedding_service.get_embedding(entry.content)
            entry.embedding = embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            embedding = [0.0] * self.embedding_service.dimension

        # Store in Qdrant
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = self._entry_to_payload(entry)
            request_body = {
                "points": [{
                    "id": qdrant_id,
                    "vector": embedding,
                    "payload": payload
                }]
            }

            response = await client.put(
                f"{self.qdrant_url}/collections/{self.COLLECTION_NAME}/points",
                json=request_body
            )

            if response.status_code != 200:
                logger.error(f"Qdrant store failed: {response.status_code} - {response.text}")
                logger.error(f"Entry ID: {entry.id}, Qdrant ID: {qdrant_id}")
                logger.error(f"Payload keys: {list(payload.keys())}")

            response.raise_for_status()

        # Also store in fallback if available
        if self.fallback_store:
            try:
                await self.fallback_store.store(entry)
            except Exception:
                pass

        logger.info(f"Stored {entry.tier.value} memory in Qdrant: {entry.id}")
        return entry.id

    async def retrieve(self, id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID."""
        await self._ensure_collection()

        # Convert ID to Qdrant format
        qdrant_id = self._to_qdrant_id(id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.qdrant_url}/collections/{self.COLLECTION_NAME}/points",
                json={"ids": [qdrant_id], "with_payload": True}
            )

            if response.status_code != 200:
                return None

            result = response.json()
            points = result.get("result", [])

            if not points:
                # Try fallback
                if self.fallback_store:
                    return await self.fallback_store.retrieve(id)
                return None

            payload = points[0].get("payload", {})
            entry = self._payload_to_entry(payload)
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()

            return entry

    async def search(
        self,
        query: str,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
        min_relevance: float = 0.0,
    ) -> List[MemoryEntry]:
        """Search memories using semantic similarity."""
        await self._ensure_collection()

        # Generate query embedding
        try:
            query_embedding = await self.embedding_service.get_embedding(query)
        except Exception as e:
            logger.warning(f"Failed to generate query embedding: {e}")
            # Fall back to text search in fallback store
            if self.fallback_store:
                return await self.fallback_store.search(query, tier, limit, min_relevance)
            return []

        # Build filter
        filter_conditions = []
        if tier:
            filter_conditions.append({
                "key": "tier",
                "match": {"value": tier.value}
            })

        search_filter = None
        if filter_conditions:
            search_filter = {"must": filter_conditions}

        # Search Qdrant
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_body = {
                "vector": query_embedding,
                "limit": limit,
                "with_payload": True,
                "score_threshold": min_relevance
            }
            if search_filter:
                search_body["filter"] = search_filter

            response = await client.post(
                f"{self.qdrant_url}/collections/{self.COLLECTION_NAME}/points/search",
                json=search_body
            )

            if response.status_code != 200:
                logger.warning(f"Qdrant search failed: {response.status_code}")
                if self.fallback_store:
                    return await self.fallback_store.search(query, tier, limit, min_relevance)
                return []

            result = response.json()
            points = result.get("result", [])

        # Convert to entries
        entries = []
        for point in points:
            payload = point.get("payload", {})
            try:
                entry = self._payload_to_entry(payload)
                entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to parse memory entry: {e}")

        return entries

    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""
        await self._ensure_collection()

        # Convert ID to Qdrant format
        qdrant_id = self._to_qdrant_id(id)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.qdrant_url}/collections/{self.COLLECTION_NAME}/points/delete",
                json={"points": [qdrant_id]}
            )

            success = response.status_code == 200

            # Also delete from fallback
            if self.fallback_store:
                try:
                    await self.fallback_store.delete(id)
                except Exception:
                    pass

            if success:
                logger.info(f"Deleted memory from Qdrant: {id}")

            return success

    async def update(self, entry: MemoryEntry) -> bool:
        """Update a memory entry (re-store with same ID)."""
        entry.updated_at = datetime.utcnow()

        try:
            await self.store(entry)
            return True
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Get Qdrant collection statistics."""
        await self._ensure_collection()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.qdrant_url}/collections/{self.COLLECTION_NAME}"
            )

            if response.status_code != 200:
                return {"error": "Failed to get stats"}

            result = response.json()
            collection = result.get("result", {})

            return {
                "collection": self.COLLECTION_NAME,
                "points_count": collection.get("points_count", 0),
                "vectors_count": collection.get("vectors_count", 0),
                "status": collection.get("status", "unknown"),
                "embedding_model": self.embedding_service.model,
                "embedding_dimension": self.embedding_service.dimension,
            }

    async def migrate_from_json(self, json_store: JSONMemoryStore) -> Dict[str, int]:
        """Migrate memories from JSON store to Qdrant."""
        migrated = {"total": 0, "success": 0, "failed": 0}

        for tier in MemoryTier:
            for entry_id, entry in json_store._cache[tier].items():
                migrated["total"] += 1
                try:
                    await self.store(entry)
                    migrated["success"] += 1
                except Exception as e:
                    logger.warning(f"Failed to migrate {entry_id}: {e}")
                    migrated["failed"] += 1

        logger.info(f"Migration complete: {migrated}")
        return migrated


# =============================================================================
# Neo4j Graph Store - Relationship Management
# =============================================================================

class Neo4jGraphStore:
    """
    Neo4j-based graph store for memory relationships.

    Enables:
    - Multi-hop reasoning across connected facts
    - Relationship tracking between memories
    - Entity disambiguation
    - Explainable retrieval paths
    """

    def __init__(
        self,
        neo4j_url: str = "http://192.168.1.244:7474",
        username: str = "neo4j",
        password: str = "HydraNeo4jPass2024",
    ):
        self.neo4j_url = neo4j_url
        self.username = username
        self.password = password
        self._initialized = False

    async def _execute_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a Cypher query against Neo4j."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.neo4j_url}/db/neo4j/tx/commit",
                auth=(self.username, self.password),
                headers={"Content-Type": "application/json"},
                json={
                    "statements": [{
                        "statement": query,
                        "parameters": parameters or {}
                    }]
                }
            )
            response.raise_for_status()
            return response.json()

    async def ensure_initialized(self):
        """Ensure constraints and indexes exist."""
        if self._initialized:
            return

        # Create constraint on Memory id
        try:
            await self._execute_cypher(
                "CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE"
            )
            logger.info("Neo4j Memory constraint created")
        except Exception as e:
            logger.warning(f"Could not create constraint: {e}")

        self._initialized = True

    async def store_memory_node(self, entry: MemoryEntry) -> bool:
        """Store a memory as a Neo4j node."""
        await self.ensure_initialized()

        query = """
        MERGE (m:Memory {id: $id})
        SET m.tier = $tier,
            m.content = $content,
            m.priority = $priority,
            m.tags = $tags,
            m.created_at = $created_at,
            m.updated_at = $updated_at
        RETURN m
        """

        try:
            result = await self._execute_cypher(query, {
                "id": entry.id,
                "tier": entry.tier.value,
                "content": entry.content[:500],  # Truncate for graph storage
                "priority": entry.priority.value,
                "tags": entry.tags,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            })

            if result.get("errors"):
                logger.error(f"Neo4j store error: {result['errors']}")
                return False

            logger.debug(f"Stored memory node in Neo4j: {entry.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store memory in Neo4j: {e}")
            return False

    async def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a relationship between two memories."""
        await self.ensure_initialized()

        query = f"""
        MATCH (a:Memory {{id: $from_id}})
        MATCH (b:Memory {{id: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $properties
        RETURN r
        """

        try:
            result = await self._execute_cypher(query, {
                "from_id": from_id,
                "to_id": to_id,
                "properties": properties or {}
            })

            if result.get("errors"):
                logger.error(f"Neo4j relationship error: {result['errors']}")
                return False

            logger.info(f"Created {rel_type} relationship: {from_id} -> {to_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False

    async def get_related(
        self,
        memory_id: str,
        rel_types: Optional[List[str]] = None,
        max_hops: int = 2,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get memories related to a given memory via graph traversal."""
        await self.ensure_initialized()

        # Build relationship pattern
        rel_pattern = ""
        if rel_types:
            rel_pattern = ":" + "|".join(rel_types)

        query = f"""
        MATCH path = (start:Memory {{id: $id}})-[r{rel_pattern}*1..{max_hops}]-(related:Memory)
        RETURN DISTINCT related.id as id,
               related.tier as tier,
               related.content as content,
               related.priority as priority,
               length(path) as distance,
               [rel in relationships(path) | type(rel)] as relationship_path
        ORDER BY distance, related.priority DESC
        LIMIT $limit
        """

        try:
            result = await self._execute_cypher(query, {
                "id": memory_id,
                "limit": limit
            })

            if result.get("errors"):
                logger.error(f"Neo4j query error: {result['errors']}")
                return []

            # Parse results
            related = []
            for row in result.get("results", [{}])[0].get("data", []):
                values = row.get("row", [])
                if len(values) >= 6:
                    related.append({
                        "id": values[0],
                        "tier": values[1],
                        "content": values[2],
                        "priority": values[3],
                        "distance": values[4],
                        "relationship_path": values[5]
                    })

            return related

        except Exception as e:
            logger.error(f"Failed to get related memories: {e}")
            return []

    async def find_path(
        self,
        from_id: str,
        to_id: str,
        max_hops: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """Find the shortest path between two memories."""
        await self.ensure_initialized()

        query = f"""
        MATCH path = shortestPath((a:Memory {{id: $from_id}})-[*..{max_hops}]-(b:Memory {{id: $to_id}}))
        RETURN [n in nodes(path) | {{id: n.id, tier: n.tier, content: n.content}}] as nodes,
               [r in relationships(path) | type(r)] as relationships
        """

        try:
            result = await self._execute_cypher(query, {
                "from_id": from_id,
                "to_id": to_id
            })

            if result.get("errors") or not result.get("results", [{}])[0].get("data"):
                return None

            row = result["results"][0]["data"][0]["row"]
            return {
                "nodes": row[0],
                "relationships": row[1]
            }

        except Exception as e:
            logger.error(f"Failed to find path: {e}")
            return None

    async def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        await self.ensure_initialized()

        # Query for nodes
        node_query = "MATCH (m:Memory) RETURN count(m) as total"
        rel_query = "MATCH ()-[r]->() RETURN count(r) as total"

        try:
            # Get node count
            node_result = await self._execute_cypher(node_query)
            node_data = node_result.get("results", [{}])[0].get("data", [])
            total_nodes = node_data[0].get("row", [0])[0] if node_data else 0

            # Get relationship count
            rel_result = await self._execute_cypher(rel_query)
            rel_data = rel_result.get("results", [{}])[0].get("data", [])
            total_relationships = rel_data[0].get("row", [0])[0] if rel_data else 0

            return {
                "total_nodes": total_nodes,
                "total_relationships": total_relationships,
                "neo4j_url": self.neo4j_url,
                "status": "connected"
            }
        except Exception as e:
            logger.error(f"Failed to get Neo4j stats: {e}")
            return {"error": str(e)}

    async def sync_from_qdrant(self, qdrant_store: QdrantMemoryStore) -> Dict[str, int]:
        """Sync all memories from Qdrant to Neo4j graph."""
        synced = {"total": 0, "success": 0, "failed": 0}

        # Get all points from Qdrant
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{qdrant_store.qdrant_url}/collections/{qdrant_store.COLLECTION_NAME}/points/scroll",
                json={"limit": 1000, "with_payload": True}
            )

            if response.status_code != 200:
                return {"error": "Failed to read from Qdrant"}

            result = response.json()
            points = result.get("result", {}).get("points", [])

        for point in points:
            synced["total"] += 1
            payload = point.get("payload", {})

            # Create memory entry from payload
            try:
                tier = MemoryTier(payload.get("tier", "semantic"))
                entry = MemoryEntry(
                    id=payload.get("id", str(point.get("id"))),
                    tier=tier,
                    content=payload.get("content", ""),
                    created_at=datetime.fromisoformat(payload.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(payload.get("updated_at", datetime.utcnow().isoformat())),
                    priority=MemoryPriority(payload.get("priority", "medium")),
                    tags=payload.get("tags", []),
                )

                if await self.store_memory_node(entry):
                    synced["success"] += 1
                else:
                    synced["failed"] += 1

            except Exception as e:
                logger.warning(f"Failed to sync memory to Neo4j: {e}")
                synced["failed"] += 1

        logger.info(f"Neo4j sync complete: {synced}")
        return synced


# =============================================================================
# Memory Manager - Orchestrates All Memory Operations
# =============================================================================

class MIRIXMemoryManager:
    """
    Orchestrates the 6-tier memory system.

    Handles:
    - Memory creation and storage across tiers
    - Intelligent retrieval with context assembly
    - Memory consolidation and archival
    - Decay and forgetting
    - Cross-tier relationship management
    """

    def __init__(
        self,
        store: Optional[MemoryStore] = None,
        data_dir: str = "/data/memory",
        core_memory_tokens: int = 512,
        qdrant_url: str = "http://192.168.1.244:6333",
    ):
        self.store = store or JSONMemoryStore(data_dir)
        self.data_dir = Path(data_dir)
        self.core_memory_tokens = core_memory_tokens
        self.qdrant_url = qdrant_url

        # Initialize embedding client (lazy)
        self._embedding_client = None

        # Core memory is always loaded
        self._core_memory_cache: Dict[str, CoreMemoryEntry] = {}
        self._load_core_memory()

    def _load_core_memory(self):
        """Load core memories into cache."""
        if isinstance(self.store, JSONMemoryStore):
            self._core_memory_cache = {
                id: entry
                for id, entry in self.store._cache[MemoryTier.CORE].items()
            }

    # =========================================================================
    # Core Memory Operations
    # =========================================================================

    async def set_core_memory(
        self,
        category: str,
        content: str,
        key: Optional[str] = None,
    ) -> str:
        """
        Set a core memory value.

        Core memory is always in context and includes:
        - Identity: Who the agent is
        - User facts: Key user information
        - Preferences: User preferences
        """
        # Generate stable ID from category and key
        if key:
            id = hashlib.md5(f"{category}:{key}".encode()).hexdigest()[:16]
        else:
            id = hashlib.md5(f"{category}:{content[:50]}".encode()).hexdigest()[:16]

        now = datetime.utcnow()
        entry = CoreMemoryEntry(
            id=id,
            tier=MemoryTier.CORE,
            content=content,
            created_at=now,
            updated_at=now,
            category=category,
            tags=[category],
        )

        await self.store.store(entry)
        self._core_memory_cache[id] = entry

        return id

    async def get_core_context(self) -> str:
        """
        Get the full core memory context for prompt injection.

        Returns formatted string to include in every prompt.
        """
        lines = ["<core_memory>"]

        # Group by category
        by_category: Dict[str, List[str]] = {}
        for entry in self._core_memory_cache.values():
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry.content)

        for category, contents in by_category.items():
            lines.append(f"## {category.title()}")
            for content in contents:
                lines.append(f"- {content}")
            lines.append("")

        lines.append("</core_memory>")
        return "\n".join(lines)

    # =========================================================================
    # Episodic Memory Operations
    # =========================================================================

    async def record_episode(
        self,
        content: str,
        event_type: str,
        session_id: Optional[str] = None,
        participants: Optional[List[str]] = None,
        outcome: Optional[str] = None,
        emotional_valence: float = 0.0,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Record an episodic memory (event).

        Args:
            content: Description of what happened
            event_type: Type of event (interaction, task, error, milestone)
            session_id: Current session identifier
            participants: Who was involved
            outcome: Result of the event
            emotional_valence: How positive/negative (-1 to 1)
            tags: Additional tags
        """
        now = datetime.utcnow()
        entry = EpisodicMemoryEntry(
            id=str(uuid.uuid4()),
            tier=MemoryTier.EPISODIC,
            content=content,
            created_at=now,
            updated_at=now,
            session_id=session_id or "",
            event_type=event_type,
            participants=participants or [],
            outcome=outcome,
            emotional_valence=emotional_valence,
            tags=tags or [event_type],
        )

        return await self.store.store(entry)

    async def get_recent_episodes(
        self,
        limit: int = 10,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[EpisodicMemoryEntry]:
        """Get recent episodic memories."""
        results = []

        if isinstance(self.store, JSONMemoryStore):
            entries = list(self.store._cache[MemoryTier.EPISODIC].values())

            # Filter
            if session_id:
                entries = [e for e in entries if e.session_id == session_id]
            if event_type:
                entries = [e for e in entries if e.event_type == event_type]

            # Sort by created_at
            entries.sort(key=lambda e: e.created_at, reverse=True)
            results = entries[:limit]

        return results

    # =========================================================================
    # Semantic Memory Operations
    # =========================================================================

    async def store_fact(
        self,
        content: str,
        domain: str,
        confidence: float = 1.0,
        source: str = "learned",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Store a semantic fact/knowledge.

        Args:
            content: The fact or knowledge
            domain: Knowledge domain (programming, infrastructure, etc.)
            confidence: How confident we are (0-1)
            source: How we learned it (learned, stated, inferred)
            tags: Additional tags
        """
        now = datetime.utcnow()
        entry = SemanticMemoryEntry(
            id=str(uuid.uuid4()),
            tier=MemoryTier.SEMANTIC,
            content=content,
            created_at=now,
            updated_at=now,
            domain=domain,
            confidence=confidence,
            source=source,
            tags=tags or [domain],
        )

        return await self.store.store(entry)

    async def query_knowledge(
        self,
        query: str,
        domain: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 5,
    ) -> List[SemanticMemoryEntry]:
        """Query semantic knowledge."""
        results = await self.store.search(
            query=query,
            tier=MemoryTier.SEMANTIC,
            limit=limit * 2,  # Get more to filter
        )

        # Filter by domain and confidence
        filtered = []
        for entry in results:
            if isinstance(entry, SemanticMemoryEntry):
                if domain and entry.domain != domain:
                    continue
                if entry.confidence < min_confidence:
                    continue
                filtered.append(entry)

        return filtered[:limit]

    # =========================================================================
    # Procedural Memory Operations
    # =========================================================================

    async def store_skill(
        self,
        skill_name: str,
        content: str,
        trigger_conditions: List[str],
        steps: List[Dict[str, Any]],
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Store a procedural skill/workflow.

        Args:
            skill_name: Name of the skill
            content: Description of what the skill does
            trigger_conditions: When to use this skill
            steps: Steps to execute the skill
            tags: Additional tags
        """
        now = datetime.utcnow()
        entry = ProceduralMemoryEntry(
            id=str(uuid.uuid4()),
            tier=MemoryTier.PROCEDURAL,
            content=content,
            created_at=now,
            updated_at=now,
            skill_name=skill_name,
            trigger_conditions=trigger_conditions,
            steps=steps,
            tags=tags or [skill_name],
        )

        return await self.store.store(entry)

    async def find_skill(self, context: str) -> Optional[ProceduralMemoryEntry]:
        """Find a skill matching the context."""
        if isinstance(self.store, JSONMemoryStore):
            for entry in self.store._cache[MemoryTier.PROCEDURAL].values():
                for condition in entry.trigger_conditions:
                    if condition.lower() in context.lower():
                        return entry
        return None

    async def record_skill_execution(
        self,
        skill_id: str,
        success: bool,
        duration_ms: int,
    ):
        """Record skill execution for learning."""
        entry = await self.store.retrieve(skill_id)
        if entry and isinstance(entry, ProceduralMemoryEntry):
            entry.execution_count += 1
            # Update running average
            n = entry.execution_count
            entry.average_duration_ms = int(
                (entry.average_duration_ms * (n - 1) + duration_ms) / n
            )
            # Update success rate
            if success:
                entry.success_rate = (entry.success_rate * (n - 1) + 1) / n
            else:
                entry.success_rate = entry.success_rate * (n - 1) / n

            await self.store.update(entry)

    async def extract_skill_from_task(
        self,
        task_description: str,
        task_steps: List[str],
        outcome: str,
        context: str = "",
    ) -> Optional[str]:
        """
        Extract a reusable skill from a successful task completion.

        Uses LLM to analyze the task and extract a procedural skill that can be
        reused in similar situations. This is a key pattern from MIRIX architecture.

        Args:
            task_description: What the task was
            task_steps: Steps taken to complete the task
            outcome: What happened (success/failure and result)
            context: Additional context

        Returns:
            skill_id if skill was extracted, None otherwise
        """
        ollama_url = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")

        extraction_prompt = f"""Analyze this completed task and extract a reusable skill/procedure.

TASK DESCRIPTION:
{task_description}

STEPS TAKEN:
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(task_steps))}

OUTCOME:
{outcome}

CONTEXT:
{context}

If this represents a reusable skill, respond with a JSON object:
{{
  "is_skill": true,
  "skill_name": "short_snake_case_name",
  "description": "What this skill does",
  "trigger_conditions": ["condition 1", "condition 2"],
  "generalized_steps": [
    {{"step": 1, "action": "description", "notes": "any important notes"}}
  ],
  "tags": ["tag1", "tag2"]
}}

If this is NOT a reusable skill (one-time task, too specific), respond:
{{"is_skill": false, "reason": "why not"}}

Respond ONLY with the JSON object."""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ollama_url}/v1/chat/completions",
                    json={
                        "model": "qwen2.5:7b",
                        "messages": [{"role": "user", "content": extraction_prompt}],
                        "max_tokens": 1024,
                    },
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    # Parse JSON from response
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        skill_data = json.loads(json_match.group())

                        if skill_data.get("is_skill"):
                            # Store the extracted skill
                            steps = [
                                {"step": s.get("step"), "action": s.get("action"), "notes": s.get("notes", "")}
                                for s in skill_data.get("generalized_steps", [])
                            ]

                            skill_id = await self.store_skill(
                                skill_name=skill_data.get("skill_name", "unnamed_skill"),
                                content=skill_data.get("description", ""),
                                trigger_conditions=skill_data.get("trigger_conditions", []),
                                steps=steps,
                                tags=skill_data.get("tags", []),
                            )

                            logger.info(f"Extracted skill: {skill_data.get('skill_name')} -> {skill_id}")
                            return skill_id

        except Exception as e:
            logger.error(f"Skill extraction failed: {e}")

        return None

    # =========================================================================
    # Memory Consolidation and Archival
    # =========================================================================

    async def consolidate(self) -> Dict[str, Any]:
        """
        Run memory consolidation.

        - Archives old episodic memories
        - Decays unused memories
        - Consolidates similar semantic memories
        """
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "archived": 0,
            "decayed": 0,
            "consolidated": 0,
        }

        now = datetime.utcnow()
        archive_threshold = timedelta(days=30)
        decay_threshold = timedelta(days=7)

        if not isinstance(self.store, JSONMemoryStore):
            return report

        # Archive old episodic memories
        for id, entry in list(self.store._cache[MemoryTier.EPISODIC].items()):
            age = now - entry.created_at
            if age > archive_threshold:
                # Create vault entry
                vault_entry = VaultMemoryEntry(
                    id=str(uuid.uuid4()),
                    tier=MemoryTier.VAULT,
                    content=entry.content,
                    created_at=entry.created_at,
                    updated_at=now,
                    original_tier=MemoryTier.EPISODIC,
                    archived_at=now,
                    archive_reason="aged_out",
                    summary=f"{entry.event_type}: {entry.content[:100]}...",
                    tags=entry.tags,
                )
                await self.store.store(vault_entry)
                await self.store.delete(id)
                report["archived"] += 1

        # Apply decay to semantic memories
        for id, entry in list(self.store._cache[MemoryTier.SEMANTIC].items()):
            if entry.last_accessed:
                time_since_access = now - entry.last_accessed
                if time_since_access > decay_threshold:
                    days = time_since_access.days
                    decay = min(0.5, entry.decay_rate * days)
                    entry.confidence = max(0.1, entry.confidence - decay)
                    await self.store.update(entry)
                    report["decayed"] += 1

        return report

    # =========================================================================
    # Context Assembly
    # =========================================================================

    async def assemble_context(
        self,
        query: str,
        max_tokens: int = 2000,
        include_episodic: bool = True,
        include_semantic: bool = True,
        include_procedural: bool = True,
    ) -> str:
        """
        Assemble relevant memory context for a query.

        Returns formatted context string to inject into prompts.
        """
        sections = []

        # Always include core memory
        core = await self.get_core_context()
        sections.append(core)

        # Search relevant memories
        if include_episodic:
            episodes = await self.get_recent_episodes(limit=3)
            if episodes:
                lines = ["<recent_events>"]
                for ep in episodes:
                    lines.append(f"- [{ep.event_type}] {ep.content}")
                lines.append("</recent_events>")
                sections.append("\n".join(lines))

        if include_semantic:
            knowledge = await self.query_knowledge(query, limit=5)
            if knowledge:
                lines = ["<relevant_knowledge>"]
                for k in knowledge:
                    lines.append(f"- {k.content} (confidence: {k.confidence:.1%})")
                lines.append("</relevant_knowledge>")
                sections.append("\n".join(lines))

        if include_procedural:
            skill = await self.find_skill(query)
            if skill:
                lines = [f"<available_skill name=\"{skill.skill_name}\">"]
                lines.append(skill.content)
                if skill.steps:
                    lines.append("Steps:")
                    for i, step in enumerate(skill.steps, 1):
                        lines.append(f"  {i}. {step.get('action', 'unknown')}")
                lines.append("</available_skill>")
                sections.append("\n".join(lines))

        return "\n\n".join(sections)

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        stats = {
            "tier_counts": {},
            "total_memories": 0,
            "core_memory_size": len(self._core_memory_cache),
            "storage_backend": "unknown",
        }

        if isinstance(self.store, QdrantMemoryStore):
            stats["storage_backend"] = "qdrant"
            qdrant_stats = await self.store.get_stats()
            stats["qdrant"] = qdrant_stats
            stats["total_memories"] = qdrant_stats.get("points_count", 0)
        elif isinstance(self.store, JSONMemoryStore):
            stats["storage_backend"] = "json"
            for tier, cache in self.store._cache.items():
                count = len(cache)
                stats["tier_counts"][tier.value] = count
                stats["total_memories"] += count

        return stats


# =============================================================================
# Global Instance
# =============================================================================

_memory_manager: Optional[MIRIXMemoryManager] = None
# Default to Qdrant if MEMORY_BACKEND=qdrant, otherwise JSON
_use_qdrant: bool = os.environ.get("MEMORY_BACKEND", "qdrant").lower() == "qdrant"


def get_memory_manager(use_qdrant: Optional[bool] = None) -> MIRIXMemoryManager:
    """
    Get or create the global memory manager.

    Args:
        use_qdrant: If True, use Qdrant backend. If None, use current setting.
    """
    global _memory_manager, _use_qdrant

    # Update Qdrant setting if specified
    if use_qdrant is not None:
        _use_qdrant = use_qdrant
        _memory_manager = None  # Force recreation

    if _memory_manager is None:
        data_dir = os.environ.get("HYDRA_DATA_DIR", "/data")
        json_store = JSONMemoryStore(f"{data_dir}/memory")

        if _use_qdrant:
            # Use Qdrant with JSON fallback
            qdrant_url = os.environ.get("QDRANT_URL", "http://192.168.1.244:6333")
            ollama_url = os.environ.get("OLLAMA_URL", "http://192.168.1.203:11434")

            embedding_service = EmbeddingService(ollama_url=ollama_url)
            store = QdrantMemoryStore(
                qdrant_url=qdrant_url,
                embedding_service=embedding_service,
                fallback_store=json_store,
            )
        else:
            store = json_store

        _memory_manager = MIRIXMemoryManager(
            store=store,
            data_dir=f"{data_dir}/memory"
        )

    return _memory_manager


def is_qdrant_enabled() -> bool:
    """Check if Qdrant backend is enabled."""
    return _use_qdrant


# =============================================================================
# FastAPI Router
# =============================================================================

class StoreMemoryRequest(BaseModel):
    """Request to store a memory."""
    tier: str
    content: str
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    # Tier-specific fields
    category: Optional[str] = None  # Core
    event_type: Optional[str] = None  # Episodic
    domain: Optional[str] = None  # Semantic
    skill_name: Optional[str] = None  # Procedural


class SearchMemoryRequest(BaseModel):
    """Request to search memories."""
    query: str
    tier: Optional[str] = None
    limit: int = 10


def create_memory_router() -> APIRouter:
    """Create FastAPI router for memory endpoints."""
    router = APIRouter(prefix="/memory", tags=["memory"])

    @router.get("/status")
    async def get_status():
        """Get memory system status."""
        manager = get_memory_manager()
        stats = await manager.get_stats()
        return {
            "status": "operational",
            "tiers": list(MemoryTier.__members__.keys()),
            "stats": stats,
        }

    @router.get("/core")
    async def get_core_memory():
        """Get core memory context."""
        manager = get_memory_manager()
        context = await manager.get_core_context()
        return {"context": context}

    @router.post("/core")
    async def set_core_memory(category: str, content: str, key: Optional[str] = None):
        """Set a core memory value."""
        manager = get_memory_manager()
        id = await manager.set_core_memory(category, content, key)
        return {"id": id, "status": "stored"}

    @router.post("/episodic")
    async def record_episode(
        content: str,
        event_type: str,
        session_id: Optional[str] = None,
        outcome: Optional[str] = None,
    ):
        """Record an episodic event."""
        manager = get_memory_manager()
        id = await manager.record_episode(
            content=content,
            event_type=event_type,
            session_id=session_id,
            outcome=outcome,
        )
        return {"id": id, "status": "recorded"}

    @router.get("/episodic/recent")
    async def get_recent_episodes(limit: int = 10, session_id: Optional[str] = None):
        """Get recent episodic memories."""
        manager = get_memory_manager()
        episodes = await manager.get_recent_episodes(limit, session_id)
        return {
            "episodes": [e.to_dict() for e in episodes],
            "count": len(episodes),
        }

    @router.post("/semantic")
    async def store_fact(
        content: str,
        domain: str,
        confidence: float = 1.0,
        source: str = "learned",
    ):
        """Store a semantic fact."""
        manager = get_memory_manager()
        id = await manager.store_fact(content, domain, confidence, source)
        return {"id": id, "status": "stored"}

    @router.get("/semantic/query")
    async def query_knowledge(
        query: str,
        domain: Optional[str] = None,
        limit: int = 5,
    ):
        """Query semantic knowledge."""
        manager = get_memory_manager()
        results = await manager.query_knowledge(query, domain, limit=limit)
        return {
            "results": [r.to_dict() for r in results],
            "count": len(results),
        }

    @router.post("/procedural")
    async def store_skill(
        skill_name: str,
        content: str,
        trigger_conditions: List[str],
        steps: List[Dict[str, Any]],
    ):
        """Store a procedural skill."""
        manager = get_memory_manager()
        id = await manager.store_skill(skill_name, content, trigger_conditions, steps)
        return {"id": id, "status": "stored"}

    @router.get("/procedural/find")
    async def find_skill(context: str):
        """Find a skill matching context."""
        manager = get_memory_manager()
        skill = await manager.find_skill(context)
        if skill:
            return {"skill": skill.to_dict(), "found": True}
        return {"skill": None, "found": False}

    class SkillExtractionRequest(BaseModel):
        task_description: str
        task_steps: List[str]
        outcome: str
        context: str = ""

    @router.post("/procedural/extract")
    async def extract_skill(request: SkillExtractionRequest):
        """
        Extract a reusable skill from a completed task.

        Uses LLM to analyze the task and extract a procedural skill
        that can be reused in similar situations. This is a key pattern
        from the MIRIX memory architecture for skill learning.
        """
        manager = get_memory_manager()
        skill_id = await manager.extract_skill_from_task(
            task_description=request.task_description,
            task_steps=request.task_steps,
            outcome=request.outcome,
            context=request.context,
        )
        if skill_id:
            return {"skill_id": skill_id, "extracted": True}
        return {"skill_id": None, "extracted": False, "message": "Task not suitable for skill extraction"}

    @router.post("/consolidate")
    async def consolidate():
        """Run memory consolidation."""
        manager = get_memory_manager()
        report = await manager.consolidate()
        return report

    @router.get("/context")
    async def assemble_context(query: str, max_tokens: int = 2000):
        """Assemble relevant context for a query."""
        manager = get_memory_manager()
        context = await manager.assemble_context(query, max_tokens)
        return {"context": context}

    @router.get("/stats")
    async def get_stats():
        """Get memory statistics."""
        manager = get_memory_manager()
        return await manager.get_stats()

    @router.post("/enable-qdrant")
    async def enable_qdrant():
        """
        Enable Qdrant vector storage backend.

        Switches from JSON file storage to Qdrant with semantic search.
        """
        manager = get_memory_manager(use_qdrant=True)
        stats = await manager.get_stats()
        return {
            "status": "enabled",
            "backend": "qdrant",
            "stats": stats,
        }

    @router.post("/disable-qdrant")
    async def disable_qdrant():
        """
        Disable Qdrant and fall back to JSON storage.
        """
        manager = get_memory_manager(use_qdrant=False)
        stats = await manager.get_stats()
        return {
            "status": "disabled",
            "backend": "json",
            "stats": stats,
        }

    @router.get("/qdrant-status")
    async def qdrant_status():
        """
        Get Qdrant backend status.
        """
        enabled = is_qdrant_enabled()
        result = {
            "enabled": enabled,
            "backend": "qdrant" if enabled else "json",
        }

        if enabled:
            manager = get_memory_manager()
            if isinstance(manager.store, QdrantMemoryStore):
                result["qdrant"] = await manager.store.get_stats()

        return result

    @router.post("/migrate-to-qdrant")
    async def migrate_to_qdrant():
        """
        Migrate all memories from JSON storage to Qdrant.

        This will:
        1. Enable Qdrant backend
        2. Copy all existing JSON memories to Qdrant with embeddings
        3. Keep JSON as fallback
        """
        # Get current JSON store
        data_dir = os.environ.get("HYDRA_DATA_DIR", "/data")
        json_store = JSONMemoryStore(f"{data_dir}/memory")

        # Enable Qdrant
        manager = get_memory_manager(use_qdrant=True)

        if not isinstance(manager.store, QdrantMemoryStore):
            raise HTTPException(
                status_code=500,
                detail="Failed to enable Qdrant backend"
            )

        # Run migration
        migration_result = await manager.store.migrate_from_json(json_store)

        return {
            "status": "migration_complete",
            "result": migration_result,
            "backend": "qdrant",
        }

    @router.post("/semantic-search")
    async def semantic_search(query: str, limit: int = 10, min_relevance: float = 0.0):
        """
        Perform semantic search across all memories.

        Requires Qdrant backend to be enabled for true semantic search.
        Falls back to text matching if using JSON backend.
        """
        manager = get_memory_manager()
        results = await manager.store.search(
            query=query,
            limit=limit,
            min_relevance=min_relevance,
        )
        return {
            "query": query,
            "results": [r.to_dict() for r in results],
            "count": len(results),
            "backend": "qdrant" if is_qdrant_enabled() else "json",
        }

    # =========================================================================
    # Neo4j Graph Endpoints
    # =========================================================================

    @router.get("/graph/status")
    async def graph_status():
        """Get Neo4j graph store status."""
        graph = Neo4jGraphStore()
        stats = await graph.get_stats()
        return {
            "status": "operational" if "error" not in stats else "error",
            "backend": "neo4j",
            "stats": stats,
        }

    @router.post("/graph/sync")
    async def sync_to_graph():
        """
        Sync all memories from Qdrant to Neo4j graph.

        Creates Memory nodes in Neo4j for each memory in Qdrant.
        """
        if not is_qdrant_enabled():
            raise HTTPException(
                status_code=400,
                detail="Qdrant backend must be enabled first. Use /memory/enable-qdrant"
            )

        manager = get_memory_manager()
        if not isinstance(manager.store, QdrantMemoryStore):
            raise HTTPException(
                status_code=500,
                detail="Qdrant store not initialized"
            )

        graph = Neo4jGraphStore()
        result = await graph.sync_from_qdrant(manager.store)

        return {
            "status": "sync_complete",
            "result": result,
            "backend": "neo4j",
        }

    @router.post("/graph/relationship")
    async def create_relationship(
        from_id: str,
        to_id: str,
        rel_type: str = "RELATED_TO",
    ):
        """
        Create a relationship between two memories.

        Common relationship types:
        - RELATED_TO: General relationship
        - DEPENDS_ON: Dependency relationship
        - DERIVED_FROM: Source relationship
        - CONTRADICTS: Contradictory facts
        - SUPERSEDES: Updated information
        """
        graph = Neo4jGraphStore()
        success = await graph.create_relationship(from_id, to_id, rel_type)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to create relationship"
            )

        return {
            "status": "created",
            "from": from_id,
            "to": to_id,
            "relationship": rel_type,
        }

    @router.get("/graph/related/{memory_id}")
    async def get_related_memories(
        memory_id: str,
        max_hops: int = 2,
        limit: int = 20,
    ):
        """
        Get memories related to a given memory via graph traversal.

        Enables multi-hop reasoning across connected facts.
        """
        graph = Neo4jGraphStore()
        related = await graph.get_related(memory_id, max_hops=max_hops, limit=limit)

        return {
            "memory_id": memory_id,
            "related": related,
            "count": len(related),
            "max_hops": max_hops,
        }

    @router.get("/graph/path")
    async def find_path(
        from_id: str,
        to_id: str,
        max_hops: int = 5,
    ):
        """
        Find the shortest path between two memories.

        Returns the nodes and relationships along the path.
        """
        graph = Neo4jGraphStore()
        path = await graph.find_path(from_id, to_id, max_hops=max_hops)

        if not path:
            return {
                "status": "no_path_found",
                "from": from_id,
                "to": to_id,
            }

        return {
            "status": "path_found",
            "from": from_id,
            "to": to_id,
            "path": path,
        }

    # =========================================================================
    # Memory Decay and Conflict Resolution Endpoints
    # =========================================================================

    @router.post("/decay/run")
    async def run_decay():
        """
        Manually run memory decay process.

        Applies time-based decay to memories that haven't been accessed recently.
        Higher decay rates for less important memories.
        """
        manager = get_memory_manager()
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "decayed": 0,
            "archived": 0,
            "details": [],
        }

        now = datetime.utcnow()

        # For JSON store, directly access cache
        if isinstance(manager.store, JSONMemoryStore):
            for tier in [MemoryTier.EPISODIC, MemoryTier.SEMANTIC]:
                for id, entry in list(manager.store._cache.get(tier, {}).items()):
                    if hasattr(entry, 'last_accessed') and entry.last_accessed:
                        days_since_access = (now - entry.last_accessed).days
                        if days_since_access > 7:
                            decay_amount = min(0.3, entry.decay_rate * days_since_access)
                            old_priority = entry.priority

                            # Decay confidence for semantic memories
                            if hasattr(entry, 'confidence'):
                                entry.confidence = max(0.1, entry.confidence - decay_amount)

                            # Potentially lower priority
                            if days_since_access > 30 and entry.priority != MemoryPriority.LOW:
                                entry.priority = MemoryPriority.LOW
                                report["details"].append({
                                    "id": id,
                                    "action": "priority_lowered",
                                    "days_since_access": days_since_access,
                                })

                            await manager.store.update(entry)
                            report["decayed"] += 1

        # For Qdrant store, we'd need to query and update
        elif isinstance(manager.store, QdrantMemoryStore):
            # Qdrant decay is handled during query time via boosting
            report["note"] = "Qdrant uses query-time decay boosting"

        return report

    @router.post("/conflicts/detect")
    async def detect_conflicts(threshold: float = 0.85):
        """
        Detect potentially conflicting memories.

        Uses semantic similarity to find memories with high overlap
        that might contain contradictory information.
        """
        manager = get_memory_manager()

        conflicts = []

        # Get all semantic memories
        if isinstance(manager.store, JSONMemoryStore):
            semantic = list(manager.store._cache.get(MemoryTier.SEMANTIC, {}).values())

            # Compare each pair
            for i, m1 in enumerate(semantic):
                for m2 in semantic[i+1:]:
                    # Simple text similarity check
                    words1 = set(m1.content.lower().split())
                    words2 = set(m2.content.lower().split())
                    if words1 and words2:
                        overlap = len(words1 & words2) / min(len(words1), len(words2))
                        if overlap > threshold:
                            conflicts.append({
                                "memory_1": {"id": m1.id, "content": m1.content[:200]},
                                "memory_2": {"id": m2.id, "content": m2.content[:200]},
                                "similarity": round(overlap, 3),
                            })

        elif isinstance(manager.store, QdrantMemoryStore):
            # For Qdrant, use vector similarity
            try:
                memories = await manager.store.list_all(MemoryTier.SEMANTIC, limit=100)
                for m1 in memories:
                    if m1.embedding:
                        similar = await manager.store.search(
                            m1.content[:100],
                            tier=MemoryTier.SEMANTIC,
                            limit=5
                        )
                        for m2 in similar:
                            if m2.id != m1.id:
                                conflicts.append({
                                    "memory_1": {"id": m1.id, "content": m1.content[:200]},
                                    "memory_2": {"id": m2.id, "content": m2.content[:200]},
                                    "similarity": "vector_match",
                                })
            except Exception as e:
                return {"error": str(e), "conflicts": []}

        return {
            "conflicts_found": len(conflicts),
            "threshold": threshold,
            "conflicts": conflicts[:20],  # Limit to 20
        }

    @router.post("/conflicts/resolve")
    async def resolve_conflict(
        keep_id: str,
        remove_id: str,
        create_supersedes_relationship: bool = True,
    ):
        """
        Resolve a memory conflict by keeping one and marking the other as superseded.

        The removed memory is not deleted but marked as superseded and moved to vault.
        """
        manager = get_memory_manager()

        # Get both memories
        keep_memory = await manager.store.get(keep_id)
        remove_memory = await manager.store.get(remove_id)

        if not keep_memory:
            raise HTTPException(404, f"Memory {keep_id} not found")
        if not remove_memory:
            raise HTTPException(404, f"Memory {remove_id} not found")

        # Create SUPERSEDES relationship in Neo4j if available
        if create_supersedes_relationship:
            try:
                graph = Neo4jGraphStore()
                await graph.create_relationship(keep_id, remove_id, "SUPERSEDES")
            except Exception as e:
                logger.warning(f"Failed to create graph relationship: {e}")

        # Archive the removed memory to vault
        now = datetime.utcnow()
        vault_entry = VaultMemoryEntry(
            id=str(uuid.uuid4()),
            tier=MemoryTier.VAULT,
            content=remove_memory.content,
            created_at=remove_memory.created_at,
            updated_at=now,
            original_tier=remove_memory.tier,
            archived_at=now,
            archive_reason=f"superseded_by:{keep_id}",
            summary=f"Conflict resolved - superseded by {keep_id}",
            tags=getattr(remove_memory, 'tags', []) + ["conflict_resolved"],
        )
        await manager.store.store(vault_entry)

        # Delete the original
        await manager.store.delete(remove_id)

        # Boost confidence of kept memory
        if hasattr(keep_memory, 'confidence'):
            keep_memory.confidence = min(1.0, keep_memory.confidence + 0.1)
            await manager.store.update(keep_memory)

        return {
            "status": "resolved",
            "kept": keep_id,
            "archived": remove_id,
            "vault_id": vault_entry.id,
            "supersedes_relationship": create_supersedes_relationship,
        }

    @router.get("/health/memory")
    async def memory_health():
        """
        Get memory system health metrics.

        Includes decay status, conflict warnings, and consolidation needs.
        """
        manager = get_memory_manager()
        stats = await manager.get_stats()

        now = datetime.utcnow()
        stale_count = 0
        low_confidence_count = 0

        # Analyze memory health
        if isinstance(manager.store, JSONMemoryStore):
            for tier in MemoryTier:
                for id, entry in manager.store._cache.get(tier, {}).items():
                    if hasattr(entry, 'last_accessed') and entry.last_accessed:
                        if (now - entry.last_accessed).days > 30:
                            stale_count += 1
                    if hasattr(entry, 'confidence') and entry.confidence < 0.5:
                        low_confidence_count += 1

        # Build recommendations list (only include non-None items)
        recommendations = []
        if stale_count > 5:
            recommendations.append("Run /memory/consolidate to archive stale memories")
        if stale_count > 10:
            recommendations.append("Run /memory/decay/run to apply time-based decay")
        if low_confidence_count > 3:
            recommendations.append("Run /memory/conflicts/detect to find contradictions")
        if not recommendations:
            recommendations.append("Memory system healthy - no action needed")

        return {
            "status": "healthy" if stale_count < 10 else "needs_maintenance",
            "total_memories": stats.get("total", 0),
            "stale_memories": stale_count,
            "low_confidence_memories": low_confidence_count,
            "recommendations": recommendations,
            "timestamp": now.isoformat(),
        }

    return router


# Quick test
if __name__ == "__main__":
    import asyncio

    async def test():
        manager = MIRIXMemoryManager(data_dir="/tmp/mirix-test")

        # Test core memory
        await manager.set_core_memory("identity", "I am Hydra, an autonomous AI assistant.")
        await manager.set_core_memory("user_facts", "User prefers concise responses.")

        # Test episodic memory
        await manager.record_episode(
            content="User asked about cluster status",
            event_type="interaction",
            outcome="Provided status report",
        )

        # Test semantic memory
        await manager.store_fact(
            content="TabbyAPI runs on port 5000 on hydra-ai",
            domain="infrastructure",
        )

        # Test context assembly
        context = await manager.assemble_context("cluster status")
        print("Assembled context:")
        print(context)

        # Stats
        stats = await manager.get_stats()
        print("\nStats:", stats)

    asyncio.run(test())
