"""Tests for lore/observability.py"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lore.observability import (
    ErrorEnvelope,
    ObservabilityHub,
    TokenBudget,
    ToolCallVerifier,
    _set_hub,
    error_rate,
    recent_errors,
    record_error,
    record_success,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_hub(tmp_path: Path) -> ObservabilityHub:
    """Create a fresh ObservabilityHub writing to a temp dir."""
    log_path = tmp_path / ".lore" / "observability.jsonl"
    hub = ObservabilityHub(log_path=log_path)
    _set_hub(hub)
    return hub


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# ErrorEnvelope
# ---------------------------------------------------------------------------


class TestErrorEnvelope:
    def test_frozen(self):
        env = ErrorEnvelope(task_id="t1", error_type="ValueError", stack="tb")
        with pytest.raises((AttributeError, TypeError)):
            env.task_id = "changed"  # type: ignore[misc]

    def test_defaults(self):
        env = ErrorEnvelope(task_id="t1", error_type="IOError", stack="tb")
        assert env.attempt_count == 1
        assert env.model == ""
        assert env.latency_s == 0.0
        assert env.extra == {}
        assert isinstance(env.timestamp, float)
        assert isinstance(env.worker_id, str) and env.worker_id  # non-empty

    def test_custom_values(self):
        env = ErrorEnvelope(
            task_id="abc",
            error_type="TimeoutError",
            stack="line1\nline2",
            attempt_count=3,
            model="gpt-4.1",
            latency_s=1.5,
            extra={"retry": True},
        )
        assert env.attempt_count == 3
        assert env.model == "gpt-4.1"
        assert env.latency_s == 1.5
        assert env.extra == {"retry": True}

    def test_to_dict_round_trip(self):
        env = ErrorEnvelope(
            task_id="x",
            error_type="RuntimeError",
            stack="traceback",
            model="deepseek-chat",
            latency_s=0.25,
        )
        d = env.to_dict()
        assert d["event"] == "error"
        assert d["task_id"] == "x"
        restored = ErrorEnvelope.from_dict(d)
        assert restored.task_id == env.task_id
        assert restored.error_type == env.error_type
        assert restored.model == env.model
        assert restored.latency_s == env.latency_s

    def test_extra_defaults_to_empty_dict_not_shared(self):
        """Each instance should have its own extra dict (no shared default)."""
        e1 = ErrorEnvelope(task_id="a", error_type="E", stack="s")
        e2 = ErrorEnvelope(task_id="b", error_type="E", stack="s")
        assert e1.extra is not e2.extra


# ---------------------------------------------------------------------------
# ToolCallVerifier
# ---------------------------------------------------------------------------


class TestToolCallVerifier:
    def test_verify_http_success_range(self):
        for code in (200, 201, 204, 299):
            assert ToolCallVerifier.verify_http(code) is True

    def test_verify_http_failure_range(self):
        for code in (100, 301, 400, 404, 500, 503):
            assert ToolCallVerifier.verify_http(code) is False

    def test_verify_non_empty_truthy(self):
        assert ToolCallVerifier.verify_non_empty("hello") is True
        assert ToolCallVerifier.verify_non_empty([1, 2]) is True
        assert ToolCallVerifier.verify_non_empty({"k": "v"}) is True
        assert ToolCallVerifier.verify_non_empty(0) is True  # falsy but not empty-type
        assert ToolCallVerifier.verify_non_empty(False) is True

    def test_verify_non_empty_falsy(self):
        assert ToolCallVerifier.verify_non_empty(None) is False
        assert ToolCallVerifier.verify_non_empty("") is False
        assert ToolCallVerifier.verify_non_empty([]) is False
        assert ToolCallVerifier.verify_non_empty({}) is False

    def test_verify_schema_all_keys_present(self):
        assert ToolCallVerifier.verify_schema({"a": 1, "b": 2}, ["a", "b"]) is True
        assert ToolCallVerifier.verify_schema({"a": 1, "b": 2, "c": 3}, ["a"]) is True

    def test_verify_schema_missing_key(self):
        assert ToolCallVerifier.verify_schema({"a": 1}, ["a", "b"]) is False

    def test_verify_schema_non_dict(self):
        assert ToolCallVerifier.verify_schema("not a dict", ["key"]) is False  # type: ignore[arg-type]

    def test_verify_schema_empty_required(self):
        assert ToolCallVerifier.verify_schema({}, []) is True

    def test_verify_all_all_pass(self):
        passed, failures = ToolCallVerifier.verify_all(
            200, {"data": [1, 2]}, required_keys=["data"]
        )
        assert passed is True
        assert failures == []

    def test_verify_all_bad_status(self):
        passed, failures = ToolCallVerifier.verify_all(500, {"data": []})
        assert passed is False
        assert any("http_status_not_ok" in f for f in failures)

    def test_verify_all_empty_response(self):
        passed, failures = ToolCallVerifier.verify_all(200, "")
        assert passed is False
        assert any("response_is_empty" in f for f in failures)

    def test_verify_all_missing_keys(self):
        passed, failures = ToolCallVerifier.verify_all(
            200, {"a": 1}, required_keys=["a", "b"]
        )
        assert passed is False
        assert any("missing_keys" in f for f in failures)

    def test_verify_all_no_required_keys(self):
        passed, failures = ToolCallVerifier.verify_all(200, {"x": 1})
        assert passed is True
        assert failures == []

    def test_verify_all_multiple_failures(self):
        passed, failures = ToolCallVerifier.verify_all(
            404, None, required_keys=["key"]
        )
        assert passed is False
        assert len(failures) >= 2  # http + empty


# ---------------------------------------------------------------------------
# TokenBudget
# ---------------------------------------------------------------------------


class TestTokenBudget:
    def test_initial_remaining(self):
        tb = TokenBudget(1000)
        assert tb.remaining() == 1000

    def test_consume_reduces_remaining(self):
        tb = TokenBudget(1000)
        tb.consume("step1", 300)
        assert tb.remaining() == 700

    def test_consume_accumulates_same_step(self):
        tb = TokenBudget(1000)
        tb.consume("step1", 200)
        tb.consume("step1", 100)
        assert tb.remaining() == 700

    def test_pct_used(self):
        tb = TokenBudget(1000)
        tb.consume("a", 500)
        assert tb.pct_used() == pytest.approx(0.5)

    def test_pct_used_capped_at_1(self):
        tb = TokenBudget(100)
        tb.consume("a", 200)
        assert tb.pct_used() == 1.0

    def test_remaining_floored_at_0(self):
        tb = TokenBudget(100)
        tb.consume("a", 200)
        assert tb.remaining() == 0

    def test_warn_if_low_below_threshold(self):
        tb = TokenBudget(1000)
        tb.consume("a", 500)  # 50%
        assert tb.warn_if_low(threshold=0.80) is False

    def test_warn_if_low_at_threshold(self):
        tb = TokenBudget(1000)
        tb.consume("a", 800)  # exactly 80%
        assert tb.warn_if_low(threshold=0.80) is True

    def test_warn_if_low_above_threshold(self):
        tb = TokenBudget(1000)
        tb.consume("a", 950)  # 95%
        assert tb.warn_if_low(threshold=0.80) is True

    def test_warn_if_low_logs_warning(self, caplog):
        import logging
        tb = TokenBudget(100)
        tb.consume("x", 85)
        with caplog.at_level(logging.WARNING, logger="lore.observability"):
            result = tb.warn_if_low(threshold=0.80)
        assert result is True
        assert any("%" in rec.message for rec in caplog.records)

    def test_summary_structure(self):
        tb = TokenBudget(500)
        tb.consume("parse", 100)
        tb.consume("generate", 150)
        s = tb.summary()
        assert s["parse"] == 100
        assert s["generate"] == 150
        assert s["total"] == 500
        assert s["consumed"] == 250
        assert s["remaining"] == 250
        assert s["pct_used"] == pytest.approx(0.5)

    def test_summary_empty(self):
        tb = TokenBudget(200)
        s = tb.summary()
        assert s["consumed"] == 0
        assert s["remaining"] == 200
        assert s["pct_used"] == 0.0


# ---------------------------------------------------------------------------
# ObservabilityHub
# ---------------------------------------------------------------------------


class TestObservabilityHub:
    def test_record_error_persists_to_jsonl(self, tmp_path):
        hub = make_hub(tmp_path)
        env = ErrorEnvelope(task_id="t1", error_type="IOError", stack="tb")
        hub.record_error(env)

        log_path = tmp_path / ".lore" / "observability.jsonl"
        assert log_path.exists()
        records = read_jsonl(log_path)
        assert len(records) == 1
        assert records[0]["event"] == "error"
        assert records[0]["task_id"] == "t1"

    def test_record_success_persists_to_jsonl(self, tmp_path):
        hub = make_hub(tmp_path)
        hub.record_success(task_id="t2", model="gpt-4.1", latency_s=0.3, tokens_used=50)

        log_path = tmp_path / ".lore" / "observability.jsonl"
        records = read_jsonl(log_path)
        assert len(records) == 1
        assert records[0]["event"] == "success"
        assert records[0]["task_id"] == "t2"
        assert records[0]["model"] == "gpt-4.1"
        assert records[0]["tokens_used"] == 50

    def test_multiple_events_appended(self, tmp_path):
        hub = make_hub(tmp_path)
        hub.record_error(ErrorEnvelope(task_id="e1", error_type="E", stack="s"))
        hub.record_success(task_id="s1", model="m", latency_s=0.1, tokens_used=10)
        hub.record_error(ErrorEnvelope(task_id="e2", error_type="E", stack="s"))

        log_path = tmp_path / ".lore" / "observability.jsonl"
        records = read_jsonl(log_path)
        assert len(records) == 3

    def test_recent_errors_returns_error_envelopes(self, tmp_path):
        hub = make_hub(tmp_path)
        hub.record_error(ErrorEnvelope(task_id="e1", error_type="A", stack="s1"))
        hub.record_success(task_id="s1", model="m", latency_s=0.1, tokens_used=5)
        hub.record_error(ErrorEnvelope(task_id="e2", error_type="B", stack="s2"))

        errors = hub.recent_errors(n=10)
        assert len(errors) == 2
        assert all(isinstance(e, ErrorEnvelope) for e in errors)
        assert errors[0].task_id == "e1"
        assert errors[1].task_id == "e2"

    def test_recent_errors_respects_n(self, tmp_path):
        hub = make_hub(tmp_path)
        for i in range(10):
            hub.record_error(ErrorEnvelope(task_id=f"e{i}", error_type="E", stack="s"))

        errors = hub.recent_errors(n=3)
        assert len(errors) == 3
        # Should be the last 3
        assert errors[-1].task_id == "e9"

    def test_recent_errors_empty_when_none(self, tmp_path):
        hub = make_hub(tmp_path)
        hub.record_success(task_id="s1", model="m", latency_s=0.1, tokens_used=5)
        assert hub.recent_errors() == []

    def test_error_rate_all_errors(self, tmp_path):
        hub = make_hub(tmp_path)
        for i in range(5):
            hub.record_error(ErrorEnvelope(task_id=f"e{i}", error_type="E", stack="s"))
        assert hub.error_rate(window_s=300) == pytest.approx(1.0)

    def test_error_rate_no_errors(self, tmp_path):
        hub = make_hub(tmp_path)
        for i in range(5):
            hub.record_success(task_id=f"s{i}", model="m", latency_s=0.1, tokens_used=5)
        assert hub.error_rate(window_s=300) == pytest.approx(0.0)

    def test_error_rate_mixed(self, tmp_path):
        hub = make_hub(tmp_path)
        for i in range(3):
            hub.record_error(ErrorEnvelope(task_id=f"e{i}", error_type="E", stack="s"))
        for i in range(7):
            hub.record_success(task_id=f"s{i}", model="m", latency_s=0.1, tokens_used=5)
        rate = hub.error_rate(window_s=300)
        assert rate == pytest.approx(0.3)

    def test_error_rate_empty_window(self, tmp_path):
        hub = make_hub(tmp_path)
        assert hub.error_rate(window_s=300) == 0.0

    def test_error_rate_respects_window(self, tmp_path):
        hub = make_hub(tmp_path)
        # Record an error, then fake its timestamp to be old
        env = ErrorEnvelope(task_id="old", error_type="E", stack="s")
        hub.record_error(env)
        # Manually age the event beyond the window
        with hub._lock:
            hub._events[0]["timestamp"] = time.time() - 400

        # Within a 300s window, the old event shouldn't count
        assert hub.error_rate(window_s=300) == 0.0

    def test_memory_ring_buffer_capped(self, tmp_path):
        hub = make_hub(tmp_path)
        for i in range(120):
            hub.record_success(task_id=f"s{i}", model="m", latency_s=0.0, tokens_used=1)
        with hub._lock:
            assert len(hub._events) <= 100

    def test_jsonl_each_line_valid_json(self, tmp_path):
        hub = make_hub(tmp_path)
        hub.record_error(ErrorEnvelope(task_id="t1", error_type="E", stack="s"))
        hub.record_success(task_id="t2", model="m", latency_s=0.1, tokens_used=10)

        log_path = tmp_path / ".lore" / "observability.jsonl"
        for line in log_path.read_text().splitlines():
            assert line.strip()
            obj = json.loads(line)  # raises if invalid
            assert "event" in obj
            assert "timestamp" in obj

    def test_log_dir_created_automatically(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / ".lore" / "observability.jsonl"
        hub = ObservabilityHub(log_path=nested)
        hub.record_success(task_id="t1", model="m", latency_s=0.0, tokens_used=0)
        assert nested.exists()


# ---------------------------------------------------------------------------
# Module-level wrappers
# ---------------------------------------------------------------------------


class TestModuleLevelWrappers:
    def test_record_error_wrapper(self, tmp_path):
        make_hub(tmp_path)
        env = ErrorEnvelope(task_id="w1", error_type="E", stack="s")
        record_error(env)
        errors = recent_errors(n=1)
        assert len(errors) == 1
        assert errors[0].task_id == "w1"

    def test_record_success_wrapper(self, tmp_path):
        hub = make_hub(tmp_path)
        record_success(task_id="w2", model="m", latency_s=0.5, tokens_used=100)
        log_path = tmp_path / ".lore" / "observability.jsonl"
        records = read_jsonl(log_path)
        assert records[0]["event"] == "success"

    def test_recent_errors_wrapper(self, tmp_path):
        make_hub(tmp_path)
        record_error(ErrorEnvelope(task_id="w3", error_type="X", stack="s"))
        result = recent_errors(n=5)
        assert any(e.task_id == "w3" for e in result)

    def test_error_rate_wrapper(self, tmp_path):
        make_hub(tmp_path)
        record_error(ErrorEnvelope(task_id="w4", error_type="E", stack="s"))
        rate = error_rate(window_s=300)
        assert 0.0 < rate <= 1.0
