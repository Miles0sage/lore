"""Tests for distill.py — trajectory distillation (no API calls)."""

from __future__ import annotations

import json

import pytest

from lore import distill


@pytest.fixture()
def tdir(tmp_path):
    """Provide a temp directory for trajectories.jsonl."""
    return tmp_path


def _success_result(task_type: str = "triage", model: str = "deepseek-chat", cost: float = 0.001) -> dict:
    return {
        "model": model,
        "task_type": task_type,
        "content": "ok",
        "latency_s": 1.2,
        "cost_usd": cost,
        "usage": {"prompt": 100, "completion": 50},
        "routing": {},
        "escalated_from": None,
    }


class TestCaptureTrajectory:
    def test_captures_and_persists(self, tdir):
        result = _success_result()
        traj = distill.capture_trajectory(result, base=tdir)

        assert traj["task_type"] == "triage"
        assert traj["model"] == "deepseek-chat"
        assert traj["success"] is True
        assert traj["prompt_tokens"] == 100
        assert traj["completion_tokens"] == 50

        # Check file was written
        path = tdir / "trajectories.jsonl"
        assert path.exists()
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["task_type"] == "triage"

    def test_captures_escalation(self, tdir):
        result = _success_result()
        result["escalated_from"] = "deepseek-chat"
        result["model"] = "gpt-4.1"
        traj = distill.capture_trajectory(result, base=tdir)
        assert traj["escalated_from"] == "deepseek-chat"

    def test_multiple_appends(self, tdir):
        for _ in range(3):
            distill.capture_trajectory(_success_result(), base=tdir)
        lines = (tdir / "trajectories.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3


class TestDistillSuccess:
    def test_returns_none_on_insufficient_data(self, tdir):
        distill.capture_trajectory(_success_result(), base=tdir)
        result = distill.distill_success({"task_type": "triage"}, base=tdir)
        assert result is None

    def test_identifies_cheap_model_wins(self, tdir):
        for _ in range(4):
            distill.capture_trajectory(_success_result("triage", "deepseek-chat"), base=tdir)
        rule = distill.distill_success({"task_type": "triage"}, base=tdir)
        assert rule is not None
        assert rule["rule_type"] == "downgrade_to_cheaper"
        assert rule["suggested_model"] == "deepseek-chat"
        assert rule["evidence_count"] >= 3

    def test_identifies_always_escalates(self, tdir):
        for _ in range(3):
            result = _success_result("security_review", "gpt-5.4")
            result["escalated_from"] = "gpt-4.1"
            distill.capture_trajectory(result, base=tdir)
        rule = distill.distill_success({"task_type": "security_review"}, base=tdir)
        assert rule is not None
        assert rule["rule_type"] == "pin_to_higher_tier"
        assert rule["suggested_model"] == "gpt-5.4"

    def test_no_rule_when_mixed_results(self, tdir):
        # 2 successes on cheap, 1 failure — not enough for rule
        for _ in range(2):
            distill.capture_trajectory(_success_result("mixed", "deepseek-chat"), base=tdir)
        fail = _success_result("mixed", "deepseek-chat")
        fail["error"] = "boom"
        distill.capture_trajectory(fail, base=tdir)
        result = distill.distill_success({"task_type": "mixed"}, base=tdir)
        # Only 2 successes on deepseek, need 3
        assert result is None


class TestDistillationReport:
    def test_empty_report(self, tdir):
        report = distill.get_distillation_report(base=tdir)
        assert report["trajectory_count"] == 0
        assert report["task_types"] == {}

    def test_groups_by_task_type(self, tdir):
        for _ in range(3):
            distill.capture_trajectory(_success_result("triage", "deepseek-chat"), base=tdir)
        for _ in range(2):
            distill.capture_trajectory(_success_result("review", "gpt-5.4"), base=tdir)

        report = distill.get_distillation_report(limit=100, base=tdir)
        assert report["trajectory_count"] == 5
        assert "triage" in report["task_types"]
        assert "review" in report["task_types"]
        assert report["task_types"]["triage"]["total_trajectories"] == 3
        assert "deepseek-chat" in report["task_types"]["triage"]["models"]

    def test_report_includes_optimizations(self, tdir):
        for _ in range(4):
            distill.capture_trajectory(_success_result("triage", "deepseek-chat"), base=tdir)
        report = distill.get_distillation_report(limit=100, base=tdir)
        assert len(report["optimizations"]) > 0
        assert report["optimizations"][0]["task_type"] == "triage"
