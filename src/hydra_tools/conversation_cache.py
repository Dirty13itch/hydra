"""
Hydra Conversation Cache

High-performance conversation history and context caching using Redis.
Designed to leverage the 190GB available RAM on hydra-storage for
faster context handling in long conversations.

Features:
- Conversation history storage with TTL
- Context window caching
- Session state management
- Prompt template caching

Author: Hydra Autonomous System
Created: 2025-12-17
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Prometheus Metrics
# =============================================================================

CACHE_HITS = Counter(
    "hydra_conversation_cache_hits_total",
    "Total cache hits",
    ["cache_type"]
)

CACHE_MISSES = Counter(
    "hydra_conversation_cache_misses_total",
    "Total cache misses",
    ["cache_type"]
)

CACHE_LATENCY = Histogram(
    "hydra_conversation_cache_latency_seconds",
    "Cache operation latency",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25]
)

CACHE_SIZE = Gauge(
    "hydra_conversation_cache_size_bytes",
    "Current cache size in bytes"
)

ACTIVE_CONVERSATIONS = Gauge(
    "hydra_active_conversations",
    "Number of active conversation sessions"
)

# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ConversationCacheConfig:
    """Configuration for conversation caching."""
    redis_url: str = "redis://192.168.1.244:6379"
    redis_password: Optional[str] = os.environ.get("REDIS_PASSWORD", "ls32WXmttrQ6v3Jxw9bh6XmFqhCYmIC")
    redis_db: int = 1  # Use separate DB from main Redis

    # Cache settings
    conversation_ttl_hours: int = 24  # How long to keep conversations
    context_window_ttl_hours: int = 4  # How long to keep context windows
    prompt_template_ttl_hours: int = 168  # 1 week for prompt templates
    max_conversation_length: int = 100  # Max messages per conversation
    max_context_tokens: int = 32000  # Max tokens in context window

    # Key prefixes
    conversation_prefix: str = "conv:"
    context_prefix: str = "ctx:"
    prompt_prefix: str = "prompt:"
    session_prefix: str = "session:"


# =============================================================================
# Conversation Cache Implementation
# =============================================================================

class ConversationCache:
    """
    High-performance conversation cache using Redis.

    Caches:
    - Conversation history (message sequences)
    - Context windows (preprocessed context for inference)
    - Prompt templates (frequently used system prompts)
    - Session state (user preferences, model settings)
    """

    def __init__(self, config: Optional[ConversationCacheConfig] = None):
        self.config = config or ConversationCacheConfig()
        self._redis = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        if self._initialized:
            return True

        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self.config.redis_url,
                password=self.config.redis_password,
                db=self.config.redis_db,
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()
            self._initialized = True
            logger.info("Conversation cache initialized successfully")
            return True

        except ImportError:
            logger.warning("redis package not available")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize conversation cache: {e}")
            return False

    # =========================================================================
    # Conversation History
    # =========================================================================

    async def store_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store a message in conversation history."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return False

        start = time.time()
        try:
            key = f"{self.config.conversation_prefix}{conversation_id}"

            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            # Push to list and trim to max length
            await self._redis.rpush(key, json.dumps(message))
            await self._redis.ltrim(key, -self.config.max_conversation_length, -1)

            # Set TTL
            await self._redis.expire(
                key,
                timedelta(hours=self.config.conversation_ttl_hours)
            )

            CACHE_LATENCY.labels(operation="store_message").observe(time.time() - start)
            return True

        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return False

    async def get_conversation(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get conversation history."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return []

        start = time.time()
        try:
            key = f"{self.config.conversation_prefix}{conversation_id}"

            # Get all messages (or last N)
            if limit:
                messages = await self._redis.lrange(key, -limit, -1)
            else:
                messages = await self._redis.lrange(key, 0, -1)

            result = [json.loads(m) for m in messages]

            CACHE_LATENCY.labels(operation="get_conversation").observe(time.time() - start)
            CACHE_HITS.labels(cache_type="conversation").inc() if result else CACHE_MISSES.labels(cache_type="conversation").inc()

            return result

        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return []

    async def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return False

        try:
            key = f"{self.config.conversation_prefix}{conversation_id}"
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to clear conversation: {e}")
            return False

    # =========================================================================
    # Context Window Caching
    # =========================================================================

    async def cache_context(
        self,
        context_hash: str,
        context: Dict[str, Any],
    ) -> bool:
        """Cache a preprocessed context window."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return False

        start = time.time()
        try:
            key = f"{self.config.context_prefix}{context_hash}"

            await self._redis.set(
                key,
                json.dumps(context),
                ex=timedelta(hours=self.config.context_window_ttl_hours),
            )

            CACHE_LATENCY.labels(operation="cache_context").observe(time.time() - start)
            return True

        except Exception as e:
            logger.error(f"Failed to cache context: {e}")
            return False

    async def get_context(self, context_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached context window."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return None

        start = time.time()
        try:
            key = f"{self.config.context_prefix}{context_hash}"
            data = await self._redis.get(key)

            CACHE_LATENCY.labels(operation="get_context").observe(time.time() - start)

            if data:
                CACHE_HITS.labels(cache_type="context").inc()
                return json.loads(data)
            else:
                CACHE_MISSES.labels(cache_type="context").inc()
                return None

        except Exception as e:
            logger.error(f"Failed to get context: {e}")
            return None

    # =========================================================================
    # Prompt Template Caching
    # =========================================================================

    async def cache_prompt_template(
        self,
        template_name: str,
        template: str,
        variables: Optional[List[str]] = None,
    ) -> bool:
        """Cache a prompt template."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return False

        try:
            key = f"{self.config.prompt_prefix}{template_name}"

            data = {
                "template": template,
                "variables": variables or [],
                "cached_at": datetime.utcnow().isoformat(),
            }

            await self._redis.set(
                key,
                json.dumps(data),
                ex=timedelta(hours=self.config.prompt_template_ttl_hours),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to cache prompt template: {e}")
            return False

    async def get_prompt_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get a cached prompt template."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return None

        try:
            key = f"{self.config.prompt_prefix}{template_name}"
            data = await self._redis.get(key)

            if data:
                CACHE_HITS.labels(cache_type="prompt").inc()
                return json.loads(data)
            else:
                CACHE_MISSES.labels(cache_type="prompt").inc()
                return None

        except Exception as e:
            logger.error(f"Failed to get prompt template: {e}")
            return None

    # =========================================================================
    # Session State
    # =========================================================================

    async def set_session_state(
        self,
        session_id: str,
        state: Dict[str, Any],
        ttl_hours: int = 24,
    ) -> bool:
        """Store session state."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return False

        try:
            key = f"{self.config.session_prefix}{session_id}"

            state["updated_at"] = datetime.utcnow().isoformat()

            await self._redis.set(
                key,
                json.dumps(state),
                ex=timedelta(hours=ttl_hours),
            )

            return True

        except Exception as e:
            logger.error(f"Failed to set session state: {e}")
            return False

    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return None

        try:
            key = f"{self.config.session_prefix}{session_id}"
            data = await self._redis.get(key)

            if data:
                return json.loads(data)
            return None

        except Exception as e:
            logger.error(f"Failed to get session state: {e}")
            return None

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._initialized:
            await self.initialize()

        if not self._redis:
            return {"status": "not_initialized"}

        try:
            info = await self._redis.info("memory")
            keyspace = await self._redis.info("keyspace")

            # Count keys by type
            conv_keys = len(await self._redis.keys(f"{self.config.conversation_prefix}*"))
            ctx_keys = len(await self._redis.keys(f"{self.config.context_prefix}*"))
            prompt_keys = len(await self._redis.keys(f"{self.config.prompt_prefix}*"))
            session_keys = len(await self._redis.keys(f"{self.config.session_prefix}*"))

            ACTIVE_CONVERSATIONS.set(conv_keys)
            CACHE_SIZE.set(info.get("used_memory", 0))

            return {
                "status": "connected",
                "redis_url": self.config.redis_url.split("@")[-1],  # Hide password
                "memory_used": info.get("used_memory_human", "unknown"),
                "memory_peak": info.get("used_memory_peak_human", "unknown"),
                "conversations": conv_keys,
                "context_windows": ctx_keys,
                "prompt_templates": prompt_keys,
                "sessions": session_keys,
                "total_keys": conv_keys + ctx_keys + prompt_keys + session_keys,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._initialized = False


# =============================================================================
# Global Instance
# =============================================================================

_cache_instance: Optional[ConversationCache] = None


def get_conversation_cache() -> ConversationCache:
    """Get the global conversation cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ConversationCache()
    return _cache_instance


# =============================================================================
# Helper Functions
# =============================================================================

def compute_context_hash(messages: List[Dict[str, Any]], model: str = "") -> str:
    """Compute a hash for a context window."""
    content = json.dumps(messages, sort_keys=True) + model
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# =============================================================================
# FastAPI Router
# =============================================================================

def create_conversation_cache_router():
    """Create FastAPI router for conversation cache endpoints."""
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel

    router = APIRouter(prefix="/conversation-cache", tags=["conversation-cache"])

    class StoreMessageRequest(BaseModel):
        conversation_id: str
        role: str
        content: str
        metadata: Optional[Dict[str, Any]] = None

    class GetConversationRequest(BaseModel):
        conversation_id: str
        limit: Optional[int] = None

    class CacheContextRequest(BaseModel):
        context_hash: str
        context: Dict[str, Any]

    class PromptTemplateRequest(BaseModel):
        template_name: str
        template: str
        variables: Optional[List[str]] = None

    class SessionStateRequest(BaseModel):
        session_id: str
        state: Dict[str, Any]
        ttl_hours: int = 24

    @router.get("/status")
    async def cache_status():
        """Get conversation cache status and statistics."""
        cache = get_conversation_cache()
        return await cache.get_stats()

    @router.post("/initialize")
    async def initialize_cache():
        """Initialize the conversation cache."""
        cache = get_conversation_cache()
        success = await cache.initialize()
        return {"initialized": success}

    @router.post("/messages")
    async def store_message(request: StoreMessageRequest):
        """Store a message in conversation history."""
        cache = get_conversation_cache()
        success = await cache.store_message(
            conversation_id=request.conversation_id,
            role=request.role,
            content=request.content,
            metadata=request.metadata,
        )
        if success:
            return {"status": "stored", "conversation_id": request.conversation_id}
        raise HTTPException(status_code=500, detail="Failed to store message")

    @router.get("/conversations/{conversation_id}")
    async def get_conversation(conversation_id: str, limit: Optional[int] = None):
        """Get conversation history."""
        cache = get_conversation_cache()
        messages = await cache.get_conversation(conversation_id, limit)
        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "count": len(messages),
        }

    @router.delete("/conversations/{conversation_id}")
    async def clear_conversation(conversation_id: str):
        """Clear a conversation."""
        cache = get_conversation_cache()
        success = await cache.clear_conversation(conversation_id)
        return {"cleared": success, "conversation_id": conversation_id}

    @router.post("/context")
    async def cache_context(request: CacheContextRequest):
        """Cache a preprocessed context window."""
        cache = get_conversation_cache()
        success = await cache.cache_context(
            context_hash=request.context_hash,
            context=request.context,
        )
        if success:
            return {"status": "cached", "context_hash": request.context_hash}
        raise HTTPException(status_code=500, detail="Failed to cache context")

    @router.get("/context/{context_hash}")
    async def get_context(context_hash: str):
        """Get cached context window."""
        cache = get_conversation_cache()
        context = await cache.get_context(context_hash)
        if context:
            return {"context_hash": context_hash, "context": context}
        raise HTTPException(status_code=404, detail="Context not found")

    @router.post("/prompts")
    async def cache_prompt(request: PromptTemplateRequest):
        """Cache a prompt template."""
        cache = get_conversation_cache()
        success = await cache.cache_prompt_template(
            template_name=request.template_name,
            template=request.template,
            variables=request.variables,
        )
        if success:
            return {"status": "cached", "template_name": request.template_name}
        raise HTTPException(status_code=500, detail="Failed to cache prompt")

    @router.get("/prompts/{template_name}")
    async def get_prompt(template_name: str):
        """Get a cached prompt template."""
        cache = get_conversation_cache()
        template = await cache.get_prompt_template(template_name)
        if template:
            return {"template_name": template_name, **template}
        raise HTTPException(status_code=404, detail="Prompt template not found")

    @router.post("/sessions")
    async def set_session(request: SessionStateRequest):
        """Store session state."""
        cache = get_conversation_cache()
        success = await cache.set_session_state(
            session_id=request.session_id,
            state=request.state,
            ttl_hours=request.ttl_hours,
        )
        if success:
            return {"status": "stored", "session_id": request.session_id}
        raise HTTPException(status_code=500, detail="Failed to store session")

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        """Get session state."""
        cache = get_conversation_cache()
        state = await cache.get_session_state(session_id)
        if state:
            return {"session_id": session_id, "state": state}
        raise HTTPException(status_code=404, detail="Session not found")

    return router
