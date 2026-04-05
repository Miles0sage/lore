"""Tiered model routing and lightweight telemetry for Lore."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from .config import get_router_log_path

MODEL_PROFILES = {
    "deepseek-chat": {
        "tier": "light",
        "role": "delegated triage and extraction",
        "strengths": ["bulk extraction", "duplicate detection", "cheap background work"],
    },
    "gpt-4.1": {
        "tier": "default",
        "role": "daily operator work",
        "strengths": ["standard drafting", "briefs", "routine operator loops"],
    },
    "gpt-5.4": {
        "tier": "high",
        "role": "high-judgment review",
        "strengths": ["security review", "merge decisions", "architecture judgment"],
    },
}

TASK_MODEL_MAP = {
    "light": "deepseek-chat",
    "standard": "gpt-4.1",
    "high": "gpt-5.4",
}

ESCALATION_KEYWORDS = {
    "security",
    "threat",
    "architecture",
    "merge",
    "publish",
    "canon",
    "final",
    "review",
    "deployment",
    "sandbox",
    "governance",
}

LIGHT_KEYWORDS = {
    "extract",
    "classify",
    "triage",
    "dedupe",
    "duplicate",
    "summarize",
    "source-pack",
    "tag",
    "queue",
    "proposal",
}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def classify_task(task_type: str = "", description: str = "") -> dict[str, Any]:
    text = " ".join(part for part in [task_type, description] if part).strip()
    tokens = _tokenize(text)

    if tokens & ESCALATION_KEYWORDS:
        complexity = "high"
        reason = "contains high-judgment security/architecture/publish keywords"
    elif tokens & LIGHT_KEYWORDS:
        complexity = "light"
        reason = "matches lightweight extraction/triage keywords"
    else:
        complexity = "standard"
        reason = "default operator workflow task"

    model = TASK_MODEL_MAP[complexity]
    return {
        "task_type": task_type or "general",
        "description": description,
        "complexity": complexity,
        "model": model,
        "reason": reason,
        "profile": MODEL_PROFILES[model],
    }


def log_router_event(
    *,
    task_type: str,
    model: str,
    status: str,
    description: str = "",
    latency_s: float | None = None,
    cost_usd: float | None = None,
    accepted: bool | None = None,
    revised: bool | None = None,
    error: str = "",
) -> dict[str, Any]:
    event = {
        "ts": _utc_now(),
        "task_type": task_type,
        "description": description,
        "model": model,
        "status": status,
        "latency_s": None if latency_s is None else round(float(latency_s), 3),
        "cost_usd": None if cost_usd is None else round(float(cost_usd), 6),
        "accepted": accepted,
        "revised": revised,
        "error": error,
    }

    path = get_router_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def read_router_events(limit: int = 200) -> list[dict[str, Any]]:
    path = get_router_log_path()
    if not path.exists():
        return []

    rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    events: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        row = row.strip()
        if not row:
            continue
        try:
            events.append(json.loads(row))
        except json.JSONDecodeError:
            continue
    return events


def build_router_status(limit: int = 200) -> dict[str, Any]:
    events = read_router_events(limit=limit)
    by_model: dict[str, dict[str, Any]] = {}
    dlq_counter: Counter[str] = Counter()

    for event in events:
        model = str(event.get("model", "unknown"))
        status = str(event.get("status", "unknown"))
        bucket = by_model.setdefault(
            model,
            {
                "events": 0,
                "accepted": 0,
                "revised": 0,
                "failures": 0,
                "latencies": [],
                "costs": [],
            },
        )
        bucket["events"] += 1
        if event.get("accepted") is True:
            bucket["accepted"] += 1
        if event.get("revised") is True:
            bucket["revised"] += 1
        if status != "ok":
            bucket["failures"] += 1
            dlq_counter[str(event.get("task_type", "unknown"))] += 1
        if event.get("latency_s") is not None:
            bucket["latencies"].append(float(event["latency_s"]))
        if event.get("cost_usd") is not None:
            bucket["costs"].append(float(event["cost_usd"]))

    model_stats = {}
    for model, bucket in by_model.items():
        events_count = bucket["events"] or 1
        model_stats[model] = {
            "events": bucket["events"],
            "accepted_rate": round(bucket["accepted"] / events_count, 3),
            "revision_rate": round(bucket["revised"] / events_count, 3),
            "failure_rate": round(bucket["failures"] / events_count, 3),
            "avg_latency_s": round(sum(bucket["latencies"]) / len(bucket["latencies"]), 3) if bucket["latencies"] else None,
            "total_cost_usd": round(sum(bucket["costs"]), 6) if bucket["costs"] else 0.0,
        }

    return {
        "log_path": str(get_router_log_path()),
        "event_count": len(events),
        "models": model_stats,
        "dead_letter_queue": [{"task_type": task_type, "count": count} for task_type, count in dlq_counter.most_common(10)],
        "recommended_default": "gpt-4.1",
        "recommended_high_judgment": "gpt-5.4",
        "recommended_lightweight": "deepseek-chat",
    }

