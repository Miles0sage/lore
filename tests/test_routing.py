from pathlib import Path

from lore import routing


def test_classify_task_routes_light_standard_and_high():
    light = routing.classify_task("proposal_triage", "extract duplicates and triage the queue")
    standard = routing.classify_task("morning_brief", "prepare the operator brief")
    high = routing.classify_task("security_arch", "review deployment sandbox security and publish gate")

    assert light["model"] == "deepseek-chat"
    assert standard["model"] == "gpt-4.1"
    assert high["model"] == "gpt-5.4"


def test_router_telemetry_aggregates_recent_events(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    routing.log_router_event(task_type="proposal_triage", model="deepseek-chat", status="ok", accepted=True, latency_s=0.5, cost_usd=0.0001)
    routing.log_router_event(task_type="proposal_triage", model="deepseek-chat", status="error", error="bad_json", revised=True)
    routing.log_router_event(task_type="canon_review", model="gpt-5.4", status="ok", accepted=True, latency_s=1.2, cost_usd=0.01)

    status = routing.build_router_status(limit=20)

    assert status["event_count"] == 3
    assert status["models"]["deepseek-chat"]["events"] == 2
    assert status["models"]["gpt-5.4"]["accepted_rate"] == 1.0
    assert status["dead_letter_queue"][0]["task_type"] == "proposal_triage"
