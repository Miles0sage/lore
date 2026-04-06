"""Auto-postmortem generation for dispatch failures.

When a dispatch fails or hits the circuit breaker, auto-generate a structured
postmortem with failure classification and defensive rule suggestions.
Pure offline analysis, no API calls.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_telemetry_dir

_FAILURE_KEYWORDS: dict[str, list[str]] = {
    "timeout": ["timeout", "timed out", "deadline exceeded", "read timed out"],
    "rate_limit": ["rate limit", "rate_limit", "429", "too many requests", "quota"],
    "auth_error": ["auth", "unauthorized", "401", "403", "forbidden", "api key", "invalid key"],
    "api_error": ["500", "502", "503", "504", "server error", "internal error", "bad gateway", "service unavailable"],
    "model_error": ["model", "context length", "token limit", "content filter", "invalid model"],
    "circuit_open": ["circuit", "all_circuits_open", "circuit_open"],
}


def _postmortems_path(base: Path | None = None) -> Path:
    d = base if base is not None else get_telemetry_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "postmortems.jsonl"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _make_incident_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_failure(error: str) -> str:
    """Classify an error string into a failure class.

    Returns one of: api_error, timeout, rate_limit, model_error,
    auth_error, circuit_open, unknown.
    """
    lower = error.lower()
    for failure_class, keywords in _FAILURE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return failure_class
    return "unknown"


_SUGGESTED_ACTIONS: dict[str, str] = {
    "timeout": "Increase timeout or reduce prompt size. Consider chunking large inputs.",
    "rate_limit": "Back off and retry with exponential delay. Check quota limits.",
    "auth_error": "Verify API key is set and valid. Check environment variables.",
    "api_error": "Transient server error. Retry after brief delay. If persistent, check provider status page.",
    "model_error": "Check prompt size vs model context window. Verify model name is correct.",
    "circuit_open": "Circuit breaker is open. Wait for cooldown or manually reset with lore_circuit_reset.",
    "unknown": "Unclassified failure. Inspect the raw error message for clues.",
}


def generate_postmortem(
    dispatch_result: dict[str, Any],
    *,
    base: Path | None = None,
) -> dict[str, Any]:
    """Generate a structured postmortem from a failed dispatch result.

    Args:
        dispatch_result: The dict returned by dispatch.dispatch_task (must have "error" key).
        base: Override for the telemetry directory (used by tests).

    Returns:
        The postmortem record that was appended to postmortems.jsonl.
    """
    error_msg = str(dispatch_result.get("error", "unknown error"))
    failure_class = classify_failure(error_msg)

    postmortem: dict[str, Any] = {
        "incident_id": _make_incident_id(),
        "ts": _utc_now(),
        "task_type": dispatch_result.get("task_type", "unknown"),
        "model": dispatch_result.get("model", "unknown"),
        "error": error_msg,
        "failure_class": failure_class,
        "circuit_breaker_state": {
            "failure_count": dispatch_result.get("circuit_failure_count"),
            "threshold": dispatch_result.get("circuit_threshold"),
        },
        "suggested_action": _SUGGESTED_ACTIONS.get(failure_class, _SUGGESTED_ACTIONS["unknown"]),
    }

    path = _postmortems_path(base)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(postmortem, sort_keys=True) + "\n")

    return postmortem


def _read_postmortems(limit: int, base: Path | None = None) -> list[dict[str, Any]]:
    path = _postmortems_path(base)
    if not path.exists():
        return []
    rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        row = row.strip()
        if not row:
            continue
        try:
            out.append(json.loads(row))
        except json.JSONDecodeError:
            continue
    return out


def get_postmortem_report(limit: int = 50, *, base: Path | None = None) -> dict[str, Any]:
    """Build a postmortem report from recent failures.

    Groups by failure_class with counts, common task types, and defensive rules.
    """
    postmortems = _read_postmortems(limit, base=base)
    if not postmortems:
        return {
            "postmortem_count": 0,
            "failure_classes": {},
            "defensive_rules": [],
        }

    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pm in postmortems:
        by_class[pm.get("failure_class", "unknown")].append(pm)

    class_stats: dict[str, Any] = {}
    for fc, entries in by_class.items():
        task_types = Counter(e.get("task_type", "unknown") for e in entries)
        models = Counter(e.get("model", "unknown") for e in entries)
        class_stats[fc] = {
            "count": len(entries),
            "top_task_types": task_types.most_common(5),
            "top_models": models.most_common(3),
            "suggested_action": _SUGGESTED_ACTIONS.get(fc, _SUGGESTED_ACTIONS["unknown"]),
        }

    # Generate defensive rules from patterns
    defensive_rules: list[str] = []
    for pm in postmortems:
        rule = generate_defensive_rule(pm, base=base)
        if rule and rule not in defensive_rules:
            defensive_rules.append(rule)

    return {
        "postmortem_count": len(postmortems),
        "failure_classes": class_stats,
        "defensive_rules": defensive_rules,
    }


def generate_defensive_rule(
    postmortem_record: dict[str, Any],
    *,
    base: Path | None = None,
) -> str | None:
    """Generate a CLAUDE.md-style defensive rule from a postmortem.

    Only generates a rule if there is enough evidence (3+ failures of the
    same task_type on the same model).

    Returns the rule string or None.
    """
    task_type = postmortem_record.get("task_type", "unknown")
    model = postmortem_record.get("model", "unknown")

    all_pms = _read_postmortems(200, base=base)
    same_task_model = [
        pm for pm in all_pms
        if pm.get("task_type") == task_type and pm.get("model") == model
    ]

    if len(same_task_model) < 3:
        return None

    failure_class = postmortem_record.get("failure_class", "unknown")
    return (
        f"When dispatching '{task_type}' tasks, avoid {model} "
        f"-- it has failed {len(same_task_model)} times "
        f"(class: {failure_class}). "
        f"Route to a higher tier directly."
    )
