# LORE SCAFFOLD: sentinel_observability
"""
Sentinel Observability — The Sentinel, Guardian of System Visibility

Agent observability and input validation. The Sentinel sees everything —
error rates, latency, token spend, semantic coherence. It validates inputs
before they reach the agent and logs structured events for analysis.

Includes prompt injection detection as a first-class concern.

Usage:
    sentinel = Sentinel()
    validated = sentinel.validate_input(user_input)
    sentinel.log_event("llm_call", {"model": "gpt-4", "tokens": 1500})
    report = sentinel.metrics_report()
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


# Prompt injection patterns — extend for your domain
INJECTION_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"ignore (all )?(previous|prior|above) (instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"system:\s*", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"do not follow", re.IGNORECASE),
    re.compile(r"pretend (you are|to be)", re.IGNORECASE),
)


@dataclass(frozen=True)
class ValidationResult:
    """Immutable validation result."""
    valid: bool
    input_text: str
    warnings: tuple[str, ...] = ()
    blocked: bool = False
    reason: str = ""


class InputValidator:
    """Validates agent inputs, detects prompt injection attempts."""

    def __init__(self, max_length: int = 10_000, custom_patterns: tuple[re.Pattern, ...] = ()):
        self.max_length = max_length
        self.patterns = INJECTION_PATTERNS + custom_patterns

    def validate(self, text: str) -> ValidationResult:
        """Validate input text. Returns ValidationResult (immutable)."""
        warnings: list[str] = []

        if len(text) > self.max_length:
            return ValidationResult(
                valid=False, input_text=text[:100], blocked=True,
                reason=f"Input exceeds max length ({len(text)} > {self.max_length})",
            )

        for pattern in self.patterns:
            if pattern.search(text):
                return ValidationResult(
                    valid=False, input_text=text[:100], blocked=True,
                    reason=f"Potential prompt injection detected: {pattern.pattern}",
                )

        if len(text) < 3:
            warnings.append("Input is very short — may produce low-quality output")

        return ValidationResult(valid=True, input_text=text[:100], warnings=tuple(warnings))


@dataclass
class MetricCounter:
    """Simple metric counter with time-windowed tracking."""
    counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latencies: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def increment(self, name: str, value: int = 1) -> None:
        self.counts[name] += value

    def record_latency(self, name: str, seconds: float) -> None:
        self.latencies[name].append(seconds)
        # Keep last 100 per metric
        if len(self.latencies[name]) > 100:
            self.latencies[name] = self.latencies[name][-100:]


class Sentinel:
    """Observability hub — validates inputs, logs events, tracks metrics."""

    def __init__(self, max_input_length: int = 10_000):
        self.validator = InputValidator(max_length=max_input_length)
        self.metrics = MetricCounter()
        self._events: list[dict] = []

    def validate_input(self, text: str) -> ValidationResult:
        """Validate and log input validation."""
        result = self.validator.validate(text)
        self.metrics.increment("validations_total")
        if result.blocked:
            self.metrics.increment("validations_blocked")
            self.log_event("input_blocked", {"reason": result.reason})
        return result

    def log_event(self, event_type: str, data: dict | None = None) -> None:
        """Log a structured event."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": dict(data or {}),
        }
        self._events.append(event)
        self.metrics.increment(f"events.{event_type}")

    def metrics_report(self) -> dict:
        """Return current metrics summary."""
        return {
            "counts": dict(self.metrics.counts),
            "latencies": {
                name: {
                    "count": len(vals),
                    "avg": sum(vals) / len(vals) if vals else 0,
                    "max": max(vals) if vals else 0,
                }
                for name, vals in self.metrics.latencies.items()
            },
            "recent_events": self._events[-10:],
        }
