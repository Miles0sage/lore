"""Tests for dispatch.py — circuit breaker and routing logic (no real API calls)."""

from __future__ import annotations

import pytest

from lore import dispatch, routing
from lore.circuit_breaker import (
    CircuitBreakerEngine,
    CircuitConfig,
    InMemoryCircuitStore,
    _set_engine,
    is_circuit_open,
    record_failure,
    record_success,
)

_FAILURE_THRESHOLD = CircuitConfig().failure_threshold


def _make_clean_engine() -> CircuitBreakerEngine:
    """Return a fresh in-memory engine for test isolation."""
    return CircuitBreakerEngine(store=InMemoryCircuitStore(), config=CircuitConfig())


@pytest.fixture(autouse=True)
def clean_state():
    engine = _make_clean_engine()
    _set_engine(engine)
    # Also reset the module-level cache so it references the new engine
    from lore.circuit_breaker import CachedFallback, _get_engine
    dispatch._response_cache = CachedFallback(_get_engine())
    yield
    engine = _make_clean_engine()
    _set_engine(engine)


class TestCircuitBreaker:
    def test_circuit_closed_initially(self):
        for model in dispatch._TIER_ORDER:
            assert not is_circuit_open(model)

    def test_circuit_opens_after_threshold(self):
        model = "gpt-4.1"
        for _ in range(_FAILURE_THRESHOLD):
            record_failure(model)
        assert is_circuit_open(model)

    def test_circuit_resets_on_success(self):
        model = "gpt-4.1"
        for _ in range(_FAILURE_THRESHOLD):
            record_failure(model)
        record_success(model)
        assert not is_circuit_open(model)

    def test_reset_circuit_tool(self):
        model = "deepseek-chat"
        for _ in range(_FAILURE_THRESHOLD):
            record_failure(model)
        result = dispatch.reset_circuit(model)
        assert result["reset"] == model
        assert not is_circuit_open(model)

    def test_reset_unknown_model_returns_error(self):
        result = dispatch.reset_circuit("gpt-99")
        assert "error" in result

    def test_get_circuit_status_all_closed(self):
        status = dispatch.get_circuit_status()
        for model in dispatch._TIER_ORDER:
            assert model in status
            assert status[model]["open"] is False
            assert status[model]["failures"] == 0

    def test_get_circuit_status_one_open(self):
        for _ in range(_FAILURE_THRESHOLD):
            record_failure("deepseek-chat")
        status = dispatch.get_circuit_status()
        assert status["deepseek-chat"]["open"] is True
        assert status["gpt-4.1"]["open"] is False


class TestModelResolution:
    def test_resolves_preferred_when_closed(self):
        model, reason = dispatch._resolve_model("gpt-4.1")
        assert model == "gpt-4.1"
        assert reason is None

    def test_escalates_when_circuit_open(self):
        for _ in range(_FAILURE_THRESHOLD):
            record_failure("deepseek-chat")
        model, reason = dispatch._resolve_model("deepseek-chat")
        assert model == "gpt-4.1"
        assert reason and "circuit_open" in reason

    def test_escalates_twice_when_two_circuits_open(self):
        for m in ("deepseek-chat", "gpt-4.1"):
            for _ in range(_FAILURE_THRESHOLD):
                record_failure(m)
        model, reason = dispatch._resolve_model("deepseek-chat")
        assert model == "gpt-5.4"
        assert reason and "circuit_open" in reason

    def test_all_open_returns_preferred_with_reason(self):
        for m in dispatch._TIER_ORDER:
            for _ in range(_FAILURE_THRESHOLD):
                record_failure(m)
        model, reason = dispatch._resolve_model("deepseek-chat")
        assert reason == "all_circuits_open"


class TestCostEstimate:
    def test_deepseek_cheapest(self):
        ds = dispatch._estimate_cost("deepseek-chat", 1000, 1000)
        g41 = dispatch._estimate_cost("gpt-4.1", 1000, 1000)
        g54 = dispatch._estimate_cost("gpt-5.4", 1000, 1000)
        assert ds < g41 < g54

    def test_zero_tokens_zero_cost(self):
        assert dispatch._estimate_cost("gpt-4.1", 0, 0) == 0.0


class TestDispatchNoAPI:
    """Dispatch with all circuits open — returns error without hitting any API."""

    def test_all_circuits_open_returns_error(self, monkeypatch):
        for m in dispatch._TIER_ORDER:
            for _ in range(_FAILURE_THRESHOLD):
                record_failure(m)
        result = dispatch.dispatch_task("triage", "test prompt")
        assert result["error"] == "all_circuits_open"
        assert "circuit_status" in result

    def test_missing_api_key_returns_error_dict(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "")
        # Monkeypatch _load_from_factory_env to return empty string
        monkeypatch.setattr(dispatch, "_load_from_factory_env", lambda k: "")
        result = dispatch.dispatch_task("triage", "test prompt", description="unit test")
        assert "error" in result
        assert result["task_type"] == "triage"
