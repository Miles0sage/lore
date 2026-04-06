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

_FAILURE_THRESHOLD = 3
_TIER_ORDER = ["deepseek-chat", "gpt-4.1", "gpt-5.4"]

# In-process circuit breaker state (reset on process restart)
_failure_counts: dict[str, int] = {}

# Rough pricing per 1M tokens (input, output)
_PRICING: dict[str, tuple[float, float]] = {
    "deepseek-chat": (0.27, 1.10),
    "gpt-4.1": (2.00, 8.00),
    "gpt-5.4": (10.00, 30.00),
}


def _is_circuit_open(model: str) -> bool:
    return _failure_counts.get(model, 0) >= _FAILURE_THRESHOLD


def _record_failure(model: str) -> None:
    _failure_counts[model] = _failure_counts.get(model, 0) + 1


def _record_success(model: str) -> None:
    _failure_counts[model] = 0


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _PRICING.get(model, (5.0, 15.0))
    return (prompt_tokens * rates[0] + completion_tokens * rates[1]) / 1_000_000


def _make_client(model: str):
    from openai import OpenAI  # lazy import to keep startup fast

    if model == "deepseek-chat":
        key = os.environ.get("DEEPSEEK_API_KEY") or _load_from_factory_env("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError("DEEPSEEK_API_KEY not set — add to env or /root/ai-factory/.env")
        return OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL)

    key = os.environ.get("OPENAI_API_KEY") or _load_from_factory_env("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set — add to env or /root/ai-factory/.env")
    return OpenAI(api_key=key, base_url=OPENAI_BASE_URL)


def _load_from_factory_env(key: str) -> str:
    """Fallback: read from /root/ai-factory/.env if key not in environment."""
    env_path = "/root/ai-factory/.env"
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
    if not _is_circuit_open(preferred):
        return preferred, None

    idx = _TIER_ORDER.index(preferred) if preferred in _TIER_ORDER else 0
    for fallback in _TIER_ORDER[idx + 1:]:
        if not _is_circuit_open(fallback):
            return fallback, f"circuit_open:{preferred}"

    return preferred, "all_circuits_open"


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
            "failure_counts": dict(_failure_counts),
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

        _record_success(model)
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
        _record_failure(model)
        routing.log_router_event(
            task_type=task_type,
            model=model,
            status="error",
            description=description or prompt[:80],
            latency_s=latency,
            error=str(exc)[:200],
        )
        error_result = {
            "error": str(exc),
            "model": model,
            "task_type": task_type,
            "circuit_failure_count": _failure_counts.get(model, 0),
            "circuit_threshold": _FAILURE_THRESHOLD,
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
    return {
        model: {
            "failures": _failure_counts.get(model, 0),
            "open": _is_circuit_open(model),
            "threshold": _FAILURE_THRESHOLD,
        }
        for model in _TIER_ORDER
    }


def reset_circuit(model: str) -> dict[str, Any]:
    """Manually reset a model's circuit breaker (operator use)."""
    if model not in _TIER_ORDER:
        return {"error": f"Unknown model: {model}", "known": _TIER_ORDER}
    _failure_counts[model] = 0
    return {"reset": model, "status": "closed"}
