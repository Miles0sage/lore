"""
Lore runtime preamble — injected via PYTHONSTARTUP into agent processes.

Reads LORE_* env vars and monkey-patches openai/anthropic clients with:
  - TokenBudget tracking (if LORE_BUDGET_TOKENS is set)
  - Circuit breaker wrapping (if LORE_CIRCUIT_BREAKER=true)

This module must be importable with zero side-effects when LORE_* vars
are not set — it is safe to import in any Python process.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Budget helpers
# ---------------------------------------------------------------------------


def _extract_tokens(response: Any) -> int:
    """Extract total token count from an openai or anthropic response object."""
    # openai: response.usage.total_tokens
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0
    # openai style
    total = getattr(usage, "total_tokens", None)
    if total is not None:
        return int(total)
    # anthropic style: input_tokens + output_tokens
    inp = getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "output_tokens", 0) or 0
    return int(inp) + int(out)


def _parse_budget(value: str) -> int:
    """Parse a budget string like '100k', '1M', or '500000' into an int."""
    value = value.strip()
    if value.lower().endswith("k"):
        return int(float(value[:-1]) * 1_000)
    if value.lower().endswith("m"):
        return int(float(value[:-1]) * 1_000_000)
    return int(value)


# ---------------------------------------------------------------------------
# Patch factories
# ---------------------------------------------------------------------------


def _make_budget_wrapper(original_fn: Any, budget: Any, label: str) -> Any:
    """Return a wrapper that tracks token usage against *budget*."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        budget.warn_if_low()
        if budget.remaining() == 0:
            raise RuntimeError(
                f"lore: token budget exhausted ({budget._total} tokens). "
                "Stop the agent or increase budget_tokens in lore.yaml."
            )
        result = original_fn(*args, **kwargs)
        tokens = _extract_tokens(result)
        if tokens:
            budget.consume(label, tokens)
            budget.warn_if_low()
        return result

    return wrapper


def _make_cb_wrapper(original_fn: Any, engine: Any, tool_name: str) -> Any:
    """Return a wrapper that records success/failure to *engine*."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if engine.is_open(tool_name):
            raise RuntimeError(
                f"lore: circuit breaker OPEN for '{tool_name}'. "
                "Too many recent failures — backing off."
            )
        t0 = time.monotonic()
        try:
            result = original_fn(*args, **kwargs)
            engine.record_success(tool_name)
            _ = time.monotonic() - t0
            return result
        except Exception:
            engine.record_failure(tool_name)
            raise

    return wrapper


# ---------------------------------------------------------------------------
# OpenAI patching
# ---------------------------------------------------------------------------


def _patch_openai(budget: Any | None, cb_engine: Any | None) -> bool:
    """Attempt to patch openai.OpenAI completions. Returns True if patched."""
    try:
        import openai  # type: ignore[import]
    except ImportError:
        return False

    original_create = openai.OpenAI.chat.completions.create  # type: ignore[attr-defined]

    fn = original_create
    if budget is not None:
        fn = _make_budget_wrapper(fn, budget, "openai.chat")
    if cb_engine is not None:
        fn = _make_cb_wrapper(fn, cb_engine, "openai")

    openai.OpenAI.chat.completions.create = fn  # type: ignore[attr-defined]
    logger.debug("lore preamble: patched openai.OpenAI.chat.completions.create")
    return True


# ---------------------------------------------------------------------------
# Anthropic patching
# ---------------------------------------------------------------------------


def _patch_anthropic(budget: Any | None, cb_engine: Any | None) -> bool:
    """Attempt to patch anthropic.Anthropic messages. Returns True if patched."""
    try:
        import anthropic  # type: ignore[import]
    except ImportError:
        return False

    original_create = anthropic.Anthropic.messages.create  # type: ignore[attr-defined]

    fn = original_create
    if budget is not None:
        fn = _make_budget_wrapper(fn, budget, "anthropic.messages")
    if cb_engine is not None:
        fn = _make_cb_wrapper(fn, cb_engine, "anthropic")

    anthropic.Anthropic.messages.create = fn  # type: ignore[attr-defined]
    logger.debug("lore preamble: patched anthropic.Anthropic.messages.create")
    return True


# ---------------------------------------------------------------------------
# Main entry point — called when PYTHONSTARTUP sources this file
# ---------------------------------------------------------------------------


def activate() -> None:
    """Read LORE_* env vars and install patches into the current process."""
    budget_str = os.environ.get("LORE_BUDGET_TOKENS", "").strip()
    cb_enabled = os.environ.get("LORE_CIRCUIT_BREAKER", "").lower() in ("true", "1", "yes")
    cb_threshold = int(os.environ.get("LORE_CIRCUIT_BREAKER_THRESHOLD", "5"))
    cb_window = float(os.environ.get("LORE_CIRCUIT_BREAKER_WINDOW_SECONDS", "60"))

    budget = None
    if budget_str:
        try:
            from lore.observability import TokenBudget
            total = _parse_budget(budget_str)
            budget = TokenBudget(total)
            logger.info("lore preamble: token budget set to %d tokens", total)
        except Exception as exc:
            logger.warning("lore preamble: could not init TokenBudget: %s", exc)

    cb_engine = None
    if cb_enabled:
        try:
            from lore.circuit_breaker import CircuitBreakerEngine, CircuitConfig, InMemoryCircuitStore
            config = CircuitConfig(
                failure_threshold=cb_threshold,
                recovery_wait=cb_window,
            )
            cb_engine = CircuitBreakerEngine(
                store=InMemoryCircuitStore(),
                config=config,
            )
            logger.info(
                "lore preamble: circuit breaker enabled (threshold=%d, window=%.0fs)",
                cb_threshold,
                cb_window,
            )
        except Exception as exc:
            logger.warning("lore preamble: could not init CircuitBreaker: %s", exc)

    if budget is None and cb_engine is None:
        return

    _patch_openai(budget, cb_engine)
    _patch_anthropic(budget, cb_engine)


# Auto-activate when sourced via PYTHONSTARTUP
activate()
