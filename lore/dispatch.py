"""Model dispatch for Lore — executes classified tasks against the tiered brain.

Three tiers:
  light    → deepseek-chat   (bulk extraction, triage, dedup)
  standard → gpt-4.1         (daily operator work, briefs, drafts)
  high     → gpt-5.4         (security review, canon judgment, architecture)

Circuit breaker: per-model failure counter. Once a model hits the threshold
it is marked open and traffic escalates one tier up. Top-tier open = hard fail,
no silent cost escalation.
"""

from __future__ import annotations

import os
import time
from typing import Any

from . import routing
from .circuit_breaker import (
    is_circuit_open,
    record_failure,
    record_success,
    resolve_model as cb_resolve_model,
    get_circuit_status as cb_get_circuit_status,
    reset_circuit as cb_reset_circuit,
    CachedFallback,
    _get_engine,
)

# Lazy imports for telemetry — must not break dispatch if these fail
_distill_mod = None
_postmortem_mod = None

def _get_distill():
    global _distill_mod
    if _distill_mod is None:
        try:
            from . import distill as _dm
            _distill_mod = _dm
        except Exception:
            pass
    return _distill_mod

def _get_postmortem():
    global _postmortem_mod
    if _postmortem_mod is None:
        try:
            from . import postmortem as _pm
            _postmortem_mod = _pm
        except Exception:
            pass
    return _postmortem_mod

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
OPENAI_BASE_URL = "https://api.openai.com/v1"

_TIER_ORDER = ["deepseek-chat", "gpt-4.1", "gpt-5.4"]

# Module-level CachedFallback — stores last successful response per model
# so callers can retrieve stale-but-useful results when a circuit is open.
_response_cache: CachedFallback = CachedFallback(_get_engine())

# Rough pricing per 1M tokens (input, output)
_PRICING: dict[str, tuple[float, float]] = {
    "deepseek-chat": (0.27, 1.10),
    "gpt-4.1": (2.00, 8.00),
    "gpt-5.4": (10.00, 30.00),
}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _PRICING.get(model, (5.0, 15.0))
    return (prompt_tokens * rates[0] + completion_tokens * rates[1]) / 1_000_000


def _make_client(model: str):
    from openai import OpenAI  # lazy import to keep startup fast

    if model == "deepseek-chat":
        key = os.environ.get("DEEPSEEK_API_KEY") or _load_from_factory_env("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("DEEPSEEK_API_KEY not set — add to environment or set LORE_ENV_FILE")
        return OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)

    key = os.environ.get("OPENAI_API_KEY") or _load_from_factory_env("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set — add to environment or set LORE_ENV_FILE")
    return OpenAI(api_key=key, base_url=OPENAI_BASE_URL)


def _load_from_factory_env(key: str) -> str:
    """Fallback: read from a .env file specified by LORE_ENV_FILE, or a local .env."""
    env_path = os.environ.get("LORE_ENV_FILE", ".env")
    try:
        for line in open(env_path).readlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _resolve_model(preferred: str) -> tuple[str, str | None]:
    """Return (model_to_use, escalation_reason). Applies circuit breaker."""
    return cb_resolve_model(preferred)


def dispatch_task(
    task_type: str,
    prompt: str,
    *,
    system: str = "",
    description: str = "",
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Classify task, pick model tier, call API, log telemetry.

    Returns a result dict with keys: model, content, latency_s, cost_usd,
    usage, routing. On error returns error key instead of content.
    """
    plan = routing.classify_task(task_type=task_type, description=description or prompt[:120])
    preferred = plan["model"]
    model, escalation_reason = _resolve_model(preferred)

    if escalation_reason == "all_circuits_open":
        routing.log_router_event(
            task_type=task_type,
            model=preferred,
            status="error",
            description="All model circuits open — refusing dispatch",
            error="all_circuits_open",
        )
        return {
            "error": "all_circuits_open",
            "task_type": task_type,
            "message": "All model tiers are circuit-open. Manual intervention required.",
            "circuit_status": cb_get_circuit_status(),
        }

    if escalation_reason:
        routing.log_router_event(
            task_type=task_type,
            model=model,
            status="escalated",
            description=f"Escalated from {preferred} to {model}",
            error=escalation_reason,
        )

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    start = time.monotonic()
    try:
        client = _make_client(model)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
        latency = time.monotonic() - start
        content = response.choices[0].message.content or ""

        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)

        record_success(model)
        routing.log_router_event(
            task_type=task_type,
            model=model,
            status="ok",
            description=description or prompt[:80],
            latency_s=latency,
            cost_usd=cost,
            accepted=True,
        )
        success_result = {
            "model": model,
            "task_type": task_type,
            "content": content,
            "latency_s": round(latency, 3),
            "cost_usd": round(cost, 6),
            "usage": {"prompt": prompt_tokens, "completion": completion_tokens},
            "routing": plan,
            "escalated_from": preferred if escalation_reason else None,
        }

        # Cache the successful response for CachedFallback (non-blocking)
        try:
            _response_cache.store(model, success_result)
        except Exception:
            pass

        # Trajectory distillation (non-blocking)
        try:
            dm = _get_distill()
            if dm is not None:
                dm.capture_trajectory(success_result)
        except Exception:
            pass

        return success_result

    except Exception as exc:
        latency = time.monotonic() - start
        record_failure(model)
        routing.log_router_event(
            task_type=task_type,
            model=model,
            status="error",
            description=description or prompt[:80],
            latency_s=latency,
            error=str(exc)[:200],
        )
        engine = _get_engine()
        model_status = engine.get_status(model)
        error_result = {
            "error": str(exc),
            "model": model,
            "task_type": task_type,
            "circuit_failure_count": model_status["failures"],
            "circuit_threshold": engine._config.for_tool(model).failure_threshold,
        }

        # Auto-postmortem (non-blocking)
        try:
            pm = _get_postmortem()
            if pm is not None:
                pm.generate_postmortem(error_result)
        except Exception:
            pass

        return error_result


def get_circuit_status() -> dict[str, Any]:
    """Return current circuit breaker state for all models."""
    return cb_get_circuit_status()


def reset_circuit(model: str) -> dict[str, Any]:
    """Manually reset a model's circuit breaker (operator use)."""
    return cb_reset_circuit(model)
