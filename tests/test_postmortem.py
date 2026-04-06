"""Tests for postmortem.py — auto-postmortem generation (no API calls)."""

from __future__ import annotations

import json

import pytest

from lore import postmortem


@pytest.fixture()
def tdir(tmp_path):
    """Provide a temp directory for postmortems.jsonl."""
    return tmp_path


def _error_result(
    task_type: str = "triage",
    model: str = "deepseek-chat",
    error: str = "Connection timed out",
) -> dict:
    return {
        "error": error,
        "model": model,
        "task_type": task_type,
        "circuit_failure_count": 1,
        "circuit_threshold": 3,
    }


class TestClassifyFailure:
    @pytest.mark.parametrize(
        "error,expected",
        [
            ("Connection timed out", "timeout"),
            ("Request timed out after 30s", "timeout"),
            ("429 Too Many Requests", "rate_limit"),
            ("Rate limit exceeded", "rate_limit"),
            ("401 Unauthorized", "auth_error"),
            ("Invalid API key provided", "auth_error"),
            ("500 Internal Server Error", "api_error"),
            ("502 Bad Gateway", "api_error"),
            ("Model context length exceeded", "model_error"),
            ("all_circuits_open", "circuit_open"),
            ("circuit_open:deepseek-chat", "circuit_open"),
            ("something completely random", "unknown"),
        ],
    )
    def test_classifies_correctly(self, error, expected):
        assert postmortem.classify_failure(error) == expected


class TestGeneratePostmortem:
    def test_generates_and_persists(self, tdir):
        result = _error_result()
        pm = postmortem.generate_postmortem(result, base=tdir)

        assert pm["task_type"] == "triage"
        assert pm["model"] == "deepseek-chat"
        assert pm["failure_class"] == "timeout"
        assert pm["error"] == "Connection timed out"
        assert "incident_id" in pm
        assert "ts" in pm
        assert "suggested_action" in pm
        assert pm["circuit_breaker_state"]["failure_count"] == 1

        path = tdir / "postmortems.jsonl"
        assert path.exists()
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_circuit_open_postmortem(self, tdir):
        result = {
            "error": "all_circuits_open",
            "task_type": "security_review",
            "message": "All model tiers are circuit-open.",
            "failure_counts": {"deepseek-chat": 3, "gpt-4.1": 3, "gpt-5.4": 3},
        }
        pm = postmortem.generate_postmortem(result, base=tdir)
        assert pm["failure_class"] == "circuit_open"

    def test_multiple_postmortems_append(self, tdir):
        for _ in range(3):
            postmortem.generate_postmortem(_error_result(), base=tdir)
        lines = (tdir / "postmortems.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3


class TestPostmortemReport:
    def test_empty_report(self, tdir):
        report = postmortem.get_postmortem_report(base=tdir)
        assert report["postmortem_count"] == 0
        assert report["failure_classes"] == {}

    def test_groups_by_failure_class(self, tdir):
        postmortem.generate_postmortem(_error_result(error="Connection timed out"), base=tdir)
        postmortem.generate_postmortem(_error_result(error="429 rate limit"), base=tdir)
        postmortem.generate_postmortem(_error_result(error="Read timed out"), base=tdir)

        report = postmortem.get_postmortem_report(base=tdir)
        assert report["postmortem_count"] == 3
        assert "timeout" in report["failure_classes"]
        assert report["failure_classes"]["timeout"]["count"] == 2
        assert "rate_limit" in report["failure_classes"]

    def test_report_includes_top_task_types(self, tdir):
        for _ in range(3):
            postmortem.generate_postmortem(
                _error_result(task_type="triage", error="timed out"), base=tdir,
            )
        report = postmortem.get_postmortem_report(base=tdir)
        timeout_stats = report["failure_classes"]["timeout"]
        assert ("triage", 3) in timeout_stats["top_task_types"]


class TestGenerateDefensiveRule:
    def test_generates_rule_with_enough_evidence(self, tdir):
        for _ in range(4):
            postmortem.generate_postmortem(
                _error_result(task_type="security_review", model="deepseek-chat", error="timed out"),
                base=tdir,
            )
        pm = _error_result(task_type="security_review", model="deepseek-chat", error="timed out")
        pm["failure_class"] = "timeout"
        rule = postmortem.generate_defensive_rule(pm, base=tdir)
        assert rule is not None
        assert "security_review" in rule
        assert "deepseek-chat" in rule
        assert "failed" in rule

    def test_returns_none_with_insufficient_evidence(self, tdir):
        postmortem.generate_postmortem(
            _error_result(task_type="triage", error="timed out"), base=tdir,
        )
        pm = {"task_type": "triage", "model": "deepseek-chat", "failure_class": "timeout"}
        rule = postmortem.generate_defensive_rule(pm, base=tdir)
        assert rule is None

    def test_defensive_rules_in_report(self, tdir):
        for _ in range(4):
            postmortem.generate_postmortem(
                _error_result(task_type="extract", model="gpt-4.1", error="500 server error"),
                base=tdir,
            )
        report = postmortem.get_postmortem_report(base=tdir)
        assert len(report["defensive_rules"]) > 0
        assert "extract" in report["defensive_rules"][0]
