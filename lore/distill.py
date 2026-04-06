"""Trajectory distillation — learn routing rules from successful dispatches.

When a dispatched task succeeds, capture the execution trajectory and distill
it into a learned routing rule or procedural insight.  Pure offline analysis,
no API calls.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_telemetry_dir

_MIN_SUCCESSES_FOR_RULE = 3


def _trajectories_path(base: Path | None = None) -> Path:
    d = base if base is not None else get_telemetry_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "trajectories.jsonl"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def capture_trajectory(dispatch_result: dict[str, Any], *, base: Path | None = None) -> dict[str, Any]:
    """Extract a trajectory record from a dispatch result and persist it.

    Args:
        dispatch_result: The dict returned by dispatch.dispatch_task on success.
        base: Override for the telemetry directory (used by tests).

    Returns:
        The trajectory record that was appended to trajectories.jsonl.
    """
    usage = dispatch_result.get("usage") or {}
    trajectory: dict[str, Any] = {
        "ts": _utc_now(),
        "task_type": dispatch_result.get("task_type", "unknown"),
        "model": dispatch_result.get("model", "unknown"),
        "latency_s": dispatch_result.get("latency_s"),
        "cost_usd": dispatch_result.get("cost_usd"),
        "prompt_tokens": usage.get("prompt", 0),
        "completion_tokens": usage.get("completion", 0),
        "escalated_from": dispatch_result.get("escalated_from"),
        "success": "error" not in dispatch_result,
    }

    path = _trajectories_path(base)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(trajectory, sort_keys=True) + "\n")

    return trajectory


def _read_trajectories(limit: int, base: Path | None = None) -> list[dict[str, Any]]:
    path = _trajectories_path(base)
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


def distill_success(trajectory: dict[str, Any], *, base: Path | None = None) -> dict[str, Any] | None:
    """Analyze trajectory history and suggest a routing rule if patterns emerge.

    Rules:
    - If a task_type succeeds on a cheaper model 3+ times, suggest pinning it there.
    - If a task_type always escalates, suggest pinning to the higher tier.

    Returns a suggested rule dict or None.
    """
    task_type = trajectory.get("task_type", "unknown")
    trajectories = _read_trajectories(500, base=base)

    # Filter to same task_type
    same_type = [t for t in trajectories if t.get("task_type") == task_type]
    if len(same_type) < _MIN_SUCCESSES_FOR_RULE:
        return None

    # Group successes by model
    model_successes: dict[str, int] = defaultdict(int)
    model_total: dict[str, int] = defaultdict(int)
    escalation_count = 0

    for t in same_type:
        model = t.get("model", "unknown")
        model_total[model] += 1
        if t.get("success"):
            model_successes[model] += 1
        if t.get("escalated_from"):
            escalation_count += 1

    # Check if always escalates
    if escalation_count == len(same_type) and len(same_type) >= _MIN_SUCCESSES_FOR_RULE:
        # Find the most common escalation target
        target_models = [t.get("model") for t in same_type if t.get("escalated_from")]
        if target_models:
            from collections import Counter
            most_common_target = Counter(target_models).most_common(1)[0][0]
            return {
                "rule_type": "pin_to_higher_tier",
                "task_type": task_type,
                "suggested_model": most_common_target,
                "reason": f"Task '{task_type}' always escalates ({escalation_count}/{len(same_type)}). Pin directly.",
                "evidence_count": len(same_type),
            }

    # Check if cheaper model works well
    tier_order = ["deepseek-chat", "gpt-4.1", "gpt-5.4"]
    for cheap_model in tier_order[:-1]:
        successes = model_successes.get(cheap_model, 0)
        if successes >= _MIN_SUCCESSES_FOR_RULE:
            total = model_total.get(cheap_model, 0)
            success_rate = successes / max(total, 1)
            if success_rate >= 0.8:
                return {
                    "rule_type": "downgrade_to_cheaper",
                    "task_type": task_type,
                    "suggested_model": cheap_model,
                    "reason": (
                        f"Task '{task_type}' succeeds {successes}/{total} times "
                        f"({success_rate:.0%}) on {cheap_model}. Route there to save cost."
                    ),
                    "evidence_count": total,
                    "success_rate": round(success_rate, 4),
                }

    return None


def get_distillation_report(limit: int = 100, *, base: Path | None = None) -> dict[str, Any]:
    """Build a distillation report from recent trajectories.

    Groups by task_type with per-model stats and optimization suggestions.
    """
    trajectories = _read_trajectories(limit, base=base)
    if not trajectories:
        return {
            "trajectory_count": 0,
            "task_types": {},
            "optimizations": [],
        }

    # Group by task_type
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in trajectories:
        by_type[t.get("task_type", "unknown")].append(t)

    task_stats: dict[str, Any] = {}
    optimizations: list[dict[str, Any]] = []

    for task_type, entries in by_type.items():
        model_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"successes": 0, "total": 0, "total_cost": 0.0, "total_latency": 0.0}
        )
        for entry in entries:
            model = entry.get("model", "unknown")
            md = model_data[model]
            md["total"] += 1
            if entry.get("success"):
                md["successes"] += 1
            if entry.get("cost_usd") is not None:
                md["total_cost"] += float(entry["cost_usd"])
            if entry.get("latency_s") is not None:
                md["total_latency"] += float(entry["latency_s"])

        per_model = {}
        for model, md in model_data.items():
            total = md["total"] or 1
            per_model[model] = {
                "success_rate": round(md["successes"] / total, 4),
                "total": md["total"],
                "avg_cost_usd": round(md["total_cost"] / total, 6),
                "avg_latency_s": round(md["total_latency"] / total, 3),
            }

        task_stats[task_type] = {
            "total_trajectories": len(entries),
            "models": per_model,
        }

        # Check for optimization opportunity
        suggestion = distill_success({"task_type": task_type}, base=base)
        if suggestion:
            optimizations.append(suggestion)

    return {
        "trajectory_count": len(trajectories),
        "task_types": task_stats,
        "optimizations": optimizations,
    }
