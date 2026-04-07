"""
Tool Health Monitor — The Warden, Keeper of the Gates

Tracks per-tool success rates, latency, and error classification.
Feeds signals to circuit breakers and model router.

Usage:
    monitor = ToolHealthMonitor()
    result = await monitor.call("github_api", my_github_fn, arg1)
    print(monitor.health_report())
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolMetrics:
    calls: deque = field(default_factory=lambda: deque(maxlen=100))   # bool: success/fail
    latencies: deque = field(default_factory=lambda: deque(maxlen=100))  # float: seconds
    errors: dict = field(default_factory=lambda: defaultdict(int))
    circuit_state: str = "CLOSED"

    def success_rate(self) -> float:
        if not self.calls:
            return 1.0
        return sum(self.calls) / len(self.calls)

    def p95_latency(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def is_healthy(self, threshold: float = 0.85) -> bool:
        return self.success_rate() >= threshold


class ToolHealthMonitor:
    def __init__(self, alert_threshold: float = 0.85):
        self.metrics: dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self.alert_threshold = alert_threshold

    async def call(self, tool_name: str, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call fn and track health metrics."""
        start = time.monotonic()
        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            self._record(tool_name, success=True, latency=time.monotonic() - start)
            return result
        except Exception as e:
            self._record(tool_name, success=False, latency=time.monotonic() - start, error=type(e).__name__)
            raise

    def _record(self, tool_name: str, success: bool, latency: float, error: str = "") -> None:
        m = self.metrics[tool_name]
        m.calls.append(success)
        m.latencies.append(latency)
        if error:
            m.errors[error] += 1

    def health_report(self) -> list[dict]:
        return [
            {
                "tool": name,
                "success_rate": round(m.success_rate(), 3),
                "p95_latency_ms": round(m.p95_latency() * 1000, 1),
                "circuit_state": m.circuit_state,
                "healthy": m.is_healthy(self.alert_threshold),
                "top_errors": dict(list(m.errors.items())[:3]),
            }
            for name, m in self.metrics.items()
        ]

    def degraded_tools(self) -> list[str]:
        return [name for name, m in self.metrics.items() if not m.is_healthy(self.alert_threshold)]
