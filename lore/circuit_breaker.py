"""
Circuit breaker with persistent SQLite state for Lore dispatch.

States:
  CLOSED    - Normal operation, requests pass through
  OPEN      - Model disabled, requests fail fast; CachedFallback may serve
  HALF_OPEN - One probe request allowed; success resets, failure re-opens

Usage (module-level wrappers)::

    from lore.circuit_breaker import is_circuit_open, record_failure, record_success, resolve_model

    if is_circuit_open("deepseek-chat"):
        model, reason = resolve_model("deepseek-chat")
    else:
        try:
            call_model("deepseek-chat", ...)
            record_success("deepseek-chat")
        except Exception:
            record_failure("deepseek-chat")
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from lore.config import get_telemetry_dir

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State enum
# ---------------------------------------------------------------------------


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# Config (frozen dataclass — immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CircuitConfig:
    """Configuration for circuit breaker behaviour.

    Args:
        failure_threshold: Number of consecutive failures before opening.
        recovery_wait:     Seconds to wait in OPEN before probing (HALF_OPEN).
        per_tool_overrides: Optional per-model config overrides
                            ``{"deepseek-chat": {"failure_threshold": 5}}``.
    """

    failure_threshold: int = 3
    recovery_wait: float = 30.0
    per_tool_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    def for_tool(self, tool: str) -> "CircuitConfig":
        """Return a config with per-tool overrides applied."""
        overrides = self.per_tool_overrides.get(tool, {})
        if not overrides:
            return self
        return CircuitConfig(
            failure_threshold=overrides.get("failure_threshold", self.failure_threshold),
            recovery_wait=overrides.get("recovery_wait", self.recovery_wait),
            per_tool_overrides=self.per_tool_overrides,
        )


# ---------------------------------------------------------------------------
# Store protocol (structural)
# ---------------------------------------------------------------------------


class CircuitStore:
    """Abstract base — concrete stores implement these methods."""

    def get_state(self, tool: str) -> dict[str, Any]:
        """Return dict with keys: state, failures, last_failure_ts, last_state_change_ts."""
        raise NotImplementedError

    def set_state(self, tool: str, state: CircuitState, failures: int) -> None:
        raise NotImplementedError

    def increment_failures(self, tool: str) -> int:
        """Increment failure count and last_failure_ts; return new count."""
        raise NotImplementedError

    def reset_failures(self, tool: str) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# InMemoryCircuitStore — test use only
# ---------------------------------------------------------------------------


class InMemoryCircuitStore(CircuitStore):
    """Non-persistent in-process store. Safe for single-process tests."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _default(self) -> dict[str, Any]:
        return {
            "state": CircuitState.CLOSED,
            "failures": 0,
            "last_failure_ts": 0.0,
            "last_state_change_ts": time.time(),
        }

    def get_state(self, tool: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._data.get(tool, self._default()))

    def set_state(self, tool: str, state: CircuitState, failures: int) -> None:
        with self._lock:
            existing = self._data.get(tool, self._default())
            self._data[tool] = {
                **existing,
                "state": state,
                "failures": failures,
                "last_state_change_ts": time.time(),
            }

    def increment_failures(self, tool: str) -> int:
        with self._lock:
            existing = self._data.get(tool, self._default())
            new_failures = existing["failures"] + 1
            self._data[tool] = {
                **existing,
                "failures": new_failures,
                "last_failure_ts": time.time(),
            }
            return new_failures

    def reset_failures(self, tool: str) -> None:
        with self._lock:
            existing = self._data.get(tool, self._default())
            self._data[tool] = {
                **existing,
                "failures": 0,
                "last_failure_ts": 0.0,
            }

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


# ---------------------------------------------------------------------------
# SqliteCircuitStore — production default
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS circuit_state (
    tool                  TEXT PRIMARY KEY,
    state                 TEXT NOT NULL DEFAULT 'closed',
    failures              INTEGER NOT NULL DEFAULT 0,
    last_failure_ts       REAL NOT NULL DEFAULT 0,
    last_state_change_ts  REAL NOT NULL DEFAULT 0
);
"""


class SqliteCircuitStore(CircuitStore):
    """Persistent SQLite store with WAL mode for multi-process safety.

    Args:
        db_path: Path to the SQLite database file.
                 Defaults to ``<telemetry_dir>/circuit_breaker.db``.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = get_telemetry_dir() / "circuit_breaker.db"
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local connection (each thread owns its connection)."""
        if not getattr(self._local, "conn", None):
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript(_SCHEMA)
        conn.commit()

    def _ensure_row(self, tool: str) -> None:
        conn = self._conn()
        conn.execute(
            "INSERT OR IGNORE INTO circuit_state (tool, last_state_change_ts)"
            " VALUES (?, ?)",
            (tool, time.time()),
        )
        conn.commit()

    def get_state(self, tool: str) -> dict[str, Any]:
        self._ensure_row(tool)
        conn = self._conn()
        row = conn.execute(
            "SELECT state, failures, last_failure_ts, last_state_change_ts"
            " FROM circuit_state WHERE tool = ?",
            (tool,),
        ).fetchone()
        return {
            "state": CircuitState(row["state"]),
            "failures": row["failures"],
            "last_failure_ts": row["last_failure_ts"],
            "last_state_change_ts": row["last_state_change_ts"],
        }

    def set_state(self, tool: str, state: CircuitState, failures: int) -> None:
        self._ensure_row(tool)
        conn = self._conn()
        conn.execute(
            "UPDATE circuit_state"
            " SET state = ?, failures = ?, last_state_change_ts = ?"
            " WHERE tool = ?",
            (state.value, failures, time.time(), tool),
        )
        conn.commit()

    def increment_failures(self, tool: str) -> int:
        self._ensure_row(tool)
        conn = self._conn()
        conn.execute(
            "UPDATE circuit_state"
            " SET failures = failures + 1, last_failure_ts = ?"
            " WHERE tool = ?",
            (time.time(), tool),
        )
        conn.commit()
        row = conn.execute(
            "SELECT failures FROM circuit_state WHERE tool = ?", (tool,)
        ).fetchone()
        return row["failures"]

    def reset_failures(self, tool: str) -> None:
        self._ensure_row(tool)
        conn = self._conn()
        conn.execute(
            "UPDATE circuit_state SET failures = 0, last_failure_ts = 0 WHERE tool = ?",
            (tool,),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# RedisCircuitStore — optional, lazy import
# ---------------------------------------------------------------------------


class RedisCircuitStore(CircuitStore):
    """Redis-backed store for multi-worker deployments.

    Redis must be installed (``pip install redis``) and reachable.
    Gracefully raises ``ImportError`` at construction time if redis is absent.

    Args:
        redis_url: Redis connection URL. Defaults to ``redis://localhost:6379/0``.
        prefix:    Key prefix. Defaults to ``lore:cb:``.
        ttl:       Key TTL in seconds (0 = no expiry). Defaults to 3600.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        prefix: str = "lore:cb:",
        ttl: int = 3600,
    ) -> None:
        try:
            import redis  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "redis package is required for RedisCircuitStore. "
                "Install with: pip install redis"
            ) from exc

        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._prefix = prefix
        self._ttl = ttl

    def _key(self, tool: str) -> str:
        return f"{self._prefix}{tool}"

    def get_state(self, tool: str) -> dict[str, Any]:
        import redis  # noqa: F401 — already validated in __init__

        key = self._key(tool)
        data = self._redis.hgetall(key)
        if not data:
            return {
                "state": CircuitState.CLOSED,
                "failures": 0,
                "last_failure_ts": 0.0,
                "last_state_change_ts": time.time(),
            }
        return {
            "state": CircuitState(data.get("state", "closed")),
            "failures": int(data.get("failures", 0)),
            "last_failure_ts": float(data.get("last_failure_ts", 0.0)),
            "last_state_change_ts": float(data.get("last_state_change_ts", 0.0)),
        }

    def set_state(self, tool: str, state: CircuitState, failures: int) -> None:
        key = self._key(tool)
        now = time.time()
        self._redis.hset(
            key,
            mapping={
                "state": state.value,
                "failures": failures,
                "last_state_change_ts": now,
            },
        )
        if self._ttl:
            self._redis.expire(key, self._ttl)

    def increment_failures(self, tool: str) -> int:
        key = self._key(tool)
        pipe = self._redis.pipeline()
        pipe.hincrby(key, "failures", 1)
        pipe.hset(key, "last_failure_ts", time.time())
        if self._ttl:
            pipe.expire(key, self._ttl)
        results = pipe.execute()
        return int(results[0])

    def reset_failures(self, tool: str) -> None:
        key = self._key(tool)
        self._redis.hset(key, mapping={"failures": 0, "last_failure_ts": 0.0})


# ---------------------------------------------------------------------------
# Metrics helpers
# ---------------------------------------------------------------------------


def _append_metric(telemetry_dir: Path, record: dict[str, Any]) -> None:
    """Append a JSONL record to telemetry_dir/circuit_metrics.jsonl."""
    try:
        path = telemetry_dir / "circuit_metrics.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        logger.warning("circuit_breaker: could not write metrics: %s", exc)


# ---------------------------------------------------------------------------
# CircuitBreakerEngine — singleton
# ---------------------------------------------------------------------------


class CircuitBreakerEngine:
    """Manages circuit breaker state transitions for all tools.

    This is the central decision engine. Use the module-level wrappers
    (``is_circuit_open``, ``record_failure``, ``record_success``) rather
    than calling this class directly in production code.

    Args:
        store:         Backing store (SqliteCircuitStore by default).
        config:        Global config (can be overridden per-tool).
        telemetry_dir: Directory for metric JSONL files.
    """

    def __init__(
        self,
        store: CircuitStore | None = None,
        config: CircuitConfig | None = None,
        telemetry_dir: Path | None = None,
    ) -> None:
        self._store = store or SqliteCircuitStore()
        self._config = config or CircuitConfig()
        self._telemetry_dir = telemetry_dir or get_telemetry_dir()
        self._lock = threading.Lock()

    # -- Public API ----------------------------------------------------------

    def is_open(self, tool: str) -> bool:
        """Return True if the circuit is OPEN (requests should be blocked)."""
        data = self._store.get_state(tool)
        state: CircuitState = data["state"]
        cfg = self._config.for_tool(tool)

        if state == CircuitState.CLOSED:
            return False

        if state == CircuitState.OPEN:
            elapsed = time.time() - data["last_failure_ts"]
            if elapsed >= cfg.recovery_wait:
                # Transition to HALF_OPEN
                self._transition(tool, CircuitState.HALF_OPEN, data["failures"])
                return False  # Allow one probe request
            return True

        # HALF_OPEN — allow one probe
        return False

    def record_failure(self, tool: str) -> None:
        """Record a failure for *tool*; may open the circuit."""
        with self._lock:
            cfg = self._config.for_tool(tool)
            new_failures = self._store.increment_failures(tool)
            data = self._store.get_state(tool)
            current_state: CircuitState = data["state"]

            if current_state == CircuitState.HALF_OPEN:
                # Probe failed — re-open immediately
                self._transition(tool, CircuitState.OPEN, new_failures)
            elif new_failures >= cfg.failure_threshold:
                if current_state != CircuitState.OPEN:
                    self._transition(tool, CircuitState.OPEN, new_failures)

    def record_success(self, tool: str) -> None:
        """Record a success for *tool*; closes the circuit."""
        with self._lock:
            data = self._store.get_state(tool)
            current_state: CircuitState = data["state"]
            self._store.reset_failures(tool)
            if current_state != CircuitState.CLOSED:
                self._transition(tool, CircuitState.CLOSED, 0)

    def get_status(self, tool: str) -> dict[str, Any]:
        """Return full status dict for *tool*."""
        data = self._store.get_state(tool)
        return {
            "tool": tool,
            "state": data["state"].value,
            "failures": data["failures"],
            "open": self.is_open(tool),
            "last_failure_ts": data["last_failure_ts"],
            "last_state_change_ts": data["last_state_change_ts"],
        }

    def reset(self, tool: str) -> None:
        """Manually reset *tool* to CLOSED state."""
        with self._lock:
            self._transition(tool, CircuitState.CLOSED, 0)
            self._store.reset_failures(tool)

    # -- Internal ------------------------------------------------------------

    def _transition(self, tool: str, new_state: CircuitState, failures: int) -> None:
        data = self._store.get_state(tool)
        old_state: CircuitState = data["state"]
        self._store.set_state(tool, new_state, failures)
        logger.info(
            "circuit_breaker: %s %s -> %s (failures=%d)",
            tool,
            old_state.value,
            new_state.value,
            failures,
        )
        metric = {
            "ts": time.time(),
            "tool": tool,
            "from_state": old_state.value,
            "to_state": new_state.value,
            "failures": failures,
        }
        _append_metric(self._telemetry_dir, metric)


# ---------------------------------------------------------------------------
# CachedFallback — returns cached responses when circuit is OPEN
# ---------------------------------------------------------------------------


class CachedFallback:
    """Stores the last successful response per tool and returns it when the
    circuit is open.

    Args:
        engine:   The CircuitBreakerEngine to check state against.
        max_age:  Maximum age of cached response in seconds (default: 300).
    """

    def __init__(self, engine: CircuitBreakerEngine, max_age: float = 300.0) -> None:
        self._engine = engine
        self._max_age = max_age
        self._cache: dict[str, tuple[Any, float]] = {}  # tool -> (response, ts)
        self._lock = threading.Lock()

    def store(self, tool: str, response: Any) -> None:
        """Store the latest successful response for *tool*."""
        with self._lock:
            self._cache[tool] = (response, time.time())

    def get(self, tool: str) -> Any | None:
        """Return cached response if circuit is OPEN and cache is fresh.

        Returns ``None`` when the circuit is CLOSED or cache is stale/absent.
        """
        if not self._engine.is_open(tool):
            return None
        with self._lock:
            entry = self._cache.get(tool)
        if entry is None:
            return None
        response, ts = entry
        if time.time() - ts > self._max_age:
            return None
        return response

    def clear(self, tool: str | None = None) -> None:
        """Clear cache for *tool* or all tools if *tool* is None."""
        with self._lock:
            if tool is None:
                self._cache.clear()
            else:
                self._cache.pop(tool, None)


# ---------------------------------------------------------------------------
# Singleton engine
# ---------------------------------------------------------------------------

_engine_lock = threading.Lock()
_engine: CircuitBreakerEngine | None = None


def _get_engine() -> CircuitBreakerEngine:
    """Return the process-level singleton engine (lazy init)."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = CircuitBreakerEngine()
    return _engine


def _set_engine(engine: CircuitBreakerEngine) -> None:
    """Replace the singleton engine (for tests / dependency injection)."""
    global _engine
    with _engine_lock:
        _engine = engine


# ---------------------------------------------------------------------------
# Module-level wrappers (primary public API)
# ---------------------------------------------------------------------------

_TIER_ORDER = ["deepseek-chat", "gpt-4.1", "gpt-5.4"]


def is_circuit_open(tool: str) -> bool:
    """Return True if the circuit for *tool* is currently OPEN."""
    return _get_engine().is_open(tool)


def record_failure(tool: str) -> None:
    """Record a dispatch failure for *tool*."""
    _get_engine().record_failure(tool)


def record_success(tool: str) -> None:
    """Record a successful dispatch for *tool*."""
    _get_engine().record_success(tool)


def resolve_model(preferred: str) -> tuple[str, str | None]:
    """Return ``(model_to_use, escalation_reason)``.

    Applies the circuit breaker: if *preferred* is open, walks the tier
    list to find the next available model. Returns the preferred model
    unchanged (with reason ``None``) when its circuit is CLOSED.

    Args:
        preferred: The initially requested model name.

    Returns:
        A tuple ``(model, reason)`` where *reason* is ``None`` on a
        normal dispatch, ``"circuit_open:<model>"`` on escalation, or
        ``"all_circuits_open"`` when every tier is unavailable.
    """
    if not is_circuit_open(preferred):
        return preferred, None

    idx = _TIER_ORDER.index(preferred) if preferred in _TIER_ORDER else 0
    for fallback in _TIER_ORDER[idx + 1 :]:
        if not is_circuit_open(fallback):
            return fallback, f"circuit_open:{preferred}"

    return preferred, "all_circuits_open"


def get_circuit_status(tool: str | None = None) -> dict[str, Any]:
    """Return status dict for *tool*, or all known tier models if None."""
    engine = _get_engine()
    if tool is not None:
        return engine.get_status(tool)
    return {t: engine.get_status(t) for t in _TIER_ORDER}


def reset_circuit(tool: str) -> dict[str, Any]:
    """Manually reset *tool*'s circuit to CLOSED.

    Returns a result dict with ``reset`` on success or ``error`` on failure.
    """
    if tool not in _TIER_ORDER:
        return {"error": f"unknown model: {tool}"}
    _get_engine().reset(tool)
    return {"reset": tool}
