"""
Circuit Breaker Pattern — The Breaker, Guardian of the Gate

Prevents cascading failures by monitoring request success rates and
interrupting traffic to failing components. Three states: CLOSED (normal),
OPEN (gate sealed), HALF_OPEN (single probe to test recovery).

Systems without circuit breakers experience 76% failure rates in production.

Usage:
    breaker = CircuitBreaker(name="openrouter_api")
    result = await breaker.call(my_api_function, arg1, arg2)
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class CircuitState(Enum):
    CLOSED = "CLOSED"       # Normal operation, requests flow freely
    OPEN = "OPEN"           # Gate sealed, returns fallback immediately
    HALF_OPEN = "HALF_OPEN" # Single probe allowed to test recovery


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5          # Failures before opening
    recovery_wait_seconds: float = 30.0  # Wait before HALF_OPEN probe
    success_threshold: int = 1          # Successes in HALF_OPEN to close

    # Internal state
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    consecutive_failures: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    half_open_successes: int = field(default=0, init=False)

    def _should_attempt_reset(self) -> bool:
        return (
            self.state == CircuitState.OPEN
            and time.monotonic() - self.last_failure_time >= self.recovery_wait_seconds
        )

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.consecutive_failures = 0
                self.half_open_successes = 0
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
        self.half_open_successes = 0
        if (
            self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
            and self.consecutive_failures >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN

    async def call(self, fn: Callable, *args: Any, fallback: Any = None, **kwargs: Any) -> Any:
        """Call fn with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                return fallback  # Gate sealed, return fallback immediately

        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "seconds_until_probe": max(
                0,
                self.recovery_wait_seconds - (time.monotonic() - self.last_failure_time)
            ) if self.state == CircuitState.OPEN else 0,
        }


# Global registry for multi-tool agent systems
_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _breakers[name]


async def call_with_breaker(tool_name: str, fn: Callable, *args: Any, fallback: Any = None, **kwargs: Any) -> Any:
    """Convenience wrapper — get or create breaker and call fn."""
    breaker = get_breaker(tool_name)
    return await breaker.call(fn, *args, fallback=fallback, **kwargs)


def health_report() -> list[dict]:
    """Return status of all registered circuit breakers."""
    return [b.status() for b in _breakers.values()]
