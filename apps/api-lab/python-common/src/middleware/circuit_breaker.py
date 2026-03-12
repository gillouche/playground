import asyncio
import logging
import time
from collections.abc import Callable
from enum import Enum

logger = logging.getLogger("api-lab.circuit_breaker")


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.name = name
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if (
            self._state == CircuitState.OPEN
            and time.monotonic() - self._last_failure_time >= self.recovery_timeout
        ):
            return CircuitState.HALF_OPEN
        return self._state

    async def call(self, func: Callable, *args, **kwargs):
        async with self._lock:
            current_state = self.state

            if current_state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")

            if (
                current_state == CircuitState.HALF_OPEN
                and self._half_open_calls >= self.half_open_max_calls
            ):
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' half-open limit reached"
                )

            if current_state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _on_success(self):
        async with self._lock:
            self._failure_count = 0
            if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
                logger.info("Circuit breaker '%s' closed", self.name)
            self._state = CircuitState.CLOSED
            self._half_open_calls = 0

    async def _on_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker '%s' opened after %d failures",
                    self.name,
                    self._failure_count,
                )


class CircuitBreakerOpenError(Exception):
    pass
