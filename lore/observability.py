"""
Observability and error envelope module for Lore dispatch.

Components:
  ErrorEnvelope    - Frozen dataclass capturing error context
  ToolCallVerifier - Validates tool call responses
  TokenBudget      - Per-step token tracking with budget warnings
  ObservabilityHub - Central hub for recording errors/successes (singleton)

Module-level wrappers mirror the singleton pattern from circuit_breaker.py.

Usage::

    from lore.observability import record_error, record_success, error_rate, ErrorEnvelope

    try:
        result = call_tool(...)
        record_success(task_id="t1", model="gpt-4.1", latency_s=0.5, tokens_used=120)
    except Exception as exc:
        import traceback
        envelope = ErrorEnvelope(
            task_id="t1",
            error_type=type(exc).__name__,
            stack=traceback.format_exc(),
        )
        record_error(envelope)
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lore.config import get_observability_log_path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ErrorEnvelope — frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorEnvelope:
    """Immutable record of a dispatch or tool-call error.

    Args:
        task_id:       Unique identifier for the task that failed.
        error_type:    Exception class name (e.g. ``"TimeoutError"``).
        stack:         Full traceback string.
        timestamp:     Unix epoch seconds (defaults to now).
        worker_id:     Hostname of the worker that raised the error.
        attempt_count: How many times the task has been attempted.
        model:         Model that was being invoked (empty if unknown).
        latency_s:     Elapsed time in seconds before the error occurred.
        extra:         Arbitrary additional context.
    """

    task_id: str
    error_type: str
    stack: str
    timestamp: float = field(default_factory=time.time)
    worker_id: str = field(default_factory=socket.gethostname)
    attempt_count: int = 1
    model: str = ""
    latency_s: float = 0.0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "event": "error",
            "task_id": self.task_id,
            "error_type": self.error_type,
            "stack": self.stack,
            "timestamp": self.timestamp,
            "worker_id": self.worker_id,
            "attempt_count": self.attempt_count,
            "model": self.model,
            "latency_s": self.latency_s,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ErrorEnvelope":
        """Deserialize from a dict (e.g. loaded from JSONL)."""
        return cls(
            task_id=data["task_id"],
            error_type=data["error_type"],
            stack=data.get("stack", ""),
            timestamp=data.get("timestamp", 0.0),
            worker_id=data.get("worker_id", ""),
            attempt_count=data.get("attempt_count", 1),
            model=data.get("model", ""),
            latency_s=data.get("latency_s", 0.0),
            extra=data.get("extra", {}),
        )


# ---------------------------------------------------------------------------
# ToolCallVerifier
# ---------------------------------------------------------------------------


class ToolCallVerifier:
    """Validates tool call responses.

    All methods are static — instantiate once and reuse or call as class methods.
    """

    @staticmethod
    def verify_http(status_code: int) -> bool:
        """Return True if *status_code* is in the 200–299 success range."""
        return 200 <= status_code <= 299

    @staticmethod
    def verify_non_empty(response: Any) -> bool:
        """Return True if *response* is not None, empty string, list, or dict."""
        if response is None:
            return False
        if isinstance(response, (str, list, dict)) and len(response) == 0:
            return False
        return True

    @staticmethod
    def verify_schema(response: dict, required_keys: list[str]) -> bool:
        """Return True if all *required_keys* are present in *response*."""
        if not isinstance(response, dict):
            return False
        return all(k in response for k in required_keys)

    @classmethod
    def verify_all(
        cls,
        status_code: int,
        response: Any,
        required_keys: list[str] | None = None,
    ) -> tuple[bool, list[str]]:
        """Run all applicable verifications and return ``(passed, reasons)``.

        Args:
            status_code:   HTTP status code to check.
            response:      Response payload to inspect.
            required_keys: Optional list of keys that must exist in *response*.

        Returns:
            A tuple ``(passed, failures)`` where *failures* is a list of
            human-readable strings describing each check that failed.
            *passed* is ``True`` when *failures* is empty.
        """
        failures: list[str] = []

        if not cls.verify_http(status_code):
            failures.append(f"http_status_not_ok: {status_code}")

        if not cls.verify_non_empty(response):
            failures.append("response_is_empty")

        if required_keys:
            if not cls.verify_schema(response, required_keys):
                missing = [k for k in required_keys if not isinstance(response, dict) or k not in response]
                failures.append(f"missing_keys: {missing}")

        return (len(failures) == 0, failures)


# ---------------------------------------------------------------------------
# TokenBudget
# ---------------------------------------------------------------------------


class TokenBudget:
    """Per-step token consumption tracker with budget warnings.

    Args:
        total_budget: Maximum number of tokens allowed for the operation.
    """

    def __init__(self, total_budget: int) -> None:
        self._total = total_budget
        self._steps: dict[str, int] = {}
        self._lock = threading.Lock()

    def consume(self, step_name: str, tokens: int) -> None:
        """Record *tokens* consumed by *step_name*.

        If *step_name* is called multiple times, tokens accumulate.
        """
        with self._lock:
            self._steps[step_name] = self._steps.get(step_name, 0) + tokens

    def _consumed(self) -> int:
        with self._lock:
            return sum(self._steps.values())

    def remaining(self) -> int:
        """Return the number of tokens remaining in the budget."""
        return max(0, self._total - self._consumed())

    def pct_used(self) -> float:
        """Return fraction of budget consumed, in the range 0.0–1.0."""
        if self._total <= 0:
            return 1.0
        consumed = self._consumed()
        return min(1.0, consumed / self._total)

    def warn_if_low(self, threshold: float = 0.80) -> bool:
        """Log a warning and return True if pct_used >= *threshold*.

        Args:
            threshold: Fraction (0.0–1.0) at which to warn. Default 0.80.

        Returns:
            True when the budget has hit or exceeded the threshold.
        """
        pct = self.pct_used()
        if pct >= threshold:
            logger.warning(
                "token_budget: %.0f%% used (%d/%d tokens consumed, %d remaining)",
                pct * 100,
                self._consumed(),
                self._total,
                self.remaining(),
            )
            return True
        return False

    def summary(self) -> dict[str, Any]:
        """Return a breakdown dict with per-step counts plus totals."""
        with self._lock:
            breakdown = dict(self._steps)
        consumed = sum(breakdown.values())
        return {
            **breakdown,
            "total": self._total,
            "consumed": consumed,
            "remaining": max(0, self._total - consumed),
            "pct_used": self.pct_used(),
        }


# ---------------------------------------------------------------------------
# ObservabilityHub — singleton
# ---------------------------------------------------------------------------

_MAX_MEMORY_EVENTS = 100


class ObservabilityHub:
    """Central hub for recording and querying observability events.

    Events are written atomically (one JSON line per event) to the JSONL log
    configured by ``config.get_observability_log_path()``.  The last
    ``_MAX_MEMORY_EVENTS`` events are also kept in memory for fast queries.

    Args:
        log_path: Override the JSONL log path (useful in tests).
    """

    def __init__(self, log_path: Path | None = None) -> None:
        self._log_path = log_path or get_observability_log_path()
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # In-memory ring buffer: list of dicts (both error and success events)
        self._events: list[dict[str, Any]] = []

    # -- Public API ----------------------------------------------------------

    def record_error(self, envelope: ErrorEnvelope) -> None:
        """Append *envelope* to the JSONL log and in-memory buffer."""
        record = envelope.to_dict()
        self._append_event(record)

    def record_success(
        self,
        task_id: str,
        model: str,
        latency_s: float,
        tokens_used: int,
    ) -> None:
        """Append a success event to the JSONL log and in-memory buffer."""
        record: dict[str, Any] = {
            "event": "success",
            "task_id": task_id,
            "model": model,
            "latency_s": latency_s,
            "tokens_used": tokens_used,
            "timestamp": time.time(),
            "worker_id": socket.gethostname(),
        }
        self._append_event(record)

    def recent_errors(self, n: int = 10) -> list[ErrorEnvelope]:
        """Return the last *n* error envelopes from the in-memory buffer.

        Events are returned in chronological order (oldest first within the
        returned slice, most-recent last).
        """
        with self._lock:
            errors = [e for e in self._events if e.get("event") == "error"]
        return [ErrorEnvelope.from_dict(e) for e in errors[-n:]]

    def error_rate(self, window_s: float = 300.0) -> float:
        """Return the fraction of events that were errors in the last *window_s* seconds.

        Returns 0.0 when there are no events in the window.
        """
        cutoff = time.time() - window_s
        with self._lock:
            recent = [e for e in self._events if e.get("timestamp", 0) >= cutoff]
        if not recent:
            return 0.0
        error_count = sum(1 for e in recent if e.get("event") == "error")
        return error_count / len(recent)

    # -- OTel export (lazy, no-op if not installed) --------------------------

    def _try_otel_export(self, record: dict[str, Any]) -> None:
        """Attempt to export *record* via OpenTelemetry.  No-op if OTel absent."""
        try:
            from opentelemetry import trace  # type: ignore[import]  # noqa: F401
            # Minimal integration: add a span event on the current span if active.
            tracer_provider = trace.get_tracer_provider()
            tracer = tracer_provider.get_tracer("lore.observability")
            with tracer.start_as_current_span("lore.event") as span:
                for k, v in record.items():
                    if isinstance(v, (str, int, float, bool)):
                        span.set_attribute(f"lore.{k}", v)
        except ImportError:
            pass  # OTel not installed — silently skip
        except Exception as exc:  # pragma: no cover
            logger.debug("observability: otel export failed: %s", exc)

    # -- Internal ------------------------------------------------------------

    def _append_event(self, record: dict[str, Any]) -> None:
        """Write *record* as one JSONL line and update the in-memory buffer."""
        line = json.dumps(record, default=str) + "\n"
        try:
            with self._lock:
                with self._log_path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                self._events.append(record)
                # Trim to last _MAX_MEMORY_EVENTS
                if len(self._events) > _MAX_MEMORY_EVENTS:
                    self._events = self._events[-_MAX_MEMORY_EVENTS:]
        except OSError as exc:
            logger.warning("observability: could not write event to %s: %s", self._log_path, exc)

        # Best-effort OTel export (outside the lock, non-blocking)
        self._try_otel_export(record)


# ---------------------------------------------------------------------------
# Singleton hub
# ---------------------------------------------------------------------------

_hub_lock = threading.Lock()
_hub: ObservabilityHub | None = None


def _get_hub() -> ObservabilityHub:
    """Return the process-level singleton hub (lazy init)."""
    global _hub
    if _hub is None:
        with _hub_lock:
            if _hub is None:
                _hub = ObservabilityHub()
    return _hub


def _set_hub(hub: ObservabilityHub) -> None:
    """Replace the singleton hub (for tests / dependency injection)."""
    global _hub
    with _hub_lock:
        _hub = hub


# ---------------------------------------------------------------------------
# Module-level wrappers (primary public API)
# ---------------------------------------------------------------------------


def record_error(envelope: ErrorEnvelope) -> None:
    """Record an error envelope via the singleton hub."""
    _get_hub().record_error(envelope)


def record_success(
    task_id: str,
    model: str,
    latency_s: float,
    tokens_used: int,
) -> None:
    """Record a success event via the singleton hub."""
    _get_hub().record_success(
        task_id=task_id,
        model=model,
        latency_s=latency_s,
        tokens_used=tokens_used,
    )


def recent_errors(n: int = 10) -> list[ErrorEnvelope]:
    """Return the last *n* error envelopes from the singleton hub."""
    return _get_hub().recent_errors(n)


def error_rate(window_s: float = 300.0) -> float:
    """Return the error rate over the last *window_s* seconds."""
    return _get_hub().error_rate(window_s)
