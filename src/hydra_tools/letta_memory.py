"""
Letta Memory Enhancement Tools

Provides enhanced memory management for Letta agents including:
- Model performance tracking and analysis
- User preference persistence
- System learnings storage
- Automatic memory consolidation
- Cross-session memory retrieval

Integration with Letta memory blocks for persistent agent state.
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum


class MemoryBlockType(str, Enum):
    """Types of memory blocks for Letta agents."""
    MODEL_PERFORMANCE = "model_performance"
    USER_PREFERENCES = "user_preferences"
    SYSTEM_LEARNINGS = "system_learnings"
    CONVERSATION_SUMMARY = "conversation_summary"
    OPERATIONAL_STATE = "operational_state"


@dataclass
class ModelPerformance:
    """Tracks performance metrics for a model."""
    model_name: str
    total_requests: int = 0
    avg_latency_ms: float = 0.0
    avg_tokens_per_sec: float = 0.0
    error_rate: float = 0.0
    last_used: Optional[datetime] = None
    quality_scores: List[float] = field(default_factory=list)
    context_window: int = 0
    recommended_tasks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "model_name": self.model_name,
            "total_requests": self.total_requests,
            "avg_latency_ms": self.avg_latency_ms,
            "avg_tokens_per_sec": self.avg_tokens_per_sec,
            "error_rate": self.error_rate,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "quality_scores": self.quality_scores[-10:],  # Keep last 10
            "context_window": self.context_window,
            "recommended_tasks": self.recommended_tasks
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelPerformance":
        """Create from dictionary."""
        last_used = data.get("last_used")
        if last_used:
            last_used = datetime.fromisoformat(last_used)
        return cls(
            model_name=data["model_name"],
            total_requests=data.get("total_requests", 0),
            avg_latency_ms=data.get("avg_latency_ms", 0.0),
            avg_tokens_per_sec=data.get("avg_tokens_per_sec", 0.0),
            error_rate=data.get("error_rate", 0.0),
            last_used=last_used,
            quality_scores=data.get("quality_scores", []),
            context_window=data.get("context_window", 0),
            recommended_tasks=data.get("recommended_tasks", [])
        )


@dataclass
class UserPreference:
    """A user preference learned from interactions."""
    category: str
    preference: str
    confidence: float
    examples: List[str] = field(default_factory=list)
    learned_at: datetime = field(default_factory=datetime.now)
    last_confirmed: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "category": self.category,
            "preference": self.preference,
            "confidence": self.confidence,
            "examples": self.examples[-5:],  # Keep last 5
            "learned_at": self.learned_at.isoformat(),
            "last_confirmed": self.last_confirmed.isoformat() if self.last_confirmed else None
        }


@dataclass
class SystemLearning:
    """A learned pattern about system behavior."""
    pattern: str
    description: str
    frequency: int = 1
    last_observed: datetime = field(default_factory=datetime.now)
    remediation: Optional[str] = None
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "pattern": self.pattern,
            "description": self.description,
            "frequency": self.frequency,
            "last_observed": self.last_observed.isoformat(),
            "remediation": self.remediation,
            "confidence": self.confidence
        }


class LettaMemoryManager:
    """
    Manages enhanced memory blocks for Letta agents.

    Provides high-level abstractions for storing and retrieving
    model performance data, user preferences, and system learnings.
    """

    def __init__(
        self,
        letta_url: str = "http://192.168.1.244:8283",
        agent_name: str = "hydra-steward"
    ):
        """
        Initialize the memory manager.

        Args:
            letta_url: URL of the Letta API
            agent_name: Name of the Letta agent to manage
        """
        self.letta_url = letta_url
        self.agent_name = agent_name

        # In-memory cache
        self._model_performance: Dict[str, ModelPerformance] = {}
        self._user_preferences: Dict[str, UserPreference] = {}
        self._system_learnings: Dict[str, SystemLearning] = {}

    async def _get_memory_block(self, block_type: MemoryBlockType) -> Optional[Dict[str, Any]]:
        """Get a memory block from Letta."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.letta_url}/v1/agents/{self.agent_name}/memory"
                )
                if resp.status_code == 200:
                    memory = resp.json()
                    # Find the block by label
                    for block in memory.get("memory", {}).get("blocks", []):
                        if block.get("label") == block_type.value:
                            value = block.get("value", "{}")
                            return json.loads(value) if isinstance(value, str) else value
        except Exception as e:
            print(f"Error getting memory block: {e}")
        return None

    async def _update_memory_block(self, block_type: MemoryBlockType, data: Dict[str, Any]) -> bool:
        """Update a memory block in Letta."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.patch(
                    f"{self.letta_url}/v1/agents/{self.agent_name}/memory/block/{block_type.value}",
                    json={"value": json.dumps(data)}
                )
                return resp.status_code == 200
        except Exception as e:
            print(f"Error updating memory block: {e}")
        return False

    # Model Performance Methods

    async def record_model_performance(
        self,
        model_name: str,
        latency_ms: float,
        tokens_per_sec: float,
        success: bool = True,
        quality_score: Optional[float] = None
    ) -> None:
        """
        Record a model inference event.

        Args:
            model_name: Name of the model used
            latency_ms: Request latency in milliseconds
            tokens_per_sec: Token generation speed
            success: Whether the request succeeded
            quality_score: Optional quality rating (0-1)
        """
        if model_name not in self._model_performance:
            self._model_performance[model_name] = ModelPerformance(model_name=model_name)

        perf = self._model_performance[model_name]

        # Update running averages
        n = perf.total_requests
        perf.avg_latency_ms = (perf.avg_latency_ms * n + latency_ms) / (n + 1)
        perf.avg_tokens_per_sec = (perf.avg_tokens_per_sec * n + tokens_per_sec) / (n + 1)
        perf.total_requests = n + 1
        perf.last_used = datetime.now()

        if not success:
            perf.error_rate = (perf.error_rate * n + 1) / (n + 1)

        if quality_score is not None:
            perf.quality_scores.append(quality_score)

        # Sync to Letta periodically (every 10 requests)
        if perf.total_requests % 10 == 0:
            await self._sync_model_performance()

    async def get_model_performance(self, model_name: str) -> Optional[ModelPerformance]:
        """Get performance data for a specific model."""
        if model_name not in self._model_performance:
            # Try to load from Letta
            data = await self._get_memory_block(MemoryBlockType.MODEL_PERFORMANCE)
            if data and model_name in data:
                self._model_performance[model_name] = ModelPerformance.from_dict(data[model_name])

        return self._model_performance.get(model_name)

    async def get_best_model_for_task(self, task_type: str) -> Optional[str]:
        """
        Get the best performing model for a task type.

        Args:
            task_type: Type of task (e.g., "code", "creative", "analysis")

        Returns:
            Name of the best model, or None if no data
        """
        # Load all performance data
        data = await self._get_memory_block(MemoryBlockType.MODEL_PERFORMANCE)
        if not data:
            return None

        best_model = None
        best_score = -1

        for model_name, perf_data in data.items():
            perf = ModelPerformance.from_dict(perf_data)
            if task_type in perf.recommended_tasks:
                # Score based on quality and latency
                quality = sum(perf.quality_scores) / len(perf.quality_scores) if perf.quality_scores else 0.5
                latency_score = 1 - min(perf.avg_latency_ms / 5000, 1)  # Normalize latency
                score = quality * 0.7 + latency_score * 0.3

                if score > best_score:
                    best_score = score
                    best_model = model_name

        return best_model

    async def _sync_model_performance(self) -> None:
        """Sync model performance to Letta memory."""
        data = {
            name: perf.to_dict()
            for name, perf in self._model_performance.items()
        }
        await self._update_memory_block(MemoryBlockType.MODEL_PERFORMANCE, data)

    # User Preference Methods

    async def learn_preference(
        self,
        category: str,
        preference: str,
        example: Optional[str] = None,
        confidence: float = 0.7
    ) -> None:
        """
        Learn a new user preference.

        Args:
            category: Preference category (e.g., "communication", "model", "formatting")
            preference: The preference itself
            example: Optional example that led to this learning
            confidence: Confidence in this preference (0-1)
        """
        key = f"{category}:{preference}"

        if key in self._user_preferences:
            # Reinforce existing preference
            pref = self._user_preferences[key]
            pref.confidence = min(pref.confidence + 0.1, 1.0)
            pref.last_confirmed = datetime.now()
            if example:
                pref.examples.append(example)
        else:
            # New preference
            self._user_preferences[key] = UserPreference(
                category=category,
                preference=preference,
                confidence=confidence,
                examples=[example] if example else []
            )

        await self._sync_user_preferences()

    async def get_preferences(self, category: Optional[str] = None) -> List[UserPreference]:
        """
        Get user preferences, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of user preferences
        """
        # Load from Letta if cache is empty
        if not self._user_preferences:
            data = await self._get_memory_block(MemoryBlockType.USER_PREFERENCES)
            if data:
                for key, pref_data in data.items():
                    self._user_preferences[key] = UserPreference(**pref_data)

        prefs = list(self._user_preferences.values())
        if category:
            prefs = [p for p in prefs if p.category == category]

        return sorted(prefs, key=lambda p: p.confidence, reverse=True)

    async def _sync_user_preferences(self) -> None:
        """Sync user preferences to Letta memory."""
        data = {
            f"{p.category}:{p.preference}": p.to_dict()
            for p in self._user_preferences.values()
        }
        await self._update_memory_block(MemoryBlockType.USER_PREFERENCES, data)

    # System Learning Methods

    async def record_learning(
        self,
        pattern: str,
        description: str,
        remediation: Optional[str] = None
    ) -> None:
        """
        Record a system behavior pattern learned from observation.

        Args:
            pattern: Pattern identifier (e.g., "gpu_oom_on_70b")
            description: Human-readable description
            remediation: Optional remediation steps
        """
        if pattern in self._system_learnings:
            learning = self._system_learnings[pattern]
            learning.frequency += 1
            learning.last_observed = datetime.now()
            learning.confidence = min(learning.confidence + 0.1, 1.0)
            if remediation:
                learning.remediation = remediation
        else:
            self._system_learnings[pattern] = SystemLearning(
                pattern=pattern,
                description=description,
                remediation=remediation
            )

        await self._sync_system_learnings()

    async def get_learnings(self, min_confidence: float = 0.0) -> List[SystemLearning]:
        """
        Get all system learnings above confidence threshold.

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            List of system learnings
        """
        if not self._system_learnings:
            data = await self._get_memory_block(MemoryBlockType.SYSTEM_LEARNINGS)
            if data:
                for pattern, learning_data in data.items():
                    learning_data["last_observed"] = datetime.fromisoformat(learning_data["last_observed"])
                    self._system_learnings[pattern] = SystemLearning(**learning_data)

        return [
            l for l in self._system_learnings.values()
            if l.confidence >= min_confidence
        ]

    async def get_remediation(self, pattern: str) -> Optional[str]:
        """Get remediation steps for a known pattern."""
        learning = self._system_learnings.get(pattern)
        if learning:
            return learning.remediation
        return None

    async def _sync_system_learnings(self) -> None:
        """Sync system learnings to Letta memory."""
        data = {
            l.pattern: l.to_dict()
            for l in self._system_learnings.values()
        }
        await self._update_memory_block(MemoryBlockType.SYSTEM_LEARNINGS, data)

    # Memory Consolidation

    async def consolidate_memories(self) -> Dict[str, Any]:
        """
        Consolidate and optimize memory blocks.

        - Prunes old/low-confidence data
        - Summarizes frequently accessed patterns
        - Computes aggregate statistics

        Returns:
            Consolidation report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "actions": []
        }

        # Prune old model performance data (>30 days unused)
        cutoff = datetime.now() - timedelta(days=30)
        pruned_models = []
        for name, perf in list(self._model_performance.items()):
            if perf.last_used and perf.last_used < cutoff:
                del self._model_performance[name]
                pruned_models.append(name)

        if pruned_models:
            report["actions"].append(f"Pruned {len(pruned_models)} unused models: {pruned_models}")

        # Decay low-confidence preferences
        decayed_prefs = []
        for key, pref in list(self._user_preferences.items()):
            if pref.confidence < 0.3:
                del self._user_preferences[key]
                decayed_prefs.append(key)
            elif pref.last_confirmed:
                days_since = (datetime.now() - pref.last_confirmed).days
                if days_since > 30:
                    pref.confidence *= 0.9  # Decay unconfirmed preferences

        if decayed_prefs:
            report["actions"].append(f"Removed {len(decayed_prefs)} low-confidence preferences")

        # Prune rare system learnings
        rare_learnings = []
        for pattern, learning in list(self._system_learnings.items()):
            if learning.frequency < 2 and learning.confidence < 0.5:
                del self._system_learnings[pattern]
                rare_learnings.append(pattern)

        if rare_learnings:
            report["actions"].append(f"Pruned {len(rare_learnings)} rare learnings")

        # Sync all changes
        await self._sync_model_performance()
        await self._sync_user_preferences()
        await self._sync_system_learnings()

        report["remaining"] = {
            "models": len(self._model_performance),
            "preferences": len(self._user_preferences),
            "learnings": len(self._system_learnings)
        }

        return report

    async def get_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all memory blocks.

        Returns:
            Summary with counts and highlights
        """
        return {
            "model_performance": {
                "count": len(self._model_performance),
                "models": list(self._model_performance.keys()),
                "total_requests": sum(p.total_requests for p in self._model_performance.values())
            },
            "user_preferences": {
                "count": len(self._user_preferences),
                "categories": list(set(p.category for p in self._user_preferences.values())),
                "high_confidence": len([p for p in self._user_preferences.values() if p.confidence > 0.8])
            },
            "system_learnings": {
                "count": len(self._system_learnings),
                "with_remediation": len([l for l in self._system_learnings.values() if l.remediation])
            }
        }


# Convenience function to create memory manager
def create_memory_manager(
    letta_url: str = "http://192.168.1.244:8283",
    agent_name: str = "hydra-steward"
) -> LettaMemoryManager:
    """Create a LettaMemoryManager instance."""
    return LettaMemoryManager(letta_url=letta_url, agent_name=agent_name)
