"""Routing evaluation engine — scores routing quality from telemetry.

Reads .lore/router_events.jsonl and produces a structured eval report
with per-model stats and misrouting suggestions. Pure offline analysis,
no API calls required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import get_telemetry_dir
from .routing import MODEL_PROFILES, TASK_MODEL_MAP, read_router_events


@dataclass(frozen=True)
class ModelStats:
    model: str
    tier: str
    events: int
    failures: int
    escalations: int
    acceptances: int
    revisions: int
    total_latency_s: float
    total_cost_usd: float

    @property
    def failure_rate(self) -> float:
        return round(self.failures / max(self.events, 1), 4)

    @property
    def escalation_rate(self) -> float:
        return round(self.escalations / max(self.events, 1), 4)

    @property
    def acceptance_rate(self) -> float:
        return round(self.acceptances / max(self.events, 1), 4)

    @property
    def revision_rate(self) -> float:
        return round(self.revisions / max(self.events, 1), 4)

    @property
    def avg_latency_s(self) -> float | None:
        if self.events == 0:
            return None
        return round(self.total_latency_s / self.events, 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "tier": self.tier,
            "events": self.events,
            "failure_rate": self.failure_rate,
            "escalation_rate": self.escalation_rate,
            "acceptance_rate": self.acceptance_rate,
            "revision_rate": self.revision_rate,
            "avg_latency_s": self.avg_latency_s,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }


@dataclass(frozen=True)
class KeywordSuggestion:
    keyword: str
    current_tier: str
    suggested_tier: str
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "current_tier": self.current_tier,
            "suggested_tier": self.suggested_tier,
            "reason": self.reason,
            "confidence": round(self.confidence, 2),
        }


def _tier_for_model(model: str) -> str:
    profile = MODEL_PROFILES.get(model)
    if profile:
        return profile["tier"]
    return "unknown"


def _model_for_tier(tier: str) -> str:
    return TASK_MODEL_MAP.get(tier, "gpt-4.1")


def _collect_model_stats(events: list[dict[str, Any]]) -> dict[str, ModelStats]:
    """Aggregate events into per-model stats."""
    buckets: dict[str, dict[str, Any]] = {}

    for event in events:
        model = str(event.get("model", "unknown"))
        b = buckets.setdefault(model, {
            "events": 0,
            "failures": 0,
            "escalations": 0,
            "acceptances": 0,
            "revisions": 0,
            "total_latency_s": 0.0,
            "total_cost_usd": 0.0,
        })
        b["events"] += 1
        status = str(event.get("status", ""))
        if status == "error":
            b["failures"] += 1
        if status == "escalated":
            b["escalations"] += 1
        if event.get("accepted") is True:
            b["acceptances"] += 1
        if event.get("revised") is True:
            b["revisions"] += 1
        if event.get("latency_s") is not None:
            b["total_latency_s"] += float(event["latency_s"])
        if event.get("cost_usd") is not None:
            b["total_cost_usd"] += float(event["cost_usd"])

    return {
        model: ModelStats(
            model=model,
            tier=_tier_for_model(model),
            events=b["events"],
            failures=b["failures"],
            escalations=b["escalations"],
            acceptances=b["acceptances"],
            revisions=b["revisions"],
            total_latency_s=b["total_latency_s"],
            total_cost_usd=b["total_cost_usd"],
        )
        for model, b in buckets.items()
    }


def _collect_task_stats(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-task_type stats: which model handled it and outcomes."""
    tasks: dict[str, dict[str, Any]] = {}

    for event in events:
        tt = str(event.get("task_type", "unknown"))
        model = str(event.get("model", "unknown"))
        status = str(event.get("status", ""))
        t = tasks.setdefault(tt, {
            "models_used": {},
            "total": 0,
            "failures": 0,
            "escalations": 0,
            "acceptances": 0,
        })
        t["total"] += 1
        t["models_used"][model] = t["models_used"].get(model, 0) + 1
        if status == "error":
            t["failures"] += 1
        if status == "escalated":
            t["escalations"] += 1
        if event.get("accepted") is True:
            t["acceptances"] += 1

    return tasks


def _identify_misroutes(
    task_stats: dict[str, dict[str, Any]],
) -> list[KeywordSuggestion]:
    """Find tasks that were sent to the wrong tier."""
    suggestions: list[KeywordSuggestion] = []

    tier_order = ["light", "default", "high"]

    for task_type, stats in task_stats.items():
        total = stats["total"]
        if total < 2:
            continue

        failures = stats["failures"]
        escalations = stats["escalations"]
        acceptances = stats["acceptances"]

        failure_rate = failures / total
        escalation_rate = escalations / total
        acceptance_rate = acceptances / max(total, 1)

        # Find the primary model used
        primary_model = max(stats["models_used"], key=stats["models_used"].get)
        primary_tier = _tier_for_model(primary_model)

        # "too_weak": high failure/escalation on cheap tiers
        if primary_tier in ("light", "default") and (failure_rate > 0.3 or escalation_rate > 0.3):
            tier_idx = tier_order.index(primary_tier) if primary_tier in tier_order else 0
            next_tier = tier_order[min(tier_idx + 1, len(tier_order) - 1)]
            confidence = min(0.9, (failure_rate + escalation_rate) / 2 + 0.2)
            suggestions.append(KeywordSuggestion(
                keyword=task_type,
                current_tier=primary_tier,
                suggested_tier=next_tier,
                reason=f"too_weak: failure_rate={failure_rate:.2f} escalation_rate={escalation_rate:.2f}",
                confidence=round(confidence, 2),
            ))

        # "overpowered": 100% acceptance on expensive tier, could go cheaper
        if primary_tier == "high" and acceptance_rate == 1.0 and failures == 0 and total >= 3:
            suggestions.append(KeywordSuggestion(
                keyword=task_type,
                current_tier="high",
                suggested_tier="default",
                reason=f"overpowered: 100% acceptance on high tier over {total} events, no failures",
                confidence=0.6,
            ))

        if primary_tier == "default" and acceptance_rate == 1.0 and failures == 0 and total >= 3:
            suggestions.append(KeywordSuggestion(
                keyword=task_type,
                current_tier="default",
                suggested_tier="light",
                reason=f"overpowered: 100% acceptance on default tier over {total} events, no failures",
                confidence=0.5,
            ))

    return suggestions


def build_eval_report(limit: int = 500) -> dict[str, Any]:
    """Build a full eval report from router telemetry.

    Returns a dict with per-model stats, per-task stats, misrouting
    suggestions, and metadata. No API calls — pure offline analysis.
    """
    events = read_router_events(limit=limit)

    model_stats = _collect_model_stats(events)
    task_stats = _collect_task_stats(events)
    suggestions = _identify_misroutes(task_stats)

    return {
        "event_count": len(events),
        "model_stats": {m: s.to_dict() for m, s in model_stats.items()},
        "task_stats": {
            tt: {
                "total": s["total"],
                "failure_rate": round(s["failures"] / max(s["total"], 1), 4),
                "escalation_rate": round(s["escalations"] / max(s["total"], 1), 4),
                "acceptance_rate": round(s["acceptances"] / max(s["total"], 1), 4),
                "models_used": s["models_used"],
            }
            for tt, s in task_stats.items()
        },
        "suggestions": [s.to_dict() for s in suggestions],
        "suggestion_count": len(suggestions),
        "telemetry_path": str(get_telemetry_dir() / "router_events.jsonl"),
    }
