"""Tests for rejection_tracker.py."""

from __future__ import annotations

import pytest
from lore import rejection_tracker


@pytest.fixture(autouse=True)
def patch_log_path(tmp_path, monkeypatch):
    log = tmp_path / ".lore" / "rejection_log.jsonl"
    monkeypatch.setattr(rejection_tracker, "_log_path", lambda: log)
    yield log


class TestRecordRejection:
    def test_creates_file_and_record(self, patch_log_path):
        entry = rejection_tracker.record_rejection("p1", "Circuit Breaker Pattern")
        assert patch_log_path.exists()
        assert entry["title"] == "Circuit Breaker Pattern"
        assert "circuit" in entry["tokens"]

    def test_appends_multiple(self, patch_log_path):
        rejection_tracker.record_rejection("p1", "Circuit Breaker")
        rejection_tracker.record_rejection("p2", "Dead Letter Queue")
        records = rejection_tracker.load_rejections()
        assert len(records) == 2

    def test_stores_reason_and_reviewer(self, patch_log_path):
        rejection_tracker.record_rejection("p1", "Test", reason="too vague", reviewer="ops")
        records = rejection_tracker.load_rejections()
        assert records[0]["reason"] == "too vague"
        assert records[0]["reviewer"] == "ops"


class TestIsSimilar:
    def test_exact_match_detected(self, patch_log_path):
        rejection_tracker.record_rejection("p1", "Circuit Breaker Pattern for AI Agents")
        found, matched = rejection_tracker.is_rejected_topic("Circuit Breaker Pattern for AI Agents")
        assert found is True
        assert "Circuit Breaker" in matched

    def test_partial_overlap_above_threshold(self, patch_log_path):
        # 4 shared tokens out of 5 union = 0.8 jaccard > 0.55 threshold
        rejection_tracker.record_rejection("p1", "circuit breaker pattern reliability agent")
        found, _ = rejection_tracker.is_rejected_topic("circuit breaker pattern reliability tool")
        assert found is True

    def test_unrelated_title_not_matched(self, patch_log_path):
        rejection_tracker.record_rejection("p1", "circuit breaker pattern")
        found, _ = rejection_tracker.is_rejected_topic("memory stack episodic retrieval")
        assert found is False

    def test_empty_log_returns_false(self, patch_log_path):
        found, matched = rejection_tracker.is_rejected_topic("anything")
        assert found is False
        assert matched == ""


class TestRejectionSummary:
    def test_empty_log_returns_empty(self, patch_log_path):
        assert rejection_tracker.rejection_summary() == ""

    def test_summary_includes_titles(self, patch_log_path):
        rejection_tracker.record_rejection("p1", "Circuit Breaker Noise")
        rejection_tracker.record_rejection("p2", "Low Quality Article")
        summary = rejection_tracker.rejection_summary()
        assert "Circuit Breaker Noise" in summary
        assert "Low Quality Article" in summary
        assert "Previously rejected" in summary
