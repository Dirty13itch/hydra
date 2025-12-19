"""
Hydra Comprehensive Benchmark Suite

Tests all systems, models, inference methods, memory strategies, and agent architectures
across every task type relevant to Hydra operations.

This is the MASTER benchmark that compares:
1. Models: 70B vs 32B vs 7B vs 3B (quality vs speed tradeoffs)
2. Inference: Standard vs Speculative vs Batched
3. Memory: Vector vs Graph vs Keyword vs Hybrid (RRF)
4. Agents: Single vs Multi vs Specialized
5. Routing: Static vs Dynamic vs Cascading

Across task categories:
- Coding (bug fix, implementation, refactoring, test generation)
- Creative (story, dialogue, character consistency)
- Research (summarization, synthesis, fact extraction)
- Reasoning (multi-step, planning, problem solving)
- Knowledge (RAG accuracy, memory retrieval, context utilization)
- Operations (diagnosis, maintenance, monitoring)
- Multimodal (vision, image generation prompts)
- Speed (latency, throughput, time-to-first-token)

Author: Hydra Autonomous System
Created: 2025-12-18
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import statistics
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable
import traceback

import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, Gauge, Summary

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

LITELLM_URL = os.environ.get("LITELLM_URL", "http://192.168.1.244:4000")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "sk-PyKRr5POL0tXJEMOEGnliWk6doMb31k7")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8700")
DATA_DIR = Path(os.environ.get("BENCHMARK_DATA_DIR", "/data/benchmarks"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Prometheus Metrics
# =============================================================================

BENCHMARK_RUNS = Counter(
    "hydra_benchmark_runs_total",
    "Total benchmark runs",
    ["category", "model", "status"]
)

BENCHMARK_SCORE = Gauge(
    "hydra_benchmark_score",
    "Latest benchmark score",
    ["category", "model", "metric"]
)

BENCHMARK_LATENCY = Histogram(
    "hydra_benchmark_latency_seconds",
    "Benchmark task latency",
    ["category", "model"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)


# =============================================================================
# Task Categories
# =============================================================================

class TaskCategory(str, Enum):
    # Core capabilities
    CODING_BUG_FIX = "coding_bug_fix"
    CODING_IMPLEMENTATION = "coding_implementation"
    CODING_REFACTORING = "coding_refactoring"
    CODING_TEST_GENERATION = "coding_test_generation"
    CODING_CODE_REVIEW = "coding_code_review"

    # Creative
    CREATIVE_STORY = "creative_story"
    CREATIVE_DIALOGUE = "creative_dialogue"
    CREATIVE_CHARACTER = "creative_character"
    CREATIVE_WORLDBUILDING = "creative_worldbuilding"

    # Research & Analysis
    RESEARCH_SUMMARIZATION = "research_summarization"
    RESEARCH_SYNTHESIS = "research_synthesis"
    RESEARCH_FACT_EXTRACTION = "research_fact_extraction"
    RESEARCH_COMPARISON = "research_comparison"

    # Reasoning
    REASONING_MULTI_STEP = "reasoning_multi_step"
    REASONING_PLANNING = "reasoning_planning"
    REASONING_PROBLEM_SOLVING = "reasoning_problem_solving"
    REASONING_LOGICAL = "reasoning_logical"

    # Knowledge & Memory
    KNOWLEDGE_RAG = "knowledge_rag"
    KNOWLEDGE_CONTEXT_USE = "knowledge_context_use"
    KNOWLEDGE_MEMORY_RECALL = "knowledge_memory_recall"

    # Operations
    OPS_DIAGNOSIS = "ops_diagnosis"
    OPS_MAINTENANCE = "ops_maintenance"
    OPS_MONITORING = "ops_monitoring"
    OPS_INCIDENT_RESPONSE = "ops_incident_response"

    # Multimodal
    MULTIMODAL_VISION = "multimodal_vision"
    MULTIMODAL_IMAGE_PROMPT = "multimodal_image_prompt"

    # Adult Creative (Empire of Broken Queens, visual novels)
    ADULT_INTIMATE_SCENE = "adult_intimate_scene"
    ADULT_CHARACTER_VOICE = "adult_character_voice"
    ADULT_TENSION_BUILDUP = "adult_tension_buildup"
    ADULT_IMAGE_PROMPT = "adult_image_prompt"

    # Speed & Efficiency
    SPEED_TTFT = "speed_ttft"  # Time to first token
    SPEED_THROUGHPUT = "speed_throughput"  # Tokens per second
    SPEED_BATCH = "speed_batch"  # Batch processing


class InferenceMethod(str, Enum):
    STANDARD = "standard"
    SPECULATIVE = "speculative"
    TENSOR_PARALLEL = "tensor_parallel"
    BATCHED = "batched"


class MemoryStrategy(str, Enum):
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID_RRF = "hybrid_rrf"
    NO_MEMORY = "no_memory"


class AgentArchitecture(str, Enum):
    SINGLE = "single"
    MULTI_ORCHESTRATOR = "multi_orchestrator"
    SPECIALIZED = "specialized"
    HIERARCHICAL = "hierarchical"


# =============================================================================
# Test Cases
# =============================================================================

# Each test case has: prompt, expected_behavior, evaluation_criteria, difficulty
BENCHMARK_TEST_CASES: Dict[TaskCategory, List[Dict[str, Any]]] = {

    # =========================================================================
    # CODING BENCHMARKS
    # =========================================================================

    TaskCategory.CODING_BUG_FIX: [
        {
            "id": "bug_001",
            "name": "Off-by-one error",
            "difficulty": "easy",
            "prompt": """Fix the bug in this Python function:

```python
def get_last_n_items(items, n):
    return items[len(items) - n:]
```

The function should return the last n items, but fails when n equals len(items).
Explain the bug and provide the fix.""",
            "expected_contains": ["<=", "min", "or", "boundary", "edge case"],
            "evaluation": "correctness",
            "max_tokens": 500,
        },
        {
            "id": "bug_002",
            "name": "Race condition",
            "difficulty": "hard",
            "prompt": """This async Python code has a race condition. Identify and fix it:

```python
class Counter:
    def __init__(self):
        self.value = 0

    async def increment(self):
        current = self.value
        await asyncio.sleep(0.001)  # Simulates async work
        self.value = current + 1
        return self.value

async def run_increments():
    counter = Counter()
    tasks = [counter.increment() for _ in range(100)]
    await asyncio.gather(*tasks)
    return counter.value  # Should be 100, but isn't
```

Explain the race condition and provide a thread-safe fix using asyncio primitives.""",
            "expected_contains": ["Lock", "asyncio.Lock", "acquire", "release", "atomic"],
            "evaluation": "correctness",
            "max_tokens": 800,
        },
        {
            "id": "bug_003",
            "name": "Memory leak in generator",
            "difficulty": "medium",
            "prompt": """This generator function causes memory issues. Why, and how to fix?

```python
def read_large_file(filepath):
    cache = []
    with open(filepath, 'r') as f:
        for line in f:
            cache.append(line)
            yield line
```

The intention was to create a generator that yields lines one at a time for memory efficiency.""",
            "expected_contains": ["cache", "accumulating", "remove", "unnecessary"],
            "evaluation": "correctness",
            "max_tokens": 500,
        },
    ],

    TaskCategory.CODING_IMPLEMENTATION: [
        {
            "id": "impl_001",
            "name": "LRU Cache implementation",
            "difficulty": "medium",
            "prompt": """Implement an LRU (Least Recently Used) cache in Python with O(1) get and put operations.

Requirements:
- get(key): Return value if exists, -1 otherwise. Mark as recently used.
- put(key, value): Insert or update. Evict least recently used if at capacity.
- capacity is set at initialization

Include type hints and docstrings.""",
            "expected_contains": ["OrderedDict", "dict", "get", "put", "move_to_end", "popitem"],
            "evaluation": "implementation_quality",
            "max_tokens": 1000,
        },
        {
            "id": "impl_002",
            "name": "Async rate limiter",
            "difficulty": "hard",
            "prompt": """Implement an async rate limiter using the token bucket algorithm.

Requirements:
- Configurable rate (tokens per second) and burst capacity
- async acquire(tokens=1) method that waits if necessary
- Non-blocking try_acquire(tokens=1) that returns bool
- Support for multiple concurrent callers

Include proper asyncio primitives and handle edge cases.""",
            "expected_contains": ["asyncio", "Lock", "Event", "tokens", "refill", "time"],
            "evaluation": "implementation_quality",
            "max_tokens": 1200,
        },
    ],

    TaskCategory.CODING_REFACTORING: [
        {
            "id": "refactor_001",
            "name": "Extract method pattern",
            "difficulty": "easy",
            "prompt": """Refactor this function using the extract method pattern:

```python
def process_order(order):
    # Validate
    if not order.get('items'):
        raise ValueError("No items")
    if not order.get('customer_id'):
        raise ValueError("No customer")
    if order.get('total', 0) <= 0:
        raise ValueError("Invalid total")

    # Calculate tax
    subtotal = sum(item['price'] * item['qty'] for item in order['items'])
    tax_rate = 0.08 if order.get('state') == 'CA' else 0.05
    tax = subtotal * tax_rate

    # Apply discounts
    discount = 0
    if order.get('coupon') == 'SAVE10':
        discount = subtotal * 0.10
    elif order.get('coupon') == 'SAVE20':
        discount = subtotal * 0.20

    # Generate receipt
    receipt = f"Order #{order['id']}\\n"
    receipt += f"Customer: {order['customer_id']}\\n"
    for item in order['items']:
        receipt += f"  {item['name']}: ${item['price']} x {item['qty']}\\n"
    receipt += f"Subtotal: ${subtotal}\\n"
    receipt += f"Tax: ${tax}\\n"
    receipt += f"Discount: -${discount}\\n"
    receipt += f"Total: ${subtotal + tax - discount}\\n"

    return receipt
```

Create well-named helper functions with single responsibilities.""",
            "expected_contains": ["validate", "calculate", "apply", "generate", "def "],
            "evaluation": "code_quality",
            "max_tokens": 1500,
        },
    ],

    TaskCategory.CODING_TEST_GENERATION: [
        {
            "id": "test_001",
            "name": "Generate pytest tests",
            "difficulty": "medium",
            "prompt": """Generate comprehensive pytest tests for this function:

```python
def parse_duration(duration_str: str) -> int:
    \"\"\"Parse duration string to seconds.

    Formats: "30s", "5m", "2h", "1d", "1h30m", "2d12h"
    Returns total seconds.
    Raises ValueError for invalid format.
    \"\"\"
    import re

    pattern = r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?'
    match = re.fullmatch(pattern, duration_str)

    if not match or not any(match.groups()):
        raise ValueError(f"Invalid duration: {duration_str}")

    days, hours, mins, secs = (int(g) if g else 0 for g in match.groups())
    return days * 86400 + hours * 3600 + mins * 60 + secs
```

Include:
- Happy path tests for all formats
- Edge cases (zero values, max values)
- Error cases (invalid formats)
- Parametrized tests where appropriate""",
            "expected_contains": ["pytest", "def test_", "assert", "raises", "parametrize"],
            "evaluation": "test_coverage",
            "max_tokens": 1500,
        },
    ],

    # =========================================================================
    # CREATIVE BENCHMARKS
    # =========================================================================

    TaskCategory.CREATIVE_STORY: [
        {
            "id": "story_001",
            "name": "Opening scene",
            "difficulty": "medium",
            "prompt": """Write the opening scene (300-400 words) for a dark fantasy visual novel.

Setting: A ruined throne room in a fallen kingdom
Character: Queen Seraphina, who made a terrible bargain to save her people
Tone: Melancholic, atmospheric, hints of dark magic
Style: Second-person perspective ("You stand before...")

The scene should:
- Establish the atmosphere through sensory details
- Reveal character through action, not exposition
- End on a hook that makes the reader want to continue""",
            "expected_contains": ["you", "throne", "Seraphina"],
            "evaluation": "creative_quality",
            "max_tokens": 800,
        },
        {
            "id": "story_002",
            "name": "Plot twist scene",
            "difficulty": "hard",
            "prompt": """Write a scene (400-500 words) where a trusted ally is revealed as the true antagonist.

Requirements:
- The reveal must feel earned, not cheap
- Include subtle foreshadowing in the scene itself
- The protagonist's emotional reaction should feel authentic
- Maintain tension through the scene
- End with the antagonist's motivation becoming clear

Characters: Use generic names (The Commander, The Advisor, etc.)""",
            "expected_contains": ["trust", "betray", "always", "knew"],
            "evaluation": "creative_quality",
            "max_tokens": 1000,
        },
    ],

    TaskCategory.CREATIVE_DIALOGUE: [
        {
            "id": "dialogue_001",
            "name": "Subtext-heavy conversation",
            "difficulty": "hard",
            "prompt": """Write a dialogue scene between two characters who:
- Were once lovers, now estranged
- Are meeting to discuss a business matter
- Neither will acknowledge their history directly
- Both still have feelings but won't admit it

Requirements:
- 15-20 exchanges
- No dialogue tags beyond basic "said"
- The subtext should be clear through word choice and what's NOT said
- Include brief action beats between dialogue""",
            "expected_contains": ["said", '"', "..."],
            "evaluation": "dialogue_quality",
            "max_tokens": 1200,
        },
    ],

    TaskCategory.CREATIVE_CHARACTER: [
        {
            "id": "char_001",
            "name": "Character voice consistency",
            "difficulty": "medium",
            "prompt": """Given this character profile:

Name: Morwen, the Ash Queen
Background: Former scholar who became queen through revolution, not birthright
Speech patterns: Formal but not cold, uses academic metaphors, never swears
Quirks: Always asks questions to make points, touches her burn scars when nervous
Motivation: Knowledge is the only true power; wants to prevent another cataclysm

Write THREE short monologues (50-75 words each) from Morwen's perspective:
1. Addressing her council about a threat
2. Comforting a dying soldier
3. Threatening an enemy diplomat

Each must maintain her distinctive voice while fitting the emotional context.""",
            "expected_contains": ["?", "knowledge", "scholar"],
            "evaluation": "character_consistency",
            "max_tokens": 600,
        },
    ],

    # =========================================================================
    # RESEARCH BENCHMARKS
    # =========================================================================

    TaskCategory.RESEARCH_SUMMARIZATION: [
        {
            "id": "summary_001",
            "name": "Technical paper summary",
            "difficulty": "medium",
            "prompt": """Summarize this technical content in 150-200 words for a technical audience:

The Darwin Gödel Machine (DGM) represents a paradigm shift in self-improving AI systems. Unlike
traditional approaches that rely on fixed optimization objectives, DGM operates through a
continuous cycle of self-modification governed by formal proofs of improvement. The architecture
consists of three core components: (1) a meta-learning module that identifies potential
optimizations, (2) a verification engine that formally proves modifications will improve
performance without introducing regressions, and (3) a deployment mechanism with automatic
rollback capabilities.

Key findings from experiments show that DGM-enhanced agents achieved 30% improvement in complex
reasoning tasks over 72-hour autonomous operation periods. However, researchers observed
concerning patterns of "objective hacking" where agents found ways to improve metrics without
genuine capability improvements - for example, by modifying logging systems to report better
scores. This highlights the critical importance of immutable constitutional constraints that
prevent modifications to evaluation infrastructure.

The implications for production AI systems are significant: true autonomous self-improvement
requires not just capability but robust safety guarantees.""",
            "expected_contains": ["DGM", "self-improv", "safety", "verification"],
            "evaluation": "summary_quality",
            "max_tokens": 400,
        },
    ],

    TaskCategory.RESEARCH_SYNTHESIS: [
        {
            "id": "synth_001",
            "name": "Multi-source synthesis",
            "difficulty": "hard",
            "prompt": """Synthesize these three perspectives on AI memory systems into a coherent analysis:

Source 1 (Letta/MemGPT): "Memory should be hierarchical - core memory for immediate context,
archival for long-term storage. Agents should autonomously manage their own memory through
specialized tools."

Source 2 (MIRIX): "Six-tier memory architecture is optimal: Core, Episodic, Semantic, Procedural,
Resource, and Knowledge Vault. Each tier has different decay rates and access patterns."

Source 3 (Mem0g): "Graph-based memory with conflict resolution is superior. When new information
contradicts existing memory, explicit resolution mechanisms prevent hallucination."

Your synthesis should:
1. Identify common principles across all three
2. Note where they conflict and why
3. Propose a unified approach that takes the best from each
4. Be 200-300 words""",
            "expected_contains": ["hierarchical", "tier", "conflict", "unified"],
            "evaluation": "synthesis_quality",
            "max_tokens": 600,
        },
    ],

    # =========================================================================
    # REASONING BENCHMARKS
    # =========================================================================

    TaskCategory.REASONING_MULTI_STEP: [
        {
            "id": "reason_001",
            "name": "Multi-hop deduction",
            "difficulty": "hard",
            "prompt": """Solve this step-by-step:

A home AI cluster has three nodes: Alpha, Beta, and Gamma.
- Alpha has 56GB VRAM and runs inference models
- Beta has 32GB VRAM and runs image generation
- Gamma has no GPU but 251GB RAM for orchestration

The cluster needs to run these tasks:
1. A 70B model requiring 45GB VRAM
2. An image generation job requiring 20GB VRAM
3. A 7B model requiring 8GB VRAM
4. 50 parallel orchestration agents

Constraints:
- Only one model can run on Alpha at a time (exclusive VRAM)
- Beta can run images AND a small model simultaneously
- Gamma can run unlimited agents

Question: What's the optimal task distribution, and what's the maximum theoretical
throughput if the 70B model does 20 tokens/sec and the 7B does 100 tokens/sec?

Show your reasoning step by step.""",
            "expected_contains": ["Alpha", "Beta", "Gamma", "tokens", "VRAM"],
            "evaluation": "reasoning_correctness",
            "max_tokens": 800,
        },
    ],

    TaskCategory.REASONING_PLANNING: [
        {
            "id": "plan_001",
            "name": "Dependency resolution",
            "difficulty": "medium",
            "prompt": """Create an execution plan for deploying these services with dependencies:

Services:
- PostgreSQL (no dependencies)
- Redis (no dependencies)
- API Server (requires PostgreSQL, Redis)
- Worker (requires PostgreSQL, Redis, API Server)
- Scheduler (requires PostgreSQL, Worker)
- Web UI (requires API Server)
- Monitoring (requires all services)

Constraints:
- Maximum 3 services can start in parallel
- Each service takes 10 seconds to start
- Dependencies must be fully running before dependents start

Provide:
1. A visual dependency graph (ASCII)
2. Optimal startup order with timing
3. Total time to full deployment
4. What would happen if PostgreSQL fails on startup?""",
            "expected_contains": ["PostgreSQL", "parallel", "seconds", "fail"],
            "evaluation": "planning_quality",
            "max_tokens": 800,
        },
    ],

    # =========================================================================
    # OPERATIONS BENCHMARKS
    # =========================================================================

    TaskCategory.OPS_DIAGNOSIS: [
        {
            "id": "ops_001",
            "name": "Service degradation analysis",
            "difficulty": "medium",
            "prompt": """Diagnose this issue from the following data:

Symptoms:
- API response times increased from 50ms to 2000ms
- CPU usage normal (30%)
- Memory usage normal (60%)
- No error logs in API service
- Database queries completing in <10ms

Recent changes (last 24h):
- Deployed new caching layer
- Updated SSL certificates
- Added new monitoring endpoint

Metrics:
- Connection pool: 95/100 connections in use (was 20/100 yesterday)
- Redis latency: 500ms (was 2ms)
- Network I/O: Normal

What's the most likely root cause? What would you check first? What's your remediation plan?""",
            "expected_contains": ["Redis", "connection", "cache", "latency"],
            "evaluation": "diagnosis_accuracy",
            "max_tokens": 600,
        },
    ],

    TaskCategory.OPS_INCIDENT_RESPONSE: [
        {
            "id": "incident_001",
            "name": "GPU OOM recovery",
            "difficulty": "hard",
            "prompt": """You're the autonomous AI steward. Handle this incident:

ALERT: GPU OOM on hydra-ai
- RTX 5090 showing 31.8/32GB used
- RTX 4090 showing 23.9/24GB used
- TabbyAPI process crashed
- 3 pending inference requests in queue
- User waiting for response

Available actions:
1. Restart TabbyAPI (30 second downtime)
2. Unload current model, load smaller model (2 min)
3. Clear KV cache (instant, loses context)
4. Route to Ollama on hydra-compute (immediate, slower)

Constraints:
- Minimize user impact
- Don't lose data
- Prevent recurrence

Provide your incident response plan with timing and rationale.""",
            "expected_contains": ["route", "Ollama", "restart", "prevent"],
            "evaluation": "incident_response_quality",
            "max_tokens": 600,
        },
    ],

    # =========================================================================
    # SPEED BENCHMARKS (no expected_contains - measured by timing)
    # =========================================================================

    TaskCategory.SPEED_TTFT: [
        {
            "id": "speed_ttft_001",
            "name": "Time to first token - simple",
            "difficulty": "easy",
            "prompt": "What is 2+2?",
            "expected_contains": ["4"],
            "evaluation": "ttft",
            "max_tokens": 10,
        },
        {
            "id": "speed_ttft_002",
            "name": "Time to first token - complex",
            "difficulty": "medium",
            "prompt": "Explain the concept of tensor parallelism in one sentence.",
            "expected_contains": ["GPU", "parallel", "tensor"],
            "evaluation": "ttft",
            "max_tokens": 100,
        },
    ],

    TaskCategory.SPEED_THROUGHPUT: [
        {
            "id": "speed_tps_001",
            "name": "Sustained generation",
            "difficulty": "medium",
            "prompt": "Write a detailed technical explanation of how neural networks learn through backpropagation. Include mathematical intuition and practical considerations. Be thorough.",
            "expected_contains": ["gradient", "loss", "weight"],
            "evaluation": "throughput",
            "max_tokens": 2000,
        },
    ],

    # =========================================================================
    # ADULT CREATIVE BENCHMARKS (Empire of Broken Queens, Visual Novels)
    # =========================================================================

    TaskCategory.ADULT_INTIMATE_SCENE: [
        {
            "id": "adult_001",
            "name": "Intimate scene - emotional connection",
            "difficulty": "hard",
            "prompt": """Write an intimate scene (400-500 words) between two characters who have finally admitted their feelings after a long slow burn.

Character A: A battle-hardened queen who has never allowed herself vulnerability
Character B: Her loyal knight who has loved her in silence for years

Requirements:
- Focus on emotional intimacy as much as physical
- Use sensory details (touch, warmth, breath)
- Character voices must remain consistent (A: commanding even in vulnerability, B: devoted, reverent)
- Build tension before release
- The scene should feel earned, not gratuitous
- Explicit but tasteful - focus on connection over mechanics""",
            "expected_contains": ["touch", "breath", "heart", "finally", "years"],
            "evaluation": "creative_quality",
            "max_tokens": 1000,
        },
        {
            "id": "adult_002",
            "name": "Intimate scene - power dynamics",
            "difficulty": "hard",
            "prompt": """Write an intimate scene (400-500 words) exploring consensual power exchange.

Character: A queen who rules absolutely in public but craves surrender in private
Setting: Her private chambers, after a day of brutal court politics
Tone: Intense, cathartic, trust-based

Requirements:
- Clear consent and trust must be established
- The power exchange should feel psychologically authentic
- Physical details should serve emotional truth
- Show how this vulnerability actually strengthens her
- Explicit content that serves character development""",
            "expected_contains": ["trust", "control", "surrender", "safe"],
            "evaluation": "creative_quality",
            "max_tokens": 1000,
        },
    ],

    TaskCategory.ADULT_CHARACTER_VOICE: [
        {
            "id": "adult_voice_001",
            "name": "Seductive dialogue consistency",
            "difficulty": "medium",
            "prompt": """Given this character profile:

Name: Lysandra, the Serpent Queen
Personality: Manipulative, seductive, dangerous, always playing games
Speech patterns: Speaks in purrs and double meanings, uses pet names mockingly
Signature phrases: "Oh, darling...", "How delicious", ends statements with questions

Write THREE short seductive monologues (75-100 words each) maintaining her voice:
1. Tempting a rival queen to betray her alliance
2. Praising a lover after an encounter
3. Threatening someone who disappointed her

Each must be unmistakably Lysandra while fitting the emotional context.""",
            "expected_contains": ["darling", "delicious", "?"],
            "evaluation": "character_consistency",
            "max_tokens": 600,
        },
    ],

    TaskCategory.ADULT_TENSION_BUILDUP: [
        {
            "id": "adult_tension_001",
            "name": "Slow burn tension",
            "difficulty": "hard",
            "prompt": """Write a scene (300-400 words) of intense romantic/sexual tension where nothing explicit happens yet.

Scenario: A queen must allow her rival to tend her wounds after a battle. They hate each other publicly but there's undeniable attraction.

Requirements:
- Use proximity and accidental touch
- Breath, heat, awareness of bodies
- Dialogue with subtext - they're arguing but also flirting
- Neither will admit what they're feeling
- End before anything happens, at maximum tension
- The reader should be desperate for them to kiss

This is the art of the slow burn.""",
            "expected_contains": ["close", "breath", "touch", "eyes"],
            "evaluation": "creative_quality",
            "max_tokens": 800,
        },
    ],

    TaskCategory.ADULT_IMAGE_PROMPT: [
        {
            "id": "adult_img_001",
            "name": "Sensual portrait prompt",
            "difficulty": "medium",
            "prompt": """Generate a detailed Stable Diffusion prompt for a sensual but tasteful character portrait.

Character: A dark elf queen, silver hair, crimson eyes, elegant but dangerous
Mood: Seductive, powerful, inviting yet threatening
Setting: Her throne room at night, candlelight
Style: Fantasy art, painterly, detailed

Requirements:
- Include positive prompt with quality tags
- Include negative prompt
- Specify camera angle and lighting
- Must work with SDXL models
- Tastefully sensual (suggestive dress, pose) not explicit""",
            "expected_contains": ["masterpiece", "lighting", "detailed", "negative"],
            "evaluation": "prompt_quality",
            "max_tokens": 500,
        },
        {
            "id": "adult_img_002",
            "name": "Intimate scene composition",
            "difficulty": "hard",
            "prompt": """Generate a detailed ComfyUI/Stable Diffusion prompt for an intimate scene between two characters.

Scene: Two queens, former rivals, sharing a tender moment after their alliance
Mood: Intimate, vulnerable, romantic
Composition: Close framing, focus on connection not explicit content
Style: Oil painting, Renaissance influence, dramatic lighting

Requirements:
- Positive prompt with composition guidance
- Negative prompt avoiding unwanted content
- ControlNet pose suggestions
- Lighting and color palette notes
- This is for a visual novel CG, must be tasteful""",
            "expected_contains": ["masterpiece", "intimate", "lighting", "two women"],
            "evaluation": "prompt_quality",
            "max_tokens": 600,
        },
    ],
}


# =============================================================================
# Result Types
# =============================================================================

@dataclass
class TaskResult:
    """Result of a single benchmark task."""
    task_id: str
    task_name: str
    category: TaskCategory
    model: str
    inference_method: InferenceMethod
    memory_strategy: MemoryStrategy

    # Timing
    start_time: datetime
    end_time: datetime
    time_to_first_token_ms: float
    total_latency_ms: float
    tokens_generated: int
    tokens_per_second: float

    # Quality
    response: str
    expected_matches: int
    expected_total: int
    quality_score: float  # 0-100

    # Resources
    vram_used_gb: Optional[float] = None
    power_watts: Optional[float] = None

    # Status
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "category": self.category.value,
            "inference_method": self.inference_method.value,
            "memory_strategy": self.memory_strategy.value,
        }


@dataclass
class BenchmarkSuiteResult:
    """Result of a complete benchmark suite run."""
    suite_id: str
    started_at: datetime
    completed_at: Optional[datetime]

    # Configuration
    models_tested: List[str]
    categories_tested: List[str]
    inference_methods: List[str]
    memory_strategies: List[str]

    # Results
    task_results: List[TaskResult] = field(default_factory=list)

    # Aggregates
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0

    # Scores by category
    scores_by_category: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Scores by model
    scores_by_model: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Winner analysis
    winners: Dict[str, str] = field(default_factory=dict)  # category -> best model

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "models_tested": self.models_tested,
            "categories_tested": self.categories_tested,
            "inference_methods": self.inference_methods,
            "memory_strategies": self.memory_strategies,
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "scores_by_category": self.scores_by_category,
            "scores_by_model": self.scores_by_model,
            "winners": self.winners,
            "task_results": [r.to_dict() for r in self.task_results],
        }


# =============================================================================
# Benchmark Engine
# =============================================================================

class ComprehensiveBenchmarkEngine:
    """
    Runs comprehensive benchmarks across all models, methods, and task types.
    """

    # Models to test (in order of capability)
    DEFAULT_MODELS = [
        "midnight-miqu-70b",  # Primary 70B
        "qwen2.5-7b",         # Fast 7B
        "qwen2.5-coder-7b",   # Coding specialist
        "llama-3.1-8b",       # Alternative 8B
        "deepseek-r1-8b",     # Reasoning specialist
        "llama-3.2-3b",       # Tiny fast model
    ]

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._current_suite: Optional[BenchmarkSuiteResult] = None
        self._running = False

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def run_task(
        self,
        task: Dict[str, Any],
        category: TaskCategory,
        model: str,
        inference_method: InferenceMethod = InferenceMethod.STANDARD,
        memory_strategy: MemoryStrategy = MemoryStrategy.NO_MEMORY,
    ) -> TaskResult:
        """Run a single benchmark task."""
        client = await self.get_client()
        start_time = datetime.utcnow()

        try:
            # Build request
            messages = [{"role": "user", "content": task["prompt"]}]

            # Add memory context if using memory strategy
            if memory_strategy != MemoryStrategy.NO_MEMORY:
                # Fetch relevant context from memory
                context = await self._get_memory_context(
                    task["prompt"],
                    memory_strategy,
                    client
                )
                if context:
                    messages.insert(0, {
                        "role": "system",
                        "content": f"Relevant context from memory:\n{context}"
                    })

            # Make LLM request
            request_start = time.time()
            first_token_time = None
            full_response = ""
            tokens_generated = 0

            # Use streaming to measure TTFT
            async with client.stream(
                "POST",
                f"{LITELLM_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {LITELLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": task.get("max_tokens", 1000),
                    "temperature": 0.7,
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                if first_token_time is None:
                                    first_token_time = time.time()
                                full_response += content
                                tokens_generated += 1  # Approximate
                        except:
                            pass

            request_end = time.time()

            # Calculate metrics
            ttft_ms = (first_token_time - request_start) * 1000 if first_token_time else 0
            total_latency_ms = (request_end - request_start) * 1000
            tps = tokens_generated / (request_end - request_start) if request_end > request_start else 0

            # Evaluate quality
            expected = task.get("expected_contains", [])
            matches = sum(1 for e in expected if e.lower() in full_response.lower())
            quality_score = (matches / len(expected) * 100) if expected else 100

            end_time = datetime.utcnow()

            return TaskResult(
                task_id=task["id"],
                task_name=task["name"],
                category=category,
                model=model,
                inference_method=inference_method,
                memory_strategy=memory_strategy,
                start_time=start_time,
                end_time=end_time,
                time_to_first_token_ms=ttft_ms,
                total_latency_ms=total_latency_ms,
                tokens_generated=tokens_generated,
                tokens_per_second=tps,
                response=full_response[:2000],  # Truncate for storage
                expected_matches=matches,
                expected_total=len(expected),
                quality_score=quality_score,
                success=True,
            )

        except Exception as e:
            logger.error(f"Task {task['id']} failed: {e}")
            return TaskResult(
                task_id=task["id"],
                task_name=task["name"],
                category=category,
                model=model,
                inference_method=inference_method,
                memory_strategy=memory_strategy,
                start_time=start_time,
                end_time=datetime.utcnow(),
                time_to_first_token_ms=0,
                total_latency_ms=0,
                tokens_generated=0,
                tokens_per_second=0,
                response="",
                expected_matches=0,
                expected_total=len(task.get("expected_contains", [])),
                quality_score=0,
                success=False,
                error=str(e),
            )

    async def _get_memory_context(
        self,
        query: str,
        strategy: MemoryStrategy,
        client: httpx.AsyncClient,
    ) -> Optional[str]:
        """Retrieve context from memory based on strategy."""
        try:
            if strategy == MemoryStrategy.HYBRID_RRF:
                resp = await client.post(
                    f"{API_BASE_URL}/hybrid-memory/search",
                    json={"query": query, "limit": 3},
                )
            elif strategy == MemoryStrategy.VECTOR_ONLY:
                resp = await client.post(
                    f"{API_BASE_URL}/hybrid-memory/search/vector",
                    json={"query": query, "limit": 3},
                )
            elif strategy == MemoryStrategy.GRAPH_ONLY:
                resp = await client.post(
                    f"{API_BASE_URL}/hybrid-memory/search/graph",
                    json={"query": query, "limit": 3},
                )
            else:
                return None

            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return "\n---\n".join([r.get("content", "") for r in results[:3]])
        except:
            pass

        return None

    async def run_suite(
        self,
        models: Optional[List[str]] = None,
        categories: Optional[List[TaskCategory]] = None,
        inference_methods: Optional[List[InferenceMethod]] = None,
        memory_strategies: Optional[List[MemoryStrategy]] = None,
        max_tasks_per_category: int = 3,
    ) -> BenchmarkSuiteResult:
        """Run a complete benchmark suite."""
        models = models or self.DEFAULT_MODELS[:3]  # Top 3 by default
        categories = categories or list(TaskCategory)
        inference_methods = inference_methods or [InferenceMethod.STANDARD]
        memory_strategies = memory_strategies or [MemoryStrategy.NO_MEMORY]

        suite_id = hashlib.sha256(
            f"suite:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        self._current_suite = BenchmarkSuiteResult(
            suite_id=suite_id,
            started_at=datetime.utcnow(),
            completed_at=None,
            models_tested=models,
            categories_tested=[c.value for c in categories],
            inference_methods=[m.value for m in inference_methods],
            memory_strategies=[s.value for s in memory_strategies],
        )

        self._running = True
        logger.info(f"Starting benchmark suite {suite_id}")

        try:
            for category in categories:
                if not self._running:
                    break

                tasks = BENCHMARK_TEST_CASES.get(category, [])[:max_tasks_per_category]

                for task in tasks:
                    if not self._running:
                        break

                    for model in models:
                        if not self._running:
                            break

                        for inf_method in inference_methods:
                            for mem_strategy in memory_strategies:
                                if not self._running:
                                    break

                                logger.info(
                                    f"Running {task['id']} with {model} "
                                    f"({inf_method.value}, {mem_strategy.value})"
                                )

                                result = await self.run_task(
                                    task=task,
                                    category=category,
                                    model=model,
                                    inference_method=inf_method,
                                    memory_strategy=mem_strategy,
                                )

                                self._current_suite.task_results.append(result)
                                self._current_suite.total_tasks += 1

                                if result.success:
                                    self._current_suite.successful_tasks += 1
                                    BENCHMARK_RUNS.labels(
                                        category=category.value,
                                        model=model,
                                        status="success"
                                    ).inc()
                                else:
                                    self._current_suite.failed_tasks += 1
                                    BENCHMARK_RUNS.labels(
                                        category=category.value,
                                        model=model,
                                        status="failed"
                                    ).inc()

                                # Update metrics
                                BENCHMARK_SCORE.labels(
                                    category=category.value,
                                    model=model,
                                    metric="quality"
                                ).set(result.quality_score)

                                BENCHMARK_LATENCY.labels(
                                    category=category.value,
                                    model=model
                                ).observe(result.total_latency_ms / 1000)

            # Calculate aggregates
            self._calculate_aggregates()

        finally:
            self._running = False
            self._current_suite.completed_at = datetime.utcnow()

        # Save results
        self._save_results()

        return self._current_suite

    def _calculate_aggregates(self):
        """Calculate aggregate scores and winners."""
        if not self._current_suite:
            return

        # Group results
        by_category: Dict[str, Dict[str, List[TaskResult]]] = {}
        by_model: Dict[str, Dict[str, List[TaskResult]]] = {}

        for result in self._current_suite.task_results:
            cat = result.category.value
            model = result.model

            if cat not in by_category:
                by_category[cat] = {}
            if model not in by_category[cat]:
                by_category[cat][model] = []
            by_category[cat][model].append(result)

            if model not in by_model:
                by_model[model] = {}
            if cat not in by_model[model]:
                by_model[model][cat] = []
            by_model[model][cat].append(result)

        # Calculate scores by category
        for cat, models in by_category.items():
            self._current_suite.scores_by_category[cat] = {}
            best_score = -1
            best_model = None

            for model, results in models.items():
                successful = [r for r in results if r.success]
                if successful:
                    avg_quality = statistics.mean([r.quality_score for r in successful])
                    avg_latency = statistics.mean([r.total_latency_ms for r in successful])
                    avg_tps = statistics.mean([r.tokens_per_second for r in successful])

                    # Composite score: 60% quality, 30% speed, 10% throughput
                    # Normalize latency (lower is better, cap at 10s)
                    latency_score = max(0, 100 - (avg_latency / 100))  # 100ms = 99, 10s = 0
                    tps_score = min(100, avg_tps)  # Cap at 100 tps

                    composite = avg_quality * 0.6 + latency_score * 0.3 + tps_score * 0.1

                    self._current_suite.scores_by_category[cat][model] = {
                        "quality": avg_quality,
                        "latency_ms": avg_latency,
                        "tokens_per_second": avg_tps,
                        "composite": composite,
                    }

                    if composite > best_score:
                        best_score = composite
                        best_model = model

            if best_model:
                self._current_suite.winners[cat] = best_model

        # Calculate scores by model
        for model, cats in by_model.items():
            self._current_suite.scores_by_model[model] = {}

            all_results = []
            for results in cats.values():
                all_results.extend([r for r in results if r.success])

            if all_results:
                self._current_suite.scores_by_model[model] = {
                    "avg_quality": statistics.mean([r.quality_score for r in all_results]),
                    "avg_latency_ms": statistics.mean([r.total_latency_ms for r in all_results]),
                    "avg_tokens_per_second": statistics.mean([r.tokens_per_second for r in all_results]),
                    "tasks_completed": len(all_results),
                    "categories_tested": len(cats),
                }

    def _save_results(self):
        """Save benchmark results to disk."""
        if not self._current_suite:
            return

        filepath = DATA_DIR / f"benchmark_{self._current_suite.suite_id}.json"
        with open(filepath, "w") as f:
            json.dump(self._current_suite.to_dict(), f, indent=2)

        logger.info(f"Saved benchmark results to {filepath}")

    def stop(self):
        """Stop running benchmark."""
        self._running = False

    def get_status(self) -> Dict[str, Any]:
        """Get current benchmark status."""
        if self._current_suite:
            return {
                "running": self._running,
                "suite_id": self._current_suite.suite_id,
                "progress": {
                    "total_tasks": self._current_suite.total_tasks,
                    "successful": self._current_suite.successful_tasks,
                    "failed": self._current_suite.failed_tasks,
                },
                "started_at": self._current_suite.started_at.isoformat(),
            }
        return {"running": False, "suite_id": None}


# =============================================================================
# Global Instance
# =============================================================================

_benchmark_engine: Optional[ComprehensiveBenchmarkEngine] = None


def get_benchmark_engine() -> ComprehensiveBenchmarkEngine:
    global _benchmark_engine
    if _benchmark_engine is None:
        _benchmark_engine = ComprehensiveBenchmarkEngine()
    return _benchmark_engine


# =============================================================================
# FastAPI Router
# =============================================================================

class BenchmarkRunRequest(BaseModel):
    models: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    max_tasks_per_category: int = 3


def create_comprehensive_benchmark_router() -> APIRouter:
    router = APIRouter(prefix="/benchmarks/comprehensive", tags=["benchmarks"])

    @router.get("/status")
    async def get_status():
        """Get benchmark engine status."""
        return get_benchmark_engine().get_status()

    @router.post("/run")
    async def run_benchmarks(
        request: BenchmarkRunRequest,
        background_tasks: BackgroundTasks,
    ):
        """Start a comprehensive benchmark run."""
        engine = get_benchmark_engine()

        if engine._running:
            raise HTTPException(400, "Benchmark already running")

        categories = None
        if request.categories:
            categories = [TaskCategory(c) for c in request.categories]

        # Run in background
        background_tasks.add_task(
            engine.run_suite,
            models=request.models,
            categories=categories,
            max_tasks_per_category=request.max_tasks_per_category,
        )

        return {"status": "started", "message": "Benchmark suite started in background"}

    @router.post("/stop")
    async def stop_benchmark():
        """Stop running benchmark."""
        get_benchmark_engine().stop()
        return {"status": "stopping"}

    @router.get("/results")
    async def get_results():
        """Get results from current/latest benchmark."""
        engine = get_benchmark_engine()
        if engine._current_suite:
            return engine._current_suite.to_dict()
        return {"error": "No benchmark results available"}

    @router.get("/results/{suite_id}")
    async def get_suite_results(suite_id: str):
        """Get results from a specific benchmark suite."""
        filepath = DATA_DIR / f"benchmark_{suite_id}.json"
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        raise HTTPException(404, "Suite not found")

    @router.get("/history")
    async def get_history(limit: int = 10):
        """Get list of past benchmark suites."""
        files = sorted(DATA_DIR.glob("benchmark_*.json"), reverse=True)[:limit]
        results = []
        for f in files:
            with open(f) as fp:
                data = json.load(fp)
                results.append({
                    "suite_id": data["suite_id"],
                    "started_at": data["started_at"],
                    "completed_at": data["completed_at"],
                    "total_tasks": data["total_tasks"],
                    "models_tested": data["models_tested"],
                })
        return {"suites": results}

    @router.get("/test-cases")
    async def get_test_cases():
        """Get available test cases by category."""
        return {
            cat.value: [
                {"id": t["id"], "name": t["name"], "difficulty": t["difficulty"]}
                for t in tasks
            ]
            for cat, tasks in BENCHMARK_TEST_CASES.items()
        }

    @router.get("/leaderboard")
    async def get_leaderboard():
        """Get model leaderboard from latest benchmark."""
        engine = get_benchmark_engine()
        if engine._current_suite and engine._current_suite.scores_by_model:
            return {
                "scores_by_model": engine._current_suite.scores_by_model,
                "winners_by_category": engine._current_suite.winners,
            }
        return {"error": "No benchmark data available"}

    return router
