"""Tests for eval_loop — routing evaluation engine."""

import json
from pathlib import Path

from lore import eval_loop, routing


def _write_events(workspace: Path, events: list[dict]) -> None:
    """Write synthetic router events to the workspace telemetry log."""
    log_path = workspace / ".lore" / "router_events.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def test_empty_telemetry_returns_zero_events(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    report = eval_loop.build_eval_report()
    assert report["event_count"] == 0
    assert report["model_stats"] == {}
    assert report["suggestions"] == []


def test_model_stats_aggregate_correctly(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    events = [
        {"model": "deepseek-chat", "task_type": "triage", "status": "ok", "accepted": True, "latency_s": 0.5, "cost_usd": 0.0001},
        {"model": "deepseek-chat", "task_type": "triage", "status": "error", "error": "bad", "latency_s": 0.3, "cost_usd": 0.0001},
        {"model": "deepseek-chat", "task_type": "extract", "status": "ok", "accepted": True, "latency_s": 0.4, "cost_usd": 0.0002},
        {"model": "gpt-5.4", "task_type": "canon_review", "status": "ok", "accepted": True, "latency_s": 2.0, "cost_usd": 0.01},
    ]
    _write_events(workspace, events)

    report = eval_loop.build_eval_report()

    assert report["event_count"] == 4

    ds = report["model_stats"]["deepseek-chat"]
    assert ds["events"] == 3
    assert ds["failure_rate"] > 0
    assert ds["acceptance_rate"] > 0

    gpt = report["model_stats"]["gpt-5.4"]
    assert gpt["events"] == 1
    assert gpt["acceptance_rate"] == 1.0
    assert gpt["failure_rate"] == 0.0


def test_task_stats_per_task_type(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    events = [
        {"model": "deepseek-chat", "task_type": "triage", "status": "ok", "accepted": True},
        {"model": "deepseek-chat", "task_type": "triage", "status": "error"},
        {"model": "gpt-4.1", "task_type": "brief", "status": "ok", "accepted": True},
    ]
    _write_events(workspace, events)

    report = eval_loop.build_eval_report()

    assert "triage" in report["task_stats"]
    assert report["task_stats"]["triage"]["total"] == 2
    assert report["task_stats"]["brief"]["total"] == 1


def test_too_weak_suggestion(monkeypatch, tmp_path: Path):
    """Tasks failing on cheap tier should suggest escalation."""
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    # 3 events for same task, 2 failures on deepseek = 66% failure rate
    events = [
        {"model": "deepseek-chat", "task_type": "hard_task", "status": "error"},
        {"model": "deepseek-chat", "task_type": "hard_task", "status": "error"},
        {"model": "deepseek-chat", "task_type": "hard_task", "status": "ok", "accepted": True},
    ]
    _write_events(workspace, events)

    report = eval_loop.build_eval_report()
    suggestions = report["suggestions"]

    assert len(suggestions) >= 1
    s = suggestions[0]
    assert s["keyword"] == "hard_task"
    assert "too_weak" in s["reason"]
    assert s["suggested_tier"] in ("default", "high")


def test_overpowered_suggestion(monkeypatch, tmp_path: Path):
    """Tasks with 100% acceptance on expensive tier should suggest demotion."""
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    events = [
        {"model": "gpt-5.4", "task_type": "easy_review", "status": "ok", "accepted": True, "latency_s": 0.5},
        {"model": "gpt-5.4", "task_type": "easy_review", "status": "ok", "accepted": True, "latency_s": 0.4},
        {"model": "gpt-5.4", "task_type": "easy_review", "status": "ok", "accepted": True, "latency_s": 0.6},
    ]
    _write_events(workspace, events)

    report = eval_loop.build_eval_report()
    suggestions = report["suggestions"]

    assert len(suggestions) >= 1
    s = suggestions[0]
    assert s["keyword"] == "easy_review"
    assert "overpowered" in s["reason"]
    assert s["suggested_tier"] == "default"


def test_no_suggestions_for_insufficient_data(monkeypatch, tmp_path: Path):
    """Single events per task should not trigger suggestions."""
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    events = [
        {"model": "deepseek-chat", "task_type": "one_off", "status": "error"},
    ]
    _write_events(workspace, events)

    report = eval_loop.build_eval_report()
    assert report["suggestions"] == []
