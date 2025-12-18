"""
Multi-Agent Memory Sharing - MIRIX 6-Tier Architecture

Implements a hierarchical memory system for multi-agent collaboration:
- Tier 1: Immediate Context - Current task/conversation
- Tier 2: Working Memory - Recent interactions (minutes)
- Tier 3: Short-term Memory - Session knowledge (hours)
- Tier 4: Long-term Memory - Persistent knowledge
- Tier 5: Shared Memory - Cross-agent collaboration
- Tier 6: World Knowledge - External knowledge bases

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import hashlib

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

MEMORY_OPS = Counter(
    "hydra_memory_operations_total",
    "Total memory operations",
    ["tier", "operation"]
)

MEMORY_LATENCY = Histogram(
    "hydra_memory_latency_seconds",
    "Memory operation latency",
    ["tier"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

MEMORY_SIZE = Gauge(
    "hydra_memory_size_items",
    "Number of items in memory tier",
    ["tier", "agent_id"]
)


# =============================================================================
# Memory Tier Definitions
# =============================================================================

class MemoryTier(IntEnum):
    """Memory tier levels following MIRIX architecture."""
    IMMEDIATE = 1    # Current context
    WORKING = 2      # Recent (minutes)
    SHORT_TERM = 3   # Session (hours)
    LONG_TERM = 4    # Persistent
    SHARED = 5       # Cross-agent
    WORLD = 6        # External knowledge


class MemoryPriority(Enum):
    """Priority levels for memory items."""
    CRITICAL = "critical"      # Never evict
    HIGH = "high"              # Evict last
    NORMAL = "normal"          # Standard eviction
    LOW = "low"                # Evict first
    TEMPORARY = "temporary"    # Auto-expire


# =============================================================================
# Memory Item
# =============================================================================

@dataclass
class MemoryItem:
    """A single memory item in any tier."""
    item_id: str
    content: Any
    tier: MemoryTier
    agent_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    priority: MemoryPriority = MemoryPriority.NORMAL
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None

    def is_expired(self) -> bool:
        """Check if the memory item has expired."""
        if self.ttl_seconds is None:
            return False
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry

    def touch(self) -> None:
        """Update access time and count."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "content": self.content,
            "tier": self.tier.name,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "access_count": self.access_count,
            "priority": self.priority.value,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
            "tags": self.tags,
        }


# =============================================================================
# Tier Storage Classes
# =============================================================================

class ImmediateMemory:
    """
    Tier 1: Immediate Context Memory

    Stores current task context, conversation state, and active goals.
    Fast, in-memory storage with strict size limits.
    """

    MAX_ITEMS = 100
    DEFAULT_TTL = 300  # 5 minutes

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.items: Dict[str, MemoryItem] = {}
        self.current_context: Optional[Dict[str, Any]] = None

    def store(self, content: Any, tags: List[str] = None, metadata: Dict[str, Any] = None) -> MemoryItem:
        """Store immediate context."""
        item_id = str(uuid.uuid4())[:8]

        item = MemoryItem(
            item_id=item_id,
            content=content,
            tier=MemoryTier.IMMEDIATE,
            agent_id=self.agent_id,
            priority=MemoryPriority.HIGH,
            ttl_seconds=self.DEFAULT_TTL,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Evict if at capacity
        if len(self.items) >= self.MAX_ITEMS:
            self._evict_oldest()

        self.items[item_id] = item
        MEMORY_OPS.labels(tier="immediate", operation="store").inc()
        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Get an item by ID."""
        item = self.items.get(item_id)
        if item and not item.is_expired():
            item.touch()
            return item
        return None

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set the current active context."""
        self.current_context = context

    def get_context(self) -> Optional[Dict[str, Any]]:
        """Get the current active context."""
        return self.current_context

    def _evict_oldest(self) -> None:
        """Evict the oldest expired or low-priority item."""
        # First remove expired items
        expired = [k for k, v in self.items.items() if v.is_expired()]
        for k in expired:
            del self.items[k]

        # If still full, remove oldest
        if len(self.items) >= self.MAX_ITEMS:
            oldest = min(self.items.values(), key=lambda x: x.accessed_at)
            if oldest.priority != MemoryPriority.CRITICAL:
                del self.items[oldest.item_id]

    def clear(self) -> int:
        """Clear all items."""
        count = len(self.items)
        self.items.clear()
        self.current_context = None
        return count


class WorkingMemory:
    """
    Tier 2: Working Memory

    Stores recent interactions and intermediate results.
    In-memory with moderate TTL.
    """

    MAX_ITEMS = 500
    DEFAULT_TTL = 1800  # 30 minutes

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.items: Dict[str, MemoryItem] = {}
        self.by_tag: Dict[str, Set[str]] = {}

    def store(self, content: Any, tags: List[str] = None, metadata: Dict[str, Any] = None) -> MemoryItem:
        """Store working memory item."""
        item_id = str(uuid.uuid4())[:8]
        tags = tags or []

        item = MemoryItem(
            item_id=item_id,
            content=content,
            tier=MemoryTier.WORKING,
            agent_id=self.agent_id,
            priority=MemoryPriority.NORMAL,
            ttl_seconds=self.DEFAULT_TTL,
            tags=tags,
            metadata=metadata or {},
        )

        if len(self.items) >= self.MAX_ITEMS:
            self._evict()

        self.items[item_id] = item

        # Index by tags
        for tag in tags:
            if tag not in self.by_tag:
                self.by_tag[tag] = set()
            self.by_tag[tag].add(item_id)

        MEMORY_OPS.labels(tier="working", operation="store").inc()
        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Get item by ID."""
        item = self.items.get(item_id)
        if item and not item.is_expired():
            item.touch()
            return item
        return None

    def search_by_tag(self, tag: str) -> List[MemoryItem]:
        """Search items by tag."""
        item_ids = self.by_tag.get(tag, set())
        items = []
        for item_id in item_ids:
            item = self.items.get(item_id)
            if item and not item.is_expired():
                items.append(item)
        return items

    def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """Get most recent items."""
        valid = [i for i in self.items.values() if not i.is_expired()]
        return sorted(valid, key=lambda x: x.created_at, reverse=True)[:limit]

    def _evict(self) -> None:
        """Evict expired and low-priority items."""
        # Remove expired
        expired = [k for k, v in self.items.items() if v.is_expired()]
        for k in expired:
            self._remove_item(k)

        # Remove low priority if still full
        while len(self.items) >= self.MAX_ITEMS:
            low_priority = [
                i for i in self.items.values()
                if i.priority in (MemoryPriority.LOW, MemoryPriority.TEMPORARY)
            ]
            if low_priority:
                oldest = min(low_priority, key=lambda x: x.accessed_at)
                self._remove_item(oldest.item_id)
            else:
                oldest = min(self.items.values(), key=lambda x: x.accessed_at)
                if oldest.priority != MemoryPriority.CRITICAL:
                    self._remove_item(oldest.item_id)
                else:
                    break

    def _remove_item(self, item_id: str) -> None:
        """Remove an item and its tag references."""
        item = self.items.pop(item_id, None)
        if item:
            for tag in item.tags:
                if tag in self.by_tag:
                    self.by_tag[tag].discard(item_id)


class ShortTermMemory:
    """
    Tier 3: Short-term Memory

    Session-level knowledge persisted to disk.
    Survives restarts within a session.
    """

    MAX_ITEMS = 2000
    DEFAULT_TTL = 86400  # 24 hours

    def __init__(self, agent_id: str, storage_path: str = "/data/memory"):
        self.agent_id = agent_id
        self.storage_path = Path(storage_path) / "short_term" / agent_id
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.items: Dict[str, MemoryItem] = {}
        self._load()

    def _load(self) -> None:
        """Load items from disk."""
        try:
            for file_path in self.storage_path.glob("*.json"):
                data = json.loads(file_path.read_text())
                item = MemoryItem(
                    item_id=data["item_id"],
                    content=data["content"],
                    tier=MemoryTier.SHORT_TERM,
                    agent_id=data["agent_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    accessed_at=datetime.fromisoformat(data["accessed_at"]),
                    access_count=data.get("access_count", 0),
                    priority=MemoryPriority(data.get("priority", "normal")),
                    ttl_seconds=data.get("ttl_seconds"),
                    metadata=data.get("metadata", {}),
                    tags=data.get("tags", []),
                )
                if not item.is_expired():
                    self.items[item.item_id] = item
        except Exception as e:
            logger.error(f"Failed to load short-term memory: {e}")

    def store(self, content: Any, tags: List[str] = None, metadata: Dict[str, Any] = None) -> MemoryItem:
        """Store short-term memory item."""
        item_id = str(uuid.uuid4())[:8]

        item = MemoryItem(
            item_id=item_id,
            content=content,
            tier=MemoryTier.SHORT_TERM,
            agent_id=self.agent_id,
            ttl_seconds=self.DEFAULT_TTL,
            tags=tags or [],
            metadata=metadata or {},
        )

        self.items[item_id] = item
        self._persist(item)

        MEMORY_OPS.labels(tier="short_term", operation="store").inc()
        return item

    def _persist(self, item: MemoryItem) -> None:
        """Persist item to disk."""
        file_path = self.storage_path / f"{item.item_id}.json"
        file_path.write_text(json.dumps(item.to_dict(), default=str))

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Get item by ID."""
        item = self.items.get(item_id)
        if item and not item.is_expired():
            item.touch()
            return item
        return None


class LongTermMemory:
    """
    Tier 4: Long-term Memory

    Persistent knowledge that survives indefinitely.
    Stored in database/vector store.
    """

    def __init__(self, agent_id: str, storage_path: str = "/data/memory"):
        self.agent_id = agent_id
        self.storage_path = Path(storage_path) / "long_term" / agent_id
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.items: Dict[str, MemoryItem] = {}
        self._load()

    def _load(self) -> None:
        """Load items from disk."""
        try:
            for file_path in self.storage_path.glob("*.json"):
                data = json.loads(file_path.read_text())
                item = MemoryItem(
                    item_id=data["item_id"],
                    content=data["content"],
                    tier=MemoryTier.LONG_TERM,
                    agent_id=data["agent_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    accessed_at=datetime.fromisoformat(data["accessed_at"]),
                    access_count=data.get("access_count", 0),
                    priority=MemoryPriority(data.get("priority", "normal")),
                    metadata=data.get("metadata", {}),
                    tags=data.get("tags", []),
                )
                self.items[item.item_id] = item
        except Exception as e:
            logger.error(f"Failed to load long-term memory: {e}")

    def store(
        self,
        content: Any,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        priority: MemoryPriority = MemoryPriority.NORMAL,
    ) -> MemoryItem:
        """Store long-term memory item (permanent)."""
        item_id = hashlib.sha256(
            json.dumps(content, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]

        item = MemoryItem(
            item_id=item_id,
            content=content,
            tier=MemoryTier.LONG_TERM,
            agent_id=self.agent_id,
            priority=priority,
            ttl_seconds=None,  # Never expires
            tags=tags or [],
            metadata=metadata or {},
        )

        self.items[item_id] = item
        self._persist(item)

        MEMORY_OPS.labels(tier="long_term", operation="store").inc()
        return item

    def _persist(self, item: MemoryItem) -> None:
        """Persist item to disk."""
        file_path = self.storage_path / f"{item.item_id}.json"
        file_path.write_text(json.dumps(item.to_dict(), default=str))

    def get(self, item_id: str) -> Optional[MemoryItem]:
        """Get item by ID."""
        return self.items.get(item_id)

    def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """Simple keyword search in long-term memory."""
        query_lower = query.lower()
        results = []

        for item in self.items.values():
            content_str = json.dumps(item.content, default=str).lower()
            if query_lower in content_str:
                results.append(item)

        return sorted(results, key=lambda x: x.access_count, reverse=True)[:limit]


class SharedMemory:
    """
    Tier 5: Shared Memory

    Cross-agent collaboration space.
    Allows agents to share information.
    """

    def __init__(self, storage_path: str = "/data/memory"):
        self.storage_path = Path(storage_path) / "shared"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.items: Dict[str, MemoryItem] = {}
        self.by_owner: Dict[str, Set[str]] = {}
        self.access_control: Dict[str, Set[str]] = {}  # item_id -> allowed agent_ids
        self._load()

    def _load(self) -> None:
        """Load shared items from disk."""
        try:
            for file_path in self.storage_path.glob("*.json"):
                data = json.loads(file_path.read_text())
                item = MemoryItem(
                    item_id=data["item_id"],
                    content=data["content"],
                    tier=MemoryTier.SHARED,
                    agent_id=data["agent_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    accessed_at=datetime.fromisoformat(data["accessed_at"]),
                    access_count=data.get("access_count", 0),
                    priority=MemoryPriority(data.get("priority", "normal")),
                    ttl_seconds=data.get("ttl_seconds"),
                    metadata=data.get("metadata", {}),
                    tags=data.get("tags", []),
                )
                if not item.is_expired():
                    self.items[item.item_id] = item
                    owner = item.agent_id
                    if owner not in self.by_owner:
                        self.by_owner[owner] = set()
                    self.by_owner[owner].add(item.item_id)
                    # Load access control
                    allowed = data.get("metadata", {}).get("allowed_agents", [])
                    if allowed:
                        self.access_control[item.item_id] = set(allowed)
        except Exception as e:
            logger.error(f"Failed to load shared memory: {e}")

    def share(
        self,
        agent_id: str,
        content: Any,
        allowed_agents: List[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        ttl_seconds: Optional[int] = None,
    ) -> MemoryItem:
        """Share memory with other agents."""
        item_id = str(uuid.uuid4())[:8]

        meta = metadata or {}
        if allowed_agents:
            meta["allowed_agents"] = allowed_agents

        item = MemoryItem(
            item_id=item_id,
            content=content,
            tier=MemoryTier.SHARED,
            agent_id=agent_id,
            priority=MemoryPriority.NORMAL,
            ttl_seconds=ttl_seconds,
            tags=tags or [],
            metadata=meta,
        )

        self.items[item_id] = item

        # Track ownership
        if agent_id not in self.by_owner:
            self.by_owner[agent_id] = set()
        self.by_owner[agent_id].add(item_id)

        # Track access control
        if allowed_agents:
            self.access_control[item_id] = set(allowed_agents)

        self._persist(item)

        MEMORY_OPS.labels(tier="shared", operation="share").inc()
        return item

    def _persist(self, item: MemoryItem) -> None:
        """Persist shared item."""
        file_path = self.storage_path / f"{item.item_id}.json"
        file_path.write_text(json.dumps(item.to_dict(), default=str))

    def get(self, item_id: str, requesting_agent: str) -> Optional[MemoryItem]:
        """Get shared item if agent has access."""
        item = self.items.get(item_id)
        if not item or item.is_expired():
            return None

        # Check access control
        if item_id in self.access_control:
            allowed = self.access_control[item_id]
            if requesting_agent not in allowed and item.agent_id != requesting_agent:
                return None

        item.touch()
        return item

    def get_shared_with(self, agent_id: str) -> List[MemoryItem]:
        """Get all items shared with an agent."""
        results = []
        for item_id, item in self.items.items():
            if item.is_expired():
                continue
            # Include if owned by agent or agent has access
            if item.agent_id == agent_id:
                results.append(item)
            elif item_id in self.access_control and agent_id in self.access_control[item_id]:
                results.append(item)
            elif item_id not in self.access_control:
                # No access control means public
                results.append(item)
        return results


class WorldKnowledge:
    """
    Tier 6: World Knowledge

    External knowledge bases and learned facts.
    Read-only for agents, updated by system.
    """

    def __init__(self, storage_path: str = "/data/memory"):
        self.storage_path = Path(storage_path) / "world"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.knowledge: Dict[str, Dict[str, Any]] = {}
        self.categories: Dict[str, Set[str]] = {}
        self._load()

    def _load(self) -> None:
        """Load world knowledge from disk."""
        try:
            for file_path in self.storage_path.glob("*.json"):
                data = json.loads(file_path.read_text())
                category = data.get("category", "general")
                key = data.get("key")
                if key:
                    self.knowledge[key] = data
                    if category not in self.categories:
                        self.categories[category] = set()
                    self.categories[category].add(key)
        except Exception as e:
            logger.error(f"Failed to load world knowledge: {e}")

    def add_knowledge(
        self,
        key: str,
        content: Any,
        category: str = "general",
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Add world knowledge (system only)."""
        entry = {
            "key": key,
            "content": content,
            "category": category,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self.knowledge[key] = entry

        if category not in self.categories:
            self.categories[category] = set()
        self.categories[category].add(key)

        # Persist
        file_path = self.storage_path / f"{hashlib.md5(key.encode()).hexdigest()}.json"
        file_path.write_text(json.dumps(entry, default=str))

        MEMORY_OPS.labels(tier="world", operation="add").inc()
        return entry

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get world knowledge by key."""
        return self.knowledge.get(key)

    def search_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all knowledge in a category."""
        keys = self.categories.get(category, set())
        return [self.knowledge[k] for k in keys if k in self.knowledge]

    def list_categories(self) -> List[str]:
        """List all knowledge categories."""
        return list(self.categories.keys())


# =============================================================================
# Unified Memory Manager
# =============================================================================

class MultiAgentMemoryManager:
    """
    Unified manager for the 6-tier MIRIX memory architecture.

    Provides a single interface for agents to interact with all memory tiers.
    """

    def __init__(self, storage_path: str = "/data/memory"):
        self.storage_path = storage_path

        # Agent-specific memories (created on demand)
        self.immediate: Dict[str, ImmediateMemory] = {}
        self.working: Dict[str, WorkingMemory] = {}
        self.short_term: Dict[str, ShortTermMemory] = {}
        self.long_term: Dict[str, LongTermMemory] = {}

        # Shared memories (global)
        self.shared = SharedMemory(storage_path)
        self.world = WorldKnowledge(storage_path)

        logger.info("Multi-agent memory manager initialized")

    def _get_or_create_agent_memory(self, agent_id: str) -> None:
        """Ensure agent-specific memory tiers exist."""
        if agent_id not in self.immediate:
            self.immediate[agent_id] = ImmediateMemory(agent_id)
        if agent_id not in self.working:
            self.working[agent_id] = WorkingMemory(agent_id)
        if agent_id not in self.short_term:
            self.short_term[agent_id] = ShortTermMemory(agent_id, self.storage_path)
        if agent_id not in self.long_term:
            self.long_term[agent_id] = LongTermMemory(agent_id, self.storage_path)

    async def store(
        self,
        agent_id: str,
        content: Any,
        tier: MemoryTier,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        allowed_agents: List[str] = None,
    ) -> MemoryItem:
        """Store content in the specified memory tier."""
        import time
        start = time.time()

        self._get_or_create_agent_memory(agent_id)

        if tier == MemoryTier.IMMEDIATE:
            item = self.immediate[agent_id].store(content, tags, metadata)
        elif tier == MemoryTier.WORKING:
            item = self.working[agent_id].store(content, tags, metadata)
        elif tier == MemoryTier.SHORT_TERM:
            item = self.short_term[agent_id].store(content, tags, metadata)
        elif tier == MemoryTier.LONG_TERM:
            item = self.long_term[agent_id].store(content, tags, metadata)
        elif tier == MemoryTier.SHARED:
            item = self.shared.share(agent_id, content, allowed_agents, tags, metadata)
        else:
            raise ValueError(f"Cannot store in tier {tier}")

        MEMORY_LATENCY.labels(tier=tier.name.lower()).observe(time.time() - start)
        return item

    async def retrieve(
        self,
        agent_id: str,
        query: str,
        tiers: List[MemoryTier] = None,
        limit: int = 10,
    ) -> List[MemoryItem]:
        """Retrieve memories across specified tiers."""
        self._get_or_create_agent_memory(agent_id)

        if tiers is None:
            tiers = list(MemoryTier)

        results = []

        for tier in tiers:
            if tier == MemoryTier.IMMEDIATE:
                # Get recent from immediate
                items = list(self.immediate[agent_id].items.values())
                results.extend([i for i in items if not i.is_expired()][:5])

            elif tier == MemoryTier.WORKING:
                # Search working memory by tag match
                query_words = query.lower().split()
                for word in query_words:
                    results.extend(self.working[agent_id].search_by_tag(word))

            elif tier == MemoryTier.SHORT_TERM:
                # Search short-term by content
                for item in self.short_term[agent_id].items.values():
                    if not item.is_expired():
                        content_str = json.dumps(item.content, default=str).lower()
                        if query.lower() in content_str:
                            results.append(item)

            elif tier == MemoryTier.LONG_TERM:
                results.extend(self.long_term[agent_id].search(query, limit))

            elif tier == MemoryTier.SHARED:
                shared_items = self.shared.get_shared_with(agent_id)
                for item in shared_items:
                    content_str = json.dumps(item.content, default=str).lower()
                    if query.lower() in content_str:
                        results.append(item)

        # Deduplicate and limit
        seen = set()
        unique = []
        for item in results:
            if item.item_id not in seen:
                seen.add(item.item_id)
                unique.append(item)

        return unique[:limit]

    async def promote(
        self,
        agent_id: str,
        item_id: str,
        from_tier: MemoryTier,
        to_tier: MemoryTier,
    ) -> Optional[MemoryItem]:
        """Promote a memory item to a higher tier (longer persistence)."""
        self._get_or_create_agent_memory(agent_id)

        # Get source item
        source_storage = self._get_tier_storage(agent_id, from_tier)
        if not source_storage:
            return None

        item = source_storage.get(item_id) if hasattr(source_storage, 'get') else None
        if not item:
            return None

        # Store in destination
        new_item = await self.store(
            agent_id=agent_id,
            content=item.content,
            tier=to_tier,
            tags=item.tags,
            metadata=item.metadata,
        )

        MEMORY_OPS.labels(tier=from_tier.name.lower(), operation="promote").inc()
        return new_item

    def _get_tier_storage(self, agent_id: str, tier: MemoryTier):
        """Get the storage object for a tier."""
        if tier == MemoryTier.IMMEDIATE:
            return self.immediate.get(agent_id)
        elif tier == MemoryTier.WORKING:
            return self.working.get(agent_id)
        elif tier == MemoryTier.SHORT_TERM:
            return self.short_term.get(agent_id)
        elif tier == MemoryTier.LONG_TERM:
            return self.long_term.get(agent_id)
        elif tier == MemoryTier.SHARED:
            return self.shared
        elif tier == MemoryTier.WORLD:
            return self.world
        return None

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get memory statistics for an agent."""
        self._get_or_create_agent_memory(agent_id)

        return {
            "agent_id": agent_id,
            "immediate": len(self.immediate[agent_id].items),
            "working": len(self.working[agent_id].items),
            "short_term": len(self.short_term[agent_id].items),
            "long_term": len(self.long_term[agent_id].items),
            "shared_owned": len(self.shared.by_owner.get(agent_id, set())),
            "shared_accessible": len(self.shared.get_shared_with(agent_id)),
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global memory statistics."""
        total_items = 0
        by_tier = {}

        for tier in MemoryTier:
            tier_count = 0
            if tier in (MemoryTier.IMMEDIATE, MemoryTier.WORKING, MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM):
                storage_dict = getattr(self, tier.name.lower(), {})
                for agent_storage in storage_dict.values():
                    tier_count += len(agent_storage.items)
            elif tier == MemoryTier.SHARED:
                tier_count = len(self.shared.items)
            elif tier == MemoryTier.WORLD:
                tier_count = len(self.world.knowledge)

            by_tier[tier.name.lower()] = tier_count
            total_items += tier_count

        return {
            "total_items": total_items,
            "by_tier": by_tier,
            "registered_agents": len(self.immediate),
            "world_categories": self.world.list_categories(),
        }


# =============================================================================
# Global Instance
# =============================================================================

_memory_manager: Optional[MultiAgentMemoryManager] = None


def get_memory_manager() -> MultiAgentMemoryManager:
    """Get or create the global memory manager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MultiAgentMemoryManager()
    return _memory_manager


# =============================================================================
# FastAPI Router
# =============================================================================

def create_multi_agent_memory_router():
    """Create FastAPI router for multi-agent memory endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/multi-memory", tags=["multi-agent-memory"])

    class StoreRequest(BaseModel):
        agent_id: str
        content: Any
        tier: int  # 1-6
        tags: Optional[List[str]] = None
        metadata: Optional[Dict[str, Any]] = None
        allowed_agents: Optional[List[str]] = None

    class RetrieveRequest(BaseModel):
        agent_id: str
        query: str
        tiers: Optional[List[int]] = None
        limit: int = 10

    class ShareRequest(BaseModel):
        agent_id: str
        content: Any
        allowed_agents: Optional[List[str]] = None
        tags: Optional[List[str]] = None
        metadata: Optional[Dict[str, Any]] = None

    class WorldKnowledgeRequest(BaseModel):
        key: str
        content: Any
        category: str = "general"
        metadata: Optional[Dict[str, Any]] = None

    @router.get("/status")
    async def memory_status():
        """Get global memory status and statistics."""
        manager = get_memory_manager()
        return manager.get_global_stats()

    @router.get("/agents/{agent_id}/stats")
    async def agent_memory_stats(agent_id: str):
        """Get memory statistics for a specific agent."""
        manager = get_memory_manager()
        return manager.get_agent_stats(agent_id)

    @router.post("/store")
    async def store_memory(request: StoreRequest):
        """Store content in a specific memory tier."""
        manager = get_memory_manager()

        try:
            tier = MemoryTier(request.tier)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tier: {request.tier}. Valid: 1-6")

        item = await manager.store(
            agent_id=request.agent_id,
            content=request.content,
            tier=tier,
            tags=request.tags,
            metadata=request.metadata,
            allowed_agents=request.allowed_agents,
        )

        return {
            "item_id": item.item_id,
            "tier": tier.name,
            "agent_id": item.agent_id,
            "stored_at": item.created_at.isoformat(),
        }

    @router.post("/retrieve")
    async def retrieve_memories(request: RetrieveRequest):
        """Retrieve memories across tiers."""
        manager = get_memory_manager()

        tiers = None
        if request.tiers:
            try:
                tiers = [MemoryTier(t) for t in request.tiers]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid tier values")

        items = await manager.retrieve(
            agent_id=request.agent_id,
            query=request.query,
            tiers=tiers,
            limit=request.limit,
        )

        return {
            "query": request.query,
            "results": [item.to_dict() for item in items],
            "count": len(items),
        }

    @router.post("/share")
    async def share_memory(request: ShareRequest):
        """Share memory with other agents (Tier 5)."""
        manager = get_memory_manager()

        item = await manager.store(
            agent_id=request.agent_id,
            content=request.content,
            tier=MemoryTier.SHARED,
            tags=request.tags,
            metadata=request.metadata,
            allowed_agents=request.allowed_agents,
        )

        return {
            "item_id": item.item_id,
            "shared_by": request.agent_id,
            "allowed_agents": request.allowed_agents or "all",
        }

    @router.get("/shared/{agent_id}")
    async def get_shared_memories(agent_id: str):
        """Get all memories shared with an agent."""
        manager = get_memory_manager()
        items = manager.shared.get_shared_with(agent_id)

        return {
            "agent_id": agent_id,
            "shared_items": [item.to_dict() for item in items],
            "count": len(items),
        }

    @router.post("/world")
    async def add_world_knowledge(request: WorldKnowledgeRequest):
        """Add world knowledge (system only, Tier 6)."""
        manager = get_memory_manager()

        entry = manager.world.add_knowledge(
            key=request.key,
            content=request.content,
            category=request.category,
            metadata=request.metadata,
        )

        return {
            "key": request.key,
            "category": request.category,
            "added_at": entry["created_at"],
        }

    @router.get("/world/{key}")
    async def get_world_knowledge(key: str):
        """Get world knowledge by key."""
        manager = get_memory_manager()
        entry = manager.world.get(key)

        if not entry:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        return entry

    @router.get("/world/categories")
    async def list_world_categories():
        """List all world knowledge categories."""
        manager = get_memory_manager()
        return {"categories": manager.world.list_categories()}

    @router.get("/tiers")
    async def list_tiers():
        """List all memory tiers with descriptions."""
        return {
            "tiers": [
                {"level": 1, "name": "IMMEDIATE", "description": "Current context, fast, 5min TTL"},
                {"level": 2, "name": "WORKING", "description": "Recent interactions, 30min TTL"},
                {"level": 3, "name": "SHORT_TERM", "description": "Session knowledge, 24hr TTL"},
                {"level": 4, "name": "LONG_TERM", "description": "Persistent, no expiry"},
                {"level": 5, "name": "SHARED", "description": "Cross-agent collaboration"},
                {"level": 6, "name": "WORLD", "description": "Global knowledge base"},
            ]
        }

    return router
