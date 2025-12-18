"""
Speculative Decoding Configuration and Management

Implements speculative decoding for 2-4x inference speedup on Hydra cluster.

Hardware Configuration:
- hydra-ai: RTX 5090 (32GB) + RTX 4090 (24GB) = 56GB total
- hydra-compute: 2x RTX 5070 Ti (16GB each) = 32GB total

Speculative Decoding Strategy:
- Main model: Qwen2.5-32B or smaller (fits in 56GB with draft)
- Draft model: Llama-3.2-1B or Qwen2.5-0.5B (fast, small)
- Target: 2-4x speedup on generation tasks

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Speculative Decoding Configuration
# =============================================================================

class DecodingMode(str, Enum):
    """Decoding mode selection."""
    STANDARD = "standard"          # Normal autoregressive decoding
    SPECULATIVE = "speculative"    # Speculative decoding with draft model
    ADAPTIVE = "adaptive"          # Auto-select based on task/load


@dataclass
class ModelPair:
    """A main+draft model pair for speculative decoding."""
    name: str
    main_model: str
    draft_model: str
    main_model_size_gb: float
    draft_model_size_gb: float
    expected_speedup: float
    vram_required_gb: float
    compatible_tasks: List[str]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Predefined model pairs for Hydra hardware
MODEL_PAIRS = {
    "qwen32b-llama1b": ModelPair(
        name="qwen32b-llama1b",
        main_model="Qwen2.5-32B-Instruct-exl2-4bpw",
        draft_model="Llama-3.2-1B-Instruct",
        main_model_size_gb=18.0,
        draft_model_size_gb=2.0,
        expected_speedup=2.5,
        vram_required_gb=35.0,
        compatible_tasks=["chat", "code", "reasoning"],
        notes="Best balance of speed and quality for general tasks"
    ),
    "qwen32b-qwen05b": ModelPair(
        name="qwen32b-qwen05b",
        main_model="Qwen2.5-32B-Instruct-exl2-4bpw",
        draft_model="Qwen2.5-0.5B-Instruct",
        main_model_size_gb=18.0,
        draft_model_size_gb=1.0,
        expected_speedup=3.0,
        vram_required_gb=32.0,
        compatible_tasks=["chat", "code"],
        notes="Same model family - better token alignment"
    ),
    "codestral-qwen05b": ModelPair(
        name="codestral-qwen05b",
        main_model="Codestral-22B-v0.1-exl2-4bpw",
        draft_model="Qwen2.5-0.5B-Instruct",
        main_model_size_gb=12.0,
        draft_model_size_gb=1.0,
        expected_speedup=2.8,
        vram_required_gb=20.0,
        compatible_tasks=["code"],
        notes="Optimized for code generation"
    ),
    "qwen14b-qwen05b": ModelPair(
        name="qwen14b-qwen05b",
        main_model="Qwen2.5-14B-Instruct-exl2-5bpw",
        draft_model="Qwen2.5-0.5B-Instruct",
        main_model_size_gb=10.0,
        draft_model_size_gb=1.0,
        expected_speedup=2.2,
        vram_required_gb=18.0,
        compatible_tasks=["chat", "code", "reasoning"],
        notes="Lighter option when VRAM constrained"
    ),
}


@dataclass
class SpeculativeConfig:
    """Configuration for speculative decoding."""
    enabled: bool = False
    mode: DecodingMode = DecodingMode.ADAPTIVE
    active_model_pair: Optional[str] = None
    num_speculative_tokens: int = 5  # Tokens to speculate per step
    temperature: float = 0.0         # Temperature for draft model (0 = greedy)
    min_speedup_threshold: float = 1.5  # Min speedup to use speculative
    fallback_to_standard: bool = True   # Fallback if speedup not achieved
    max_draft_cache_size_mb: int = 512  # Draft model KV cache size

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpeculativeConfig":
        data["mode"] = DecodingMode(data.get("mode", "adaptive"))
        return cls(**data)


# =============================================================================
# Benchmark Results
# =============================================================================

@dataclass
class SpeedupBenchmark:
    """Benchmark result for speculative decoding."""
    model_pair: str
    task_type: str
    input_tokens: int
    output_tokens: int
    standard_time_ms: float
    speculative_time_ms: float
    speedup: float
    acceptance_rate: float  # Percentage of speculated tokens accepted
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# Speculative Decoding Manager
# =============================================================================

class SpeculativeDecodingManager:
    """
    Manages speculative decoding configuration and optimization.

    Features:
    - Model pair management
    - Configuration persistence
    - Benchmark tracking
    - Automatic optimization
    """

    def __init__(
        self,
        data_dir: str = "/data/speculative",
        tabby_url: str = "http://192.168.1.250:5000",
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.data_dir / "config.json"
        self.benchmarks_file = self.data_dir / "benchmarks.json"
        self.tabby_url = tabby_url

        # Load configuration
        self.config = self._load_config()
        self.benchmarks: List[SpeedupBenchmark] = self._load_benchmarks()

    def _load_config(self) -> SpeculativeConfig:
        """Load configuration from disk."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                    return SpeculativeConfig.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load speculative config: {e}")
        return SpeculativeConfig()

    def _save_config(self):
        """Save configuration to disk."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save speculative config: {e}")

    def _load_benchmarks(self) -> List[SpeedupBenchmark]:
        """Load benchmark history."""
        if self.benchmarks_file.exists():
            try:
                with open(self.benchmarks_file) as f:
                    data = json.load(f)
                    return [SpeedupBenchmark(**b) for b in data]
            except Exception as e:
                logger.error(f"Failed to load benchmarks: {e}")
        return []

    def _save_benchmarks(self):
        """Save benchmark history."""
        try:
            with open(self.benchmarks_file, "w") as f:
                json.dump([b.to_dict() for b in self.benchmarks[-100:]], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save benchmarks: {e}")

    def get_model_pairs(self) -> List[Dict[str, Any]]:
        """Get all available model pairs."""
        return [mp.to_dict() for mp in MODEL_PAIRS.values()]

    def get_model_pair(self, name: str) -> Optional[ModelPair]:
        """Get a specific model pair."""
        return MODEL_PAIRS.get(name)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.config.to_dict()

    def update_config(
        self,
        enabled: Optional[bool] = None,
        mode: Optional[str] = None,
        model_pair: Optional[str] = None,
        num_speculative_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update speculative decoding configuration."""
        if enabled is not None:
            self.config.enabled = enabled
        if mode is not None:
            self.config.mode = DecodingMode(mode)
        if model_pair is not None:
            if model_pair not in MODEL_PAIRS:
                return {"error": f"Unknown model pair: {model_pair}"}
            self.config.active_model_pair = model_pair
        if num_speculative_tokens is not None:
            self.config.num_speculative_tokens = num_speculative_tokens

        self._save_config()
        logger.info(f"Updated speculative config: enabled={self.config.enabled}")
        return {"status": "updated", "config": self.config.to_dict()}

    def record_benchmark(
        self,
        model_pair: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        standard_time_ms: float,
        speculative_time_ms: float,
        acceptance_rate: float,
    ) -> SpeedupBenchmark:
        """Record a benchmark result."""
        speedup = standard_time_ms / speculative_time_ms if speculative_time_ms > 0 else 1.0

        benchmark = SpeedupBenchmark(
            model_pair=model_pair,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            standard_time_ms=standard_time_ms,
            speculative_time_ms=speculative_time_ms,
            speedup=speedup,
            acceptance_rate=acceptance_rate,
        )

        self.benchmarks.append(benchmark)
        self._save_benchmarks()

        logger.info(f"Recorded benchmark: {model_pair} - {speedup:.2f}x speedup")
        return benchmark

    def get_benchmarks(
        self,
        model_pair: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get benchmark history with optional filtering."""
        results = self.benchmarks

        if model_pair:
            results = [b for b in results if b.model_pair == model_pair]
        if task_type:
            results = [b for b in results if b.task_type == task_type]

        return [b.to_dict() for b in results[-limit:]]

    def get_average_speedup(
        self,
        model_pair: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get average speedup from benchmarks."""
        benchmarks = self.benchmarks

        if model_pair:
            benchmarks = [b for b in benchmarks if b.model_pair == model_pair]
        if task_type:
            benchmarks = [b for b in benchmarks if b.task_type == task_type]

        if not benchmarks:
            return {"average_speedup": 0, "sample_count": 0}

        avg_speedup = sum(b.speedup for b in benchmarks) / len(benchmarks)
        avg_acceptance = sum(b.acceptance_rate for b in benchmarks) / len(benchmarks)

        return {
            "average_speedup": round(avg_speedup, 2),
            "average_acceptance_rate": round(avg_acceptance, 3),
            "sample_count": len(benchmarks),
        }

    def recommend_model_pair(
        self,
        task_type: str,
        available_vram_gb: float,
    ) -> Dict[str, Any]:
        """Recommend a model pair based on task and available VRAM."""
        suitable_pairs = []

        for name, pair in MODEL_PAIRS.items():
            if pair.vram_required_gb <= available_vram_gb:
                if task_type in pair.compatible_tasks:
                    # Check historical performance
                    avg_data = self.get_average_speedup(model_pair=name, task_type=task_type)

                    suitable_pairs.append({
                        "name": name,
                        "pair": pair.to_dict(),
                        "historical_speedup": avg_data.get("average_speedup", pair.expected_speedup),
                        "sample_count": avg_data.get("sample_count", 0),
                    })

        # Sort by historical speedup (or expected if no history)
        suitable_pairs.sort(key=lambda x: x["historical_speedup"], reverse=True)

        if suitable_pairs:
            return {
                "recommendation": suitable_pairs[0]["name"],
                "expected_speedup": suitable_pairs[0]["historical_speedup"],
                "alternatives": suitable_pairs[1:],
            }

        return {
            "recommendation": None,
            "error": f"No model pairs fit in {available_vram_gb}GB VRAM for task '{task_type}'"
        }

    async def check_tabby_status(self) -> Dict[str, Any]:
        """Check TabbyAPI speculative decoding support."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Check model info
                response = await client.get(f"{self.tabby_url}/v1/model")
                if response.status_code == 200:
                    model_info = response.json()

                    # Check for draft model
                    draft_model = model_info.get("draft_model")

                    return {
                        "tabby_connected": True,
                        "main_model": model_info.get("id"),
                        "draft_model": draft_model,
                        "speculative_enabled": draft_model is not None,
                        "model_info": model_info,
                    }

        except Exception as e:
            logger.warning(f"TabbyAPI check failed: {e}")

        return {
            "tabby_connected": False,
            "speculative_enabled": False,
            "error": "Could not connect to TabbyAPI",
        }

    def get_hardware_status(self) -> Dict[str, Any]:
        """Get hardware status for speculative decoding planning."""
        return {
            "hydra_ai": {
                "gpus": ["RTX 5090 (32GB)", "RTX 4090 (24GB)"],
                "total_vram_gb": 56,
                "usable_vram_gb": 50,  # Leave overhead for system
                "notes": "Primary inference node",
            },
            "hydra_compute": {
                "gpus": ["RTX 5070 Ti (16GB)", "RTX 5070 Ti (16GB)"],
                "total_vram_gb": 32,
                "usable_vram_gb": 28,
                "notes": "Secondary inference, image generation",
            },
            "recommendations": {
                "best_pair_for_hydra_ai": "qwen32b-qwen05b",
                "best_pair_for_hydra_compute": "qwen14b-qwen05b",
                "exllamav3_status": "Monitoring for tensor parallel + speculative support",
            },
        }


# =============================================================================
# Global Instance
# =============================================================================

_manager: Optional[SpeculativeDecodingManager] = None


def get_speculative_manager() -> SpeculativeDecodingManager:
    """Get or create the global speculative decoding manager."""
    global _manager
    if _manager is None:
        _manager = SpeculativeDecodingManager()
    return _manager


# =============================================================================
# FastAPI Router
# =============================================================================

class ConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = None
    model_pair: Optional[str] = None
    num_speculative_tokens: Optional[int] = None


class BenchmarkRecordRequest(BaseModel):
    model_pair: str
    task_type: str
    input_tokens: int
    output_tokens: int
    standard_time_ms: float
    speculative_time_ms: float
    acceptance_rate: float


def create_speculative_router() -> APIRouter:
    """Create FastAPI router for speculative decoding endpoints."""
    router = APIRouter(prefix="/speculative", tags=["speculative-decoding"])

    @router.get("/config")
    async def get_config():
        """Get current speculative decoding configuration."""
        manager = get_speculative_manager()
        return manager.get_config()

    @router.post("/config")
    async def update_config(request: ConfigUpdateRequest):
        """Update speculative decoding configuration."""
        manager = get_speculative_manager()
        return manager.update_config(
            enabled=request.enabled,
            mode=request.mode,
            model_pair=request.model_pair,
            num_speculative_tokens=request.num_speculative_tokens,
        )

    @router.get("/model-pairs")
    async def get_model_pairs():
        """Get all available model pairs for speculative decoding."""
        manager = get_speculative_manager()
        return {"model_pairs": manager.get_model_pairs()}

    @router.get("/model-pairs/{name}")
    async def get_model_pair(name: str):
        """Get a specific model pair."""
        manager = get_speculative_manager()
        pair = manager.get_model_pair(name)
        if not pair:
            raise HTTPException(status_code=404, detail="Model pair not found")
        return pair.to_dict()

    @router.post("/benchmarks")
    async def record_benchmark(request: BenchmarkRecordRequest):
        """Record a speculative decoding benchmark result."""
        manager = get_speculative_manager()
        benchmark = manager.record_benchmark(
            model_pair=request.model_pair,
            task_type=request.task_type,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            standard_time_ms=request.standard_time_ms,
            speculative_time_ms=request.speculative_time_ms,
            acceptance_rate=request.acceptance_rate,
        )
        return benchmark.to_dict()

    @router.get("/benchmarks")
    async def get_benchmarks(
        model_pair: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
    ):
        """Get benchmark history."""
        manager = get_speculative_manager()
        return {
            "benchmarks": manager.get_benchmarks(model_pair, task_type, limit),
        }

    @router.get("/average-speedup")
    async def get_average_speedup(
        model_pair: Optional[str] = None,
        task_type: Optional[str] = None,
    ):
        """Get average speedup from benchmarks."""
        manager = get_speculative_manager()
        return manager.get_average_speedup(model_pair, task_type)

    @router.get("/recommend")
    async def recommend_model_pair(
        task_type: str,
        available_vram_gb: float = 50.0,
    ):
        """Get model pair recommendation based on task and VRAM."""
        manager = get_speculative_manager()
        return manager.recommend_model_pair(task_type, available_vram_gb)

    @router.get("/tabby-status")
    async def check_tabby():
        """Check TabbyAPI speculative decoding status."""
        manager = get_speculative_manager()
        return await manager.check_tabby_status()

    @router.get("/hardware")
    async def get_hardware_status():
        """Get hardware status and recommendations."""
        manager = get_speculative_manager()
        return manager.get_hardware_status()

    @router.get("/stats")
    async def get_stats():
        """Get overall speculative decoding statistics."""
        manager = get_speculative_manager()
        avg = manager.get_average_speedup()
        return {
            "config": manager.get_config(),
            "total_benchmarks": len(manager.benchmarks),
            "average_speedup": avg.get("average_speedup", 0),
            "average_acceptance_rate": avg.get("average_acceptance_rate", 0),
            "model_pairs_available": len(MODEL_PAIRS),
        }

    return router
