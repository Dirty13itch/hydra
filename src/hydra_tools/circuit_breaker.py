"""
Circuit Breaker Pattern for Inference Services

Prevents cascading failures by stopping requests to failing services.
Automatically recovers when services come back online.
"""

import asyncio
import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Callable, Any
import httpx

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Service failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 3      # Failures before opening
    success_threshold: int = 2      # Successes to close from half-open
    timeout: float = 30.0           # Seconds before trying again (open -> half-open)
    half_open_max_calls: int = 1    # Max concurrent calls in half-open state


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    last_success_time: Optional[float]
    consecutive_failures: int
    total_failures: int
    total_successes: int


class CircuitBreaker:
    """
    Circuit breaker for a single service.

    States:
    - CLOSED: Normal operation. Track failures, open if threshold exceeded.
    - OPEN: Service is failing. Block requests, wait for timeout.
    - HALF_OPEN: Test service. Allow limited requests, close if successful.
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        on_state_change: Optional[Callable[[str, CircuitState, CircuitState], None]] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.on_state_change = on_state_change

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._half_open_calls = 0

        # Lifetime stats
        self._total_failures = 0
        self._total_successes = 0

        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_closed(self) -> bool:
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    def stats(self) -> CircuitStats:
        return CircuitStats(
            state=self._state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_success_time=self._last_success_time,
            consecutive_failures=self._failure_count,
            total_failures=self._total_failures,
            total_successes=self._total_successes
        )

    async def _set_state(self, new_state: CircuitState):
        """Change state and notify listeners."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            logger.info(f"Circuit breaker '{self.name}': {old_state.value} -> {new_state.value}")

            if self.on_state_change:
                try:
                    self.on_state_change(self.name, old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")

    async def can_execute(self) -> bool:
        """Check if a request can be made."""
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if timeout has passed
                if self._last_failure_time:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.config.timeout:
                        await self._set_state(CircuitState.HALF_OPEN)
                        self._half_open_calls = 0
                        return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self):
        """Record a successful call."""
        async with self._lock:
            self._last_success_time = time.time()
            self._total_successes += 1

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._set_state(CircuitState.CLOSED)
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def record_failure(self):
        """Record a failed call."""
        async with self._lock:
            self._last_failure_time = time.time()
            self._failure_count += 1
            self._total_failures += 1

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens the circuit
                await self._set_state(CircuitState.OPEN)
                self._success_count = 0
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    await self._set_state(CircuitState.OPEN)

    async def force_open(self):
        """Manually open the circuit."""
        async with self._lock:
            await self._set_state(CircuitState.OPEN)
            self._last_failure_time = time.time()

    async def force_close(self):
        """Manually close the circuit."""
        async with self._lock:
            await self._set_state(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0


class InferenceCircuitBreakers:
    """
    Manages circuit breakers for all inference services.
    Integrates with Prometheus metrics.
    """

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._metrics_callback = None

    def register_metrics_callback(self, callback: Callable[[str, int], None]):
        """Register callback to update Prometheus metrics."""
        self._metrics_callback = callback

    def _on_state_change(self, service: str, old_state: CircuitState, new_state: CircuitState):
        """Handle state change events."""
        if self._metrics_callback:
            is_open = 1 if new_state == CircuitState.OPEN else 0
            self._metrics_callback(service, is_open)

    def get_or_create(self, service: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service not in self.breakers:
            self.breakers[service] = CircuitBreaker(
                name=service,
                config=config or CircuitBreakerConfig(),
                on_state_change=self._on_state_change
            )
        return self.breakers[service]

    def get_all_stats(self) -> Dict[str, CircuitStats]:
        """Get stats for all circuit breakers."""
        return {name: cb.stats() for name, cb in self.breakers.items()}

    async def execute_with_breaker(
        self,
        service: str,
        operation: Callable[[], Any],
        fallback: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        Execute an operation with circuit breaker protection.

        Args:
            service: Service name
            operation: Async function to execute
            fallback: Optional fallback function if circuit is open

        Returns:
            Result of operation or fallback

        Raises:
            CircuitOpenError if circuit is open and no fallback
        """
        breaker = self.get_or_create(service)

        if not await breaker.can_execute():
            if fallback:
                logger.warning(f"Circuit open for {service}, using fallback")
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
            raise CircuitOpenError(f"Circuit breaker open for {service}")

        try:
            result = await operation() if asyncio.iscoroutinefunction(operation) else operation()
            await breaker.record_success()
            return result
        except Exception as e:
            await breaker.record_failure()
            raise


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global instance
inference_breakers = InferenceCircuitBreakers()


# Convenience function for health checks
async def check_service_with_breaker(
    service: str,
    url: str,
    timeout: float = 5.0
) -> bool:
    """
    Check service health with circuit breaker.

    Returns True if healthy, False if unhealthy or circuit open.
    """
    breaker = inference_breakers.get_or_create(service)

    if not await breaker.can_execute():
        logger.debug(f"Circuit open for {service}, skipping health check")
        return False

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            if resp.status_code < 400:
                await breaker.record_success()
                return True
            else:
                await breaker.record_failure()
                return False
    except Exception as e:
        await breaker.record_failure()
        logger.warning(f"Health check failed for {service}: {e}")
        return False
