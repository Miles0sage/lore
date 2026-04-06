"""Tests for router_learner — self-rewriting router engine."""

import json
from pathlib import Path

from lore import router_learner, routing


def _write_events(workspace: Path, events: list[dict]) -> None:
    log_path = workspace / ".lore" / "router_events.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def _write_rules(workspace: Path, rules: dict) -> None:
    rules_path = workspace / ".lore" / "routing_rules.json"
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text(json.dumps(rules, indent=2), encoding="utf-8")


def _fake_dispatch_ok(task_type, prompt, *, system="", description="", max_tokens=1024):
    """Mock dispatch that returns a valid JSON response with one keyword move."""
    response = {
        "light_keywords": ["classify", "dedupe", "duplicate", "extract", "proposal", "queue", "source-pack", "summarize", "tag", "triage"],
        "escalation_keywords": ["architecture", "canon", "deployment", "final", "governance", "merge", "publish", "review", "sandbox", "security", "threat"],
        "task_overrides": {},
        "changes": [
            {"action": "move", "keyword": "hard_task", "from": "light", "to": "escalation", "reason": "high failure rate on cheap tier"}
        ],
    }
    return {
        "model": "gpt-5.4",
        "content": json.dumps(response),
        "latency_s": 1.5,
        "cost_usd": 0.01,
    }


def _fake_dispatch_error(task_type, prompt, *, system="", description="", max_tokens=1024):
    return {"error": "all_circuits_open"}


def _fake_dispatch_bad_json(task_type, prompt, *, system="", description="", max_tokens=1024):
    return {
        "model": "gpt-5.4",
        "content": "This is not JSON at all, sorry!",
        "latency_s": 1.0,
        "cost_usd": 0.005,
    }


def test_learn_skips_when_no_events(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    result = router_learner.learn_from_telemetry(dispatch_fn=_fake_dispatch_ok)
    assert result["status"] == "skipped"
    assert "No router events" in result["reason"]


def test_learn_calls_dispatch_and_saves_rules(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    events = [
        {"model": "deepseek-chat", "task_type": "triage", "status": "ok", "accepted": True, "latency_s": 0.5},
        {"model": "deepseek-chat", "task_type": "triage", "status": "error", "latency_s": 0.3},
        {"model": "gpt-5.4", "task_type": "canon_review", "status": "ok", "accepted": True, "latency_s": 2.0},
    ]
    _write_events(workspace, events)

    result = router_learner.learn_from_telemetry(dispatch_fn=_fake_dispatch_ok)

    assert result["status"] == "ok"
    assert result["change_count"] >= 0

    # Verify rules file was written
    rules_path = workspace / ".lore" / "routing_rules.json"
    assert rules_path.exists()
    saved = json.loads(rules_path.read_text())
    assert "light_keywords" in saved
    assert "escalation_keywords" in saved
    assert "updated_at" in saved


def test_learn_handles_dispatch_error(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    events = [
        {"model": "deepseek-chat", "task_type": "triage", "status": "ok", "accepted": True},
    ]
    _write_events(workspace, events)

    result = router_learner.learn_from_telemetry(dispatch_fn=_fake_dispatch_error)
    assert result["status"] == "error"
    assert "Dispatch failed" in result["reason"]


def test_learn_handles_bad_json_response(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    events = [
        {"model": "deepseek-chat", "task_type": "triage", "status": "ok", "accepted": True},
    ]
    _write_events(workspace, events)

    result = router_learner.learn_from_telemetry(dispatch_fn=_fake_dispatch_bad_json)
    assert result["status"] == "error"
    assert "parse" in result["reason"].lower()


def test_safety_gate_caps_changes():
    current = routing._default_routing_rules()

    # Propose 5 changes — should be capped to 3
    proposed = {
        "light_keywords": ["extract", "classify"],
        "escalation_keywords": ["security", "threat", "architecture", "merge", "publish", "canon", "final", "review", "deployment", "sandbox", "governance", "new1", "new2", "new3", "new4", "new5"],
        "task_overrides": {},
        "changes": [
            {"action": "add", "keyword": "new1", "to": "escalation", "reason": "r1"},
            {"action": "add", "keyword": "new2", "to": "escalation", "reason": "r2"},
            {"action": "add", "keyword": "new3", "to": "escalation", "reason": "r3"},
            {"action": "add", "keyword": "new4", "to": "escalation", "reason": "r4"},
            {"action": "add", "keyword": "new5", "to": "escalation", "reason": "r5"},
        ],
    }

    safe, warnings = router_learner._apply_safety_gate(current, proposed)
    assert len(warnings) > 0
    changes_applied = safe.get("changes", [])
    assert len(changes_applied) <= 3


def test_learn_creates_backup(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    # Pre-seed existing rules
    _write_rules(workspace, {
        "version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "updated_by": "test",
        "light_keywords": ["extract", "triage"],
        "escalation_keywords": ["security"],
        "task_overrides": {},
    })

    events = [
        {"model": "deepseek-chat", "task_type": "triage", "status": "ok", "accepted": True},
    ]
    _write_events(workspace, events)

    result = router_learner.learn_from_telemetry(dispatch_fn=_fake_dispatch_ok)
    assert result["status"] == "ok"
    assert result["backup_path"] is not None
    assert Path(result["backup_path"]).exists()


def test_routing_rules_json_fallback(monkeypatch, tmp_path: Path):
    """classify_task uses hardcoded defaults when no JSON file exists."""
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    # No routing_rules.json — should fall back to hardcoded defaults
    result = routing.classify_task("security_arch", "review deployment sandbox security")
    assert result["model"] == "gpt-5.4"

    result = routing.classify_task("proposal_triage", "extract duplicates")
    assert result["model"] == "deepseek-chat"


def test_routing_rules_json_override(monkeypatch, tmp_path: Path):
    """classify_task reads from JSON when it exists."""
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    # Write custom rules where "security" is a light keyword (unusual but tests the mechanism)
    _write_rules(workspace, {
        "version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "updated_by": "test",
        "light_keywords": ["security"],
        "escalation_keywords": ["triage"],
        "task_overrides": {},
    })

    result = routing.classify_task("security_scan", "security check")
    assert result["model"] == "deepseek-chat"
    assert result["complexity"] == "light"

    result = routing.classify_task("triage_queue", "triage items")
    assert result["model"] == "gpt-5.4"
    assert result["complexity"] == "high"


def test_task_overrides(monkeypatch, tmp_path: Path):
    """task_overrides pin specific task_types to a tier."""
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    _write_rules(workspace, {
        "version": 1,
        "updated_at": "2026-01-01T00:00:00Z",
        "updated_by": "test",
        "light_keywords": ["extract"],
        "escalation_keywords": ["security"],
        "task_overrides": {"special_task": "high"},
    })

    result = routing.classify_task("special_task", "do something")
    assert result["model"] == "gpt-5.4"
    assert result["complexity"] == "high"
    assert "task_override" in result["reason"]


def test_parse_llm_response_with_markdown_fences():
    """LLM response wrapped in ```json fences should parse correctly."""
    raw = '```json\n{"light_keywords": ["a"], "escalation_keywords": ["b"], "changes": []}\n```'
    parsed = router_learner._parse_llm_response(raw)
    assert parsed is not None
    assert parsed["light_keywords"] == ["a"]


def test_parse_llm_response_plain_json():
    raw = '{"light_keywords": ["a"], "escalation_keywords": ["b"], "changes": []}'
    parsed = router_learner._parse_llm_response(raw)
    assert parsed is not None


def test_parse_llm_response_garbage():
    parsed = router_learner._parse_llm_response("not json at all")
    assert parsed is None
