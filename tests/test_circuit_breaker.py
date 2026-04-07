"""Tests for lore/circuit_breaker.py.

Covers:
- CircuitState enum
- CircuitConfig frozen dataclass + per-tool overrides
- InMemoryCircuitStore CRUD
- SqliteCircuitStore CRUD + WAL mode
- CircuitBreakerEngine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED transitions
- CachedFallback: stores / retrieves / expires cached responses
- Module-level wrappers: is_circuit_open, record_failure, record_success, resolve_model
"""

from __future__ import annotations

import time
import sqlite3
from pathlib import Path

import pytest

from lore.circuit_breaker import (
    CachedFallback,
    CircuitBreakerEngine,
    CircuitConfig,
    CircuitState,
    InMemoryCircuitStore,
    SqliteCircuitStore,
    _set_engine,
    _get_engine,
    get_circuit_status,
    is_circuit_open,
    record_failure,
    record_success,
    reset_circuit,
    resolve_model,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_engine(
    store=None,
    failure_threshold=3,
    recovery_wait=30.0,
    telemetry_dir=None,
    tmp_path=None,
) -> CircuitBreakerEngine:
    """Build a fresh engine backed by InMemoryCircuitStore (or given store)."""
    store = store or InMemoryCircuitStore()
    config = CircuitConfig(
        failure_threshold=failure_threshold,
        recovery_wait=recovery_wait,
    )
    td = telemetry_dir or (tmp_path / "telemetry" if tmp_path else Path("/tmp/lore-test-telemetry"))
    td.mkdir(parents=True, exist_ok=True)
    return CircuitBreakerEngine(store=store, config=config, telemetry_dir=td)


@pytest.fixture()
def engine(tmp_path):
    return _make_engine(tmp_path=tmp_path)


@pytest.fixture(autouse=True)
def isolate_singleton(tmp_path):
    """Replace the module singleton with a fresh in-memory engine for every test."""
    fresh = _make_engine(tmp_path=tmp_path)
    _set_engine(fresh)
    yield
    fresh_again = _make_engine(tmp_path=tmp_path)
    _set_engine(fresh_again)


# ---------------------------------------------------------------------------
# CircuitState
# ---------------------------------------------------------------------------


class TestCircuitState:
    def test_values(self):
        assert CircuitState.CLOSED == "closed"
        assert CircuitState.OPEN == "open"
        assert CircuitState.HALF_OPEN == "half_open"

    def test_is_str_enum(self):
        assert isinstance(CircuitState.CLOSED, str)


# ---------------------------------------------------------------------------
# CircuitConfig
# ---------------------------------------------------------------------------


class TestCircuitConfig:
    def test_defaults(self):
        cfg = CircuitConfig()
        assert cfg.failure_threshold == 3
        assert cfg.recovery_wait == 30.0

    def test_frozen(self):
        cfg = CircuitConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.failure_threshold = 99  # type: ignore[misc]

    def test_per_tool_override(self):
        cfg = CircuitConfig(
            failure_threshold=3,
            recovery_wait=30.0,
            per_tool_overrides={"deepseek-chat": {"failure_threshold": 10, "recovery_wait": 60.0}},
        )
        override = cfg.for_tool("deepseek-chat")
        assert override.failure_threshold == 10
        assert override.recovery_wait == 60.0

    def test_no_override_returns_same(self):
        cfg = CircuitConfig(failure_threshold=3)
        same = cfg.for_tool("unknown-model")
        assert same.failure_threshold == 3


# ---------------------------------------------------------------------------
# InMemoryCircuitStore
# ---------------------------------------------------------------------------


class TestInMemoryCircuitStore:
    def test_initial_state_is_closed(self):
        store = InMemoryCircuitStore()
        data = store.get_state("gpt-4.1")
        assert data["state"] == CircuitState.CLOSED
        assert data["failures"] == 0

    def test_increment_failures(self):
        store = InMemoryCircuitStore()
        n = store.increment_failures("gpt-4.1")
        assert n == 1
        n2 = store.increment_failures("gpt-4.1")
        assert n2 == 2

    def test_set_state(self):
        store = InMemoryCircuitStore()
        store.set_state("gpt-4.1", CircuitState.OPEN, 5)
        data = store.get_state("gpt-4.1")
        assert data["state"] == CircuitState.OPEN
        assert data["failures"] == 5

    def test_reset_failures(self):
        store = InMemoryCircuitStore()
        store.increment_failures("gpt-4.1")
        store.increment_failures("gpt-4.1")
        store.reset_failures("gpt-4.1")
        data = store.get_state("gpt-4.1")
        assert data["failures"] == 0

    def test_isolation_between_tools(self):
        store = InMemoryCircuitStore()
        store.increment_failures("model-a")
        store.increment_failures("model-a")
        assert store.get_state("model-b")["failures"] == 0

    def test_clear(self):
        store = InMemoryCircuitStore()
        store.increment_failures("gpt-4.1")
        store.clear()
        assert store.get_state("gpt-4.1")["failures"] == 0


# ---------------------------------------------------------------------------
# SqliteCircuitStore
# ---------------------------------------------------------------------------


class TestSqliteCircuitStore:
    def test_initial_state_is_closed(self, tmp_path):
        store = SqliteCircuitStore(db_path=tmp_path / "cb.db")
        data = store.get_state("deepseek-chat")
        assert data["state"] == CircuitState.CLOSED
        assert data["failures"] == 0

    def test_increment_and_reset(self, tmp_path):
        store = SqliteCircuitStore(db_path=tmp_path / "cb.db")
        n1 = store.increment_failures("deepseek-chat")
        assert n1 == 1
        n2 = store.increment_failures("deepseek-chat")
        assert n2 == 2
        store.reset_failures("deepseek-chat")
        assert store.get_state("deepseek-chat")["failures"] == 0

    def test_set_state_persists(self, tmp_path):
        db_path = tmp_path / "cb.db"
        store = SqliteCircuitStore(db_path=db_path)
        store.set_state("gpt-4.1", CircuitState.OPEN, 7)

        # Reload from same db
        store2 = SqliteCircuitStore(db_path=db_path)
        data = store2.get_state("gpt-4.1")
        assert data["state"] == CircuitState.OPEN
        assert data["failures"] == 7

    def test_wal_mode_enabled(self, tmp_path):
        db_path = tmp_path / "cb.db"
        SqliteCircuitStore(db_path=db_path)
        conn = sqlite3.connect(str(db_path))
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_isolation_between_tools(self, tmp_path):
        store = SqliteCircuitStore(db_path=tmp_path / "cb.db")
        store.increment_failures("gpt-4.1")
        assert store.get_state("deepseek-chat")["failures"] == 0


# ---------------------------------------------------------------------------
# CircuitBreakerEngine — state transitions
# ---------------------------------------------------------------------------


class TestCircuitBreakerEngine:
    def test_starts_closed(self, engine):
        assert not engine.is_open("gpt-4.1")
        status = engine.get_status("gpt-4.1")
        assert status["state"] == "closed"

    def test_closed_to_open_after_threshold(self, engine):
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        assert engine.is_open("gpt-4.1")
        status = engine.get_status("gpt-4.1")
        assert status["state"] == "open"

    def test_failures_below_threshold_stay_closed(self, engine):
        engine.record_failure("gpt-4.1")
        engine.record_failure("gpt-4.1")
        assert not engine.is_open("gpt-4.1")

    def test_success_resets_to_closed(self, engine):
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        assert engine.is_open("gpt-4.1")
        engine.record_success("gpt-4.1")
        assert not engine.is_open("gpt-4.1")
        assert engine.get_status("gpt-4.1")["state"] == "closed"

    def test_open_transitions_to_half_open_after_recovery_wait(self, tmp_path):
        """After recovery_wait elapses, is_open() returns False (HALF_OPEN probe allowed)."""
        store = InMemoryCircuitStore()
        engine = _make_engine(store=store, failure_threshold=1, recovery_wait=0.05, tmp_path=tmp_path)
        engine.record_failure("deepseek-chat")
        assert engine.is_open("deepseek-chat")

        time.sleep(0.1)  # exceed recovery_wait
        # Now should allow probe (HALF_OPEN)
        assert not engine.is_open("deepseek-chat")
        assert engine.get_status("deepseek-chat")["state"] == "half_open"

    def test_half_open_success_closes_circuit(self, tmp_path):
        store = InMemoryCircuitStore()
        engine = _make_engine(store=store, failure_threshold=1, recovery_wait=0.05, tmp_path=tmp_path)
        engine.record_failure("deepseek-chat")
        time.sleep(0.1)
        engine.is_open("deepseek-chat")  # triggers HALF_OPEN transition
        engine.record_success("deepseek-chat")
        assert not engine.is_open("deepseek-chat")
        assert engine.get_status("deepseek-chat")["state"] == "closed"

    def test_half_open_failure_reopens_circuit(self, tmp_path):
        store = InMemoryCircuitStore()
        engine = _make_engine(store=store, failure_threshold=1, recovery_wait=0.05, tmp_path=tmp_path)
        engine.record_failure("deepseek-chat")
        time.sleep(0.1)
        engine.is_open("deepseek-chat")  # triggers HALF_OPEN
        # Probe fails
        engine.record_failure("deepseek-chat")
        assert engine.is_open("deepseek-chat")
        assert engine.get_status("deepseek-chat")["state"] == "open"

    def test_manual_reset(self, engine):
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        assert engine.is_open("gpt-4.1")
        engine.reset("gpt-4.1")
        assert not engine.is_open("gpt-4.1")
        assert engine.get_status("gpt-4.1")["state"] == "closed"

    def test_metrics_jsonl_written_on_transition(self, tmp_path):
        import json

        td = tmp_path / "telemetry"
        td.mkdir(exist_ok=True)
        store = InMemoryCircuitStore()
        engine = CircuitBreakerEngine(
            store=store,
            config=CircuitConfig(failure_threshold=1),
            telemetry_dir=td,
        )
        engine.record_failure("gpt-5.4")
        metrics_path = td / "circuit_metrics.jsonl"
        assert metrics_path.exists()
        lines = metrics_path.read_text().strip().splitlines()
        assert len(lines) >= 1
        record = json.loads(lines[-1])
        assert record["tool"] == "gpt-5.4"
        assert record["to_state"] == "open"

    def test_isolation_between_tools(self, engine):
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        assert engine.is_open("gpt-4.1")
        assert not engine.is_open("deepseek-chat")

    def test_sqlite_engine_full_cycle(self, tmp_path):
        """Full CLOSED->OPEN->HALF_OPEN->CLOSED cycle with SqliteStore."""
        db_path = tmp_path / "cb.db"
        store = SqliteCircuitStore(db_path=db_path)
        engine = CircuitBreakerEngine(
            store=store,
            config=CircuitConfig(failure_threshold=2, recovery_wait=0.05),
            telemetry_dir=tmp_path / "telemetry",
        )
        (tmp_path / "telemetry").mkdir(exist_ok=True)

        # CLOSED -> OPEN
        engine.record_failure("deepseek-chat")
        engine.record_failure("deepseek-chat")
        assert engine.is_open("deepseek-chat")

        # OPEN -> HALF_OPEN after recovery_wait
        time.sleep(0.1)
        assert not engine.is_open("deepseek-chat")
        assert engine.get_status("deepseek-chat")["state"] == "half_open"

        # HALF_OPEN -> CLOSED on success
        engine.record_success("deepseek-chat")
        assert engine.get_status("deepseek-chat")["state"] == "closed"


# ---------------------------------------------------------------------------
# CachedFallback
# ---------------------------------------------------------------------------


class TestCachedFallback:
    def test_returns_none_when_circuit_closed(self, engine):
        fallback = CachedFallback(engine)
        fallback.store("gpt-4.1", {"text": "cached"})
        # Circuit is CLOSED — should not serve cache
        assert fallback.get("gpt-4.1") is None

    def test_returns_cached_when_circuit_open(self, engine):
        fallback = CachedFallback(engine)
        fallback.store("gpt-4.1", {"text": "cached"})
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        assert engine.is_open("gpt-4.1")
        result = fallback.get("gpt-4.1")
        assert result == {"text": "cached"}

    def test_returns_none_when_cache_stale(self, engine):
        fallback = CachedFallback(engine, max_age=0.05)
        fallback.store("gpt-4.1", {"text": "cached"})
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        time.sleep(0.1)
        assert fallback.get("gpt-4.1") is None

    def test_returns_none_when_no_cache(self, engine):
        fallback = CachedFallback(engine)
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        assert fallback.get("gpt-4.1") is None

    def test_clear_specific_tool(self, engine):
        fallback = CachedFallback(engine)
        fallback.store("gpt-4.1", "response-a")
        fallback.store("deepseek-chat", "response-b")
        fallback.clear("gpt-4.1")
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        assert fallback.get("gpt-4.1") is None

    def test_clear_all(self, engine):
        fallback = CachedFallback(engine)
        fallback.store("gpt-4.1", "response-a")
        for _ in range(3):
            engine.record_failure("gpt-4.1")
        fallback.clear()
        assert fallback.get("gpt-4.1") is None


# ---------------------------------------------------------------------------
# Module-level wrappers
# ---------------------------------------------------------------------------


class TestModuleWrappers:
    def test_is_circuit_open_initially_false(self):
        assert not is_circuit_open("gpt-4.1")

    def test_record_failure_opens_circuit(self):
        for _ in range(3):
            record_failure("gpt-4.1")
        assert is_circuit_open("gpt-4.1")

    def test_record_success_closes_circuit(self):
        for _ in range(3):
            record_failure("deepseek-chat")
        assert is_circuit_open("deepseek-chat")
        record_success("deepseek-chat")
        assert not is_circuit_open("deepseek-chat")

    def test_resolve_model_returns_preferred_when_closed(self):
        model, reason = resolve_model("deepseek-chat")
        assert model == "deepseek-chat"
        assert reason is None

    def test_resolve_model_escalates_when_open(self):
        for _ in range(3):
            record_failure("deepseek-chat")
        model, reason = resolve_model("deepseek-chat")
        assert model == "gpt-4.1"
        assert reason == "circuit_open:deepseek-chat"

    def test_resolve_model_all_circuits_open(self):
        for m in ["deepseek-chat", "gpt-4.1", "gpt-5.4"]:
            for _ in range(3):
                record_failure(m)
        model, reason = resolve_model("deepseek-chat")
        # Returns preferred with all_circuits_open reason
        assert model == "deepseek-chat"
        assert reason == "all_circuits_open"

    def test_get_circuit_status_all_models(self):
        status = get_circuit_status()
        for m in ["deepseek-chat", "gpt-4.1", "gpt-5.4"]:
            assert m in status
            assert status[m]["state"] == "closed"
            assert status[m]["open"] is False

    def test_get_circuit_status_single_tool(self):
        status = get_circuit_status("gpt-4.1")
        assert status["tool"] == "gpt-4.1"
        assert "state" in status

    def test_reset_circuit_known_model(self):
        for _ in range(3):
            record_failure("gpt-5.4")
        assert is_circuit_open("gpt-5.4")
        result = reset_circuit("gpt-5.4")
        assert result == {"reset": "gpt-5.4"}
        assert not is_circuit_open("gpt-5.4")

    def test_reset_circuit_unknown_model(self):
        result = reset_circuit("gpt-99")
        assert "error" in result
