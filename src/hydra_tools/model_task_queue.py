"""
Model Task Queue - Batch Tasks by Optimal Model

Instead of using suboptimal models or switching constantly:
1. Queue tasks by their optimal model type
2. Process all tasks for current model
3. Switch to next model when queue exhausted
4. Batch similar tasks for efficiency

This ensures BEST quality for every task while minimizing model switches.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)


@dataclass
class QueuedTask:
    """A task waiting in the model queue."""
    id: str
    prompt: str
    files: List[str]
    optimal_model: str
    task_type: str
    quality_score: int
    callback: Optional[Callable[[Dict], Awaitable[None]]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: int = 0  # Higher = more urgent
    timeout_seconds: int = 300

    # Result storage
    result: Optional[Dict] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ModelTaskQueue:
    """
    Intelligent task queue that batches by optimal model.

    Strategy:
    1. Tasks come in, get classified, assigned optimal model
    2. Tasks queue up by model type
    3. Worker processes current model's queue completely
    4. Switches to model with most pending tasks
    5. Repeat

    Benefits:
    - Every task gets BEST model for its type
    - Minimal model switches (batching)
    - Fair scheduling across task types
    """

    def __init__(self):
        # Queues by model name
        self._queues: Dict[str, List[QueuedTask]] = defaultdict(list)

        # Currently loaded model
        self._current_model: Optional[str] = None

        # Processing state
        self._processing = False
        self._worker_task: Optional[asyncio.Task] = None

        # Stats
        self._stats = {
            "tasks_queued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "model_switches": 0,
            "total_wait_time_ms": 0,
        }

        # Event for new tasks
        self._new_task_event = asyncio.Event()

        # Completion futures for waiting callers
        self._completion_futures: Dict[str, asyncio.Future] = {}

    async def enqueue(
        self,
        prompt: str,
        files: List[str] = None,
        optimal_model: str = None,
        task_type: str = "general",
        quality_score: int = 100,
        priority: int = 0,
        wait_for_result: bool = True,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Add a task to the queue.

        Args:
            prompt: The task prompt
            files: Files involved
            optimal_model: Best model for this task
            task_type: Type of task (coding, creative, etc.)
            quality_score: Expected quality with optimal model
            priority: Higher = process sooner
            wait_for_result: If True, wait for completion
            timeout: Max wait time in seconds

        Returns:
            If wait_for_result: The task result
            Otherwise: Task ID for later retrieval
        """
        task_id = str(uuid.uuid4())

        task = QueuedTask(
            id=task_id,
            prompt=prompt,
            files=files or [],
            optimal_model=optimal_model or "default",
            task_type=task_type,
            quality_score=quality_score,
            priority=priority,
            timeout_seconds=timeout,
        )

        # Add to appropriate queue
        self._queues[optimal_model].append(task)
        self._stats["tasks_queued"] += 1

        # Sort by priority (higher first)
        self._queues[optimal_model].sort(key=lambda t: -t.priority)

        # Signal worker
        self._new_task_event.set()

        # Start worker if not running
        if not self._processing:
            self._start_worker()

        logger.info(f"Task {task_id} queued for model {optimal_model} (queue size: {len(self._queues[optimal_model])})")

        if not wait_for_result:
            return {"task_id": task_id, "status": "queued", "queue_position": len(self._queues[optimal_model])}

        # Wait for completion
        future = asyncio.Future()
        self._completion_futures[task_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return {"task_id": task_id, "status": "timeout", "error": f"Task timed out after {timeout}s"}
        finally:
            self._completion_futures.pop(task_id, None)

    def _start_worker(self):
        """Start the background worker."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            self._processing = True

    async def _worker_loop(self):
        """Main worker loop - process queues by model."""
        logger.info("Model task queue worker started")

        while True:
            # Find queue with most pending tasks
            next_model = self._select_next_model()

            if next_model is None:
                # No tasks - wait for new ones
                self._new_task_event.clear()
                await self._new_task_event.wait()
                continue

            # Switch model if needed
            if next_model != self._current_model:
                await self._switch_model(next_model)

            # Process all tasks for this model
            await self._process_model_queue(next_model)

    def _select_next_model(self) -> Optional[str]:
        """Select the model with most pending tasks."""
        if not self._queues:
            return None

        # Filter to non-empty queues
        non_empty = {m: q for m, q in self._queues.items() if q}

        if not non_empty:
            return None

        # Prefer current model if it has tasks (no switch needed)
        if self._current_model and self._current_model in non_empty:
            return self._current_model

        # Otherwise, pick model with most tasks
        return max(non_empty.keys(), key=lambda m: len(non_empty[m]))

    async def _switch_model(self, model_name: str):
        """Switch to a different model."""
        logger.info(f"Switching model: {self._current_model} -> {model_name}")

        from hydra_tools.intelligent_model_selector import get_model_selector

        try:
            selector = get_model_selector()

            # Find the model ranking
            from hydra_tools.intelligent_model_selector import MODEL_RANKINGS, TaskType

            # Determine backend from rankings
            backend = "tabbyapi"  # default
            for rankings in MODEL_RANKINGS.values():
                for r in rankings:
                    if r.model_name == model_name:
                        backend = r.backend
                        break

            # Load the model
            success = await selector._load_model_by_name(model_name, backend)

            if success:
                self._current_model = model_name
                self._stats["model_switches"] += 1
                logger.info(f"Successfully switched to {model_name}")
            else:
                logger.error(f"Failed to switch to {model_name}")

        except Exception as e:
            logger.exception(f"Error switching model: {e}")

    async def _process_model_queue(self, model_name: str):
        """Process all tasks in a model's queue."""
        queue = self._queues.get(model_name, [])

        while queue:
            task = queue.pop(0)

            try:
                # Calculate wait time
                wait_time = (datetime.now(timezone.utc) - task.created_at).total_seconds() * 1000
                self._stats["total_wait_time_ms"] += wait_time

                # Execute task
                result = await self._execute_task(task)

                task.result = result
                task.completed_at = datetime.now(timezone.utc)
                self._stats["tasks_completed"] += 1

                # Notify waiting caller
                if task.id in self._completion_futures:
                    self._completion_futures[task.id].set_result(result)

            except Exception as e:
                logger.exception(f"Task {task.id} failed: {e}")
                task.error = str(e)
                self._stats["tasks_failed"] += 1

                if task.id in self._completion_futures:
                    self._completion_futures[task.id].set_result({
                        "task_id": task.id,
                        "status": "error",
                        "error": str(e)
                    })

    async def _execute_task(self, task: QueuedTask) -> Dict:
        """Execute a single task with the current model."""
        # Use the agent orchestrator to execute
        from hydra_tools.agent_orchestrator import get_orchestrator, TaskRequest, AgentCapability

        orchestrator = get_orchestrator()

        # Create task request
        request = TaskRequest(
            id=task.id,
            prompt=task.prompt,
            files=task.files,
            capabilities_required=[],
            prefer_local=True,
            timeout_seconds=task.timeout_seconds
        )

        result = await orchestrator.execute_task(request)

        return {
            "task_id": task.id,
            "status": result.status,
            "output": result.output,
            "model_used": self._current_model,
            "quality_score": task.quality_score,
            "execution_time_ms": result.execution_time_ms,
        }

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "current_model": self._current_model,
            "queues": {
                model: {
                    "pending": len(tasks),
                    "tasks": [{"id": t.id, "type": t.task_type, "priority": t.priority} for t in tasks[:5]]
                }
                for model, tasks in self._queues.items() if tasks
            },
            "stats": self._stats,
            "processing": self._processing,
        }

    def get_estimated_wait(self, model_name: str) -> Dict[str, Any]:
        """Estimate wait time for a model's queue."""
        queue = self._queues.get(model_name, [])

        # Average task time (rough estimate)
        avg_task_time_ms = 30000  # 30 seconds

        # Model switch time
        switch_time_ms = 60000 if model_name != self._current_model else 0

        queue_time_ms = len(queue) * avg_task_time_ms

        return {
            "model": model_name,
            "queue_length": len(queue),
            "estimated_wait_ms": switch_time_ms + queue_time_ms,
            "needs_model_switch": model_name != self._current_model,
        }


# Singleton
_queue: Optional[ModelTaskQueue] = None


def get_task_queue() -> ModelTaskQueue:
    """Get the singleton task queue."""
    global _queue
    if _queue is None:
        _queue = ModelTaskQueue()
    return _queue


# =============================================================================
# API ROUTER
# =============================================================================

from fastapi import APIRouter

router = APIRouter(prefix="/task-queue", tags=["task-queue"])


@router.get("/status")
async def get_queue_status():
    """Get current queue status across all models."""
    queue = get_task_queue()
    return queue.get_queue_status()


@router.post("/enqueue")
async def enqueue_task(
    prompt: str,
    files: List[str] = None,
    task_type: str = "general",
    priority: int = 0,
    wait: bool = False,
    timeout: int = 300
):
    """
    Enqueue a task for processing with optimal model.

    The task will be:
    1. Classified to determine optimal model
    2. Queued with other tasks for that model
    3. Processed when model is loaded (batched with similar tasks)
    """
    from hydra_tools.intelligent_model_selector import get_model_selector, classify_task

    # Classify task
    task_type_enum = classify_task(prompt, files)

    # Get optimal model
    selector = get_model_selector()
    best = await selector.select_best_model(task_type_enum)

    if not best:
        return {"error": "No suitable model found for task type"}

    # Enqueue
    queue = get_task_queue()
    result = await queue.enqueue(
        prompt=prompt,
        files=files or [],
        optimal_model=best.model_name,
        task_type=task_type_enum.value,
        quality_score=int(best.quality_score),
        priority=priority,
        wait_for_result=wait,
        timeout=timeout
    )

    return result


@router.get("/estimate/{model_name}")
async def get_wait_estimate(model_name: str):
    """Get estimated wait time for a specific model."""
    queue = get_task_queue()
    return queue.get_estimated_wait(model_name)


def create_task_queue_router() -> APIRouter:
    """Create and return the task queue router."""
    return router
