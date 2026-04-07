"""
Dead Letter Queue (DLQ) for Lore dispatch failures.

Captures failed tasks with classification, supports TTL-based expiry,
out-of-band replay for TRANSIENT/AMBIGUOUS failures, and alert thresholds.

Usage (module-level wrappers)::

    from lore.dlq import enqueue_failure, get_pending, resolve_entry, replay_pending
    from lore.dlq import dlq_depth, dlq_alert_check, classify_failure, FailureClass

    # Classify an error
    fc = classify_failure(exc, str(exc))

    # Enqueue a failed task
    entry_id = enqueue_failure(
        task_type="dispatch",
        prompt="...",
        payload={"model": "gpt-4"},
        error=exc,
        error_msg=str(exc),
    )

    # Check depth
    depth = dlq_depth()
    if dlq_alert_check():
        logger.warning("DLQ depth exceeded alert threshold")

    # Replay pending entries
    replayed = replay_pending(handler=my_retry_fn)
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from lore.config import get_dlq_db_path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DLQ_ALERT_THRESHOLD = 50
DLQ_DEFAULT_TTL_DAYS = 7
DLQ_MAX_TTL_DAYS = 30
DLQ_DEFAULT_REPLAY_RATE = 10  # entries per minute

# ---------------------------------------------------------------------------
# FailureClass enum
# ---------------------------------------------------------------------------


class FailureClass(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    AMBIGUOUS = "ambiguous"


# ---------------------------------------------------------------------------
# DLQEntry — frozen dataclass (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DLQEntry:
    """Immutable record of a failed task in the DLQ.

    Args:
        entry_id:       UUID4 string identifier.
        task_type:      Logical name of the task (e.g. "dispatch", "evolve").
        prompt_hash:    SHA-256 of the first 200 chars of the prompt.
        payload:        Arbitrary task payload dict.
        failure_class:  Classification of the failure.
        attempt_count:  Number of dispatch attempts so far.
        last_error:     String representation of the last error.
        created_at:     Unix timestamp of initial enqueueing.
        expires_at:     Unix timestamp after which the entry may be purged.
        resolved_at:    Unix timestamp of resolution, or None if pending.
    """

    entry_id: str
    task_type: str
    prompt_hash: str
    payload: dict
    failure_class: FailureClass
    attempt_count: int
    last_error: str
    created_at: float
    expires_at: float
    resolved_at: float | None = None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dlq_entries (
    entry_id        TEXT PRIMARY KEY,
    task_type       TEXT NOT NULL,
    prompt_hash     TEXT NOT NULL,
    payload         TEXT NOT NULL,
    failure_class   TEXT NOT NULL,
    attempt_count   INTEGER NOT NULL DEFAULT 1,
    last_error      TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL,
    expires_at      REAL NOT NULL,
    resolved_at     REAL
);

CREATE INDEX IF NOT EXISTS idx_dlq_task_type       ON dlq_entries (task_type);
CREATE INDEX IF NOT EXISTS idx_dlq_failure_class   ON dlq_entries (failure_class);
CREATE INDEX IF NOT EXISTS idx_dlq_resolved_at     ON dlq_entries (resolved_at);
CREATE INDEX IF NOT EXISTS idx_dlq_expires_at      ON dlq_entries (expires_at);
"""


# ---------------------------------------------------------------------------
# DLQStore — SQLite-backed persistence
# ---------------------------------------------------------------------------


class DLQStore:
    """Persistent SQLite store for DLQ entries.

    Uses WAL mode and busy_timeout=5000 for multi-process safety.
    Per-task-type queues are supported via task_type filtering.

    Args:
        db_path:  Path to the SQLite database. Defaults to config value.
        ttl_days: Default TTL for new entries (7–30 days).
    """

    def __init__(
        self,
        db_path: Path | None = None,
        ttl_days: int = DLQ_DEFAULT_TTL_DAYS,
    ) -> None:
        if db_path is None:
            db_path = get_dlq_db_path()
        self._db_path = db_path
        self._ttl_days = max(1, min(ttl_days, DLQ_MAX_TTL_DAYS))
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    # -- Connection management -----------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection."""
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

    # -- Write operations ----------------------------------------------------

    def enqueue(self, entry: DLQEntry) -> str:
        """Insert a new DLQ entry. Returns entry_id."""
        conn = self._conn()
        conn.execute(
            """
            INSERT INTO dlq_entries
                (entry_id, task_type, prompt_hash, payload, failure_class,
                 attempt_count, last_error, created_at, expires_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.entry_id,
                entry.task_type,
                entry.prompt_hash,
                json.dumps(entry.payload),
                entry.failure_class.value,
                entry.attempt_count,
                entry.last_error,
                entry.created_at,
                entry.expires_at,
                entry.resolved_at,
            ),
        )
        conn.commit()
        return entry.entry_id

    def resolve(self, entry_id: str) -> bool:
        """Mark an entry as resolved. Returns True if a row was updated."""
        conn = self._conn()
        cursor = conn.execute(
            "UPDATE dlq_entries SET resolved_at = ? WHERE entry_id = ? AND resolved_at IS NULL",
            (time.time(), entry_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def increment_attempt(self, entry_id: str, last_error: str) -> None:
        """Increment attempt_count and update last_error for *entry_id*."""
        conn = self._conn()
        conn.execute(
            "UPDATE dlq_entries SET attempt_count = attempt_count + 1, last_error = ? WHERE entry_id = ?",
            (last_error, entry_id),
        )
        conn.commit()

    def purge_expired(self) -> int:
        """Delete entries past their expires_at. Returns count deleted."""
        now = time.time()
        conn = self._conn()
        cursor = conn.execute(
            "DELETE FROM dlq_entries WHERE expires_at < ? AND resolved_at IS NULL",
            (now,),
        )
        conn.commit()
        return cursor.rowcount

    # -- Read operations -----------------------------------------------------

    def get_entry(self, entry_id: str) -> DLQEntry | None:
        """Fetch a single entry by ID."""
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM dlq_entries WHERE entry_id = ?", (entry_id,)
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def get_pending(
        self,
        task_type: str | None = None,
        include_permanent: bool = False,
        limit: int = 200,
    ) -> list[DLQEntry]:
        """Return unresolved, unexpired entries.

        Args:
            task_type:        Filter by task type. None = all types.
            include_permanent: Include PERMANENT failures (default False).
            limit:            Max entries to return.
        """
        now = time.time()
        params: list[Any] = [now]
        query = (
            "SELECT * FROM dlq_entries"
            " WHERE resolved_at IS NULL AND expires_at >= ?"
        )
        if task_type is not None:
            query += " AND task_type = ?"
            params.append(task_type)
        if not include_permanent:
            query += " AND failure_class != ?"
            params.append(FailureClass.PERMANENT.value)
        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(limit)

        conn = self._conn()
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def depth(self, task_type: str | None = None) -> int:
        """Count unresolved, unexpired entries (optionally filtered by task_type)."""
        now = time.time()
        params: list[Any] = [now]
        query = (
            "SELECT COUNT(*) FROM dlq_entries"
            " WHERE resolved_at IS NULL AND expires_at >= ?"
        )
        if task_type is not None:
            query += " AND task_type = ?"
            params.append(task_type)
        conn = self._conn()
        row = conn.execute(query, params).fetchone()
        return int(row[0])

    # -- Helpers -------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> DLQEntry:
        return DLQEntry(
            entry_id=row["entry_id"],
            task_type=row["task_type"],
            prompt_hash=row["prompt_hash"],
            payload=json.loads(row["payload"]),
            failure_class=FailureClass(row["failure_class"]),
            attempt_count=row["attempt_count"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            resolved_at=row["resolved_at"],
        )

    def make_entry(
        self,
        task_type: str,
        prompt: str,
        payload: dict,
        failure_class: FailureClass,
        error_msg: str,
        ttl_days: int | None = None,
    ) -> DLQEntry:
        """Construct a new DLQEntry (does NOT persist — call enqueue() next)."""
        ttl = ttl_days if ttl_days is not None else self._ttl_days
        ttl = max(1, min(ttl, DLQ_MAX_TTL_DAYS))
        now = time.time()
        prompt_hash = hashlib.sha256(prompt[:200].encode()).hexdigest()
        return DLQEntry(
            entry_id=str(uuid.uuid4()),
            task_type=task_type,
            prompt_hash=prompt_hash,
            payload=dict(payload),
            failure_class=failure_class,
            attempt_count=1,
            last_error=error_msg,
            created_at=now,
            expires_at=now + ttl * 86400,
            resolved_at=None,
        )


# ---------------------------------------------------------------------------
# DLQConsumer — out-of-band replay
# ---------------------------------------------------------------------------


class DLQConsumer:
    """Replays pending DLQ entries at a configurable rate.

    Skips PERMANENT failures entirely. Monitors liveness by tracking
    the last successful replay timestamp.

    Args:
        store:        DLQStore to read from and write to.
        rate_per_min: Maximum replays per minute (default 10).
    """

    def __init__(
        self,
        store: DLQStore,
        rate_per_min: int = DLQ_DEFAULT_REPLAY_RATE,
    ) -> None:
        self._store = store
        self._rate_per_min = max(1, rate_per_min)
        self._min_interval = 60.0 / self._rate_per_min  # seconds between replays
        self._last_replay_ts: float = 0.0
        self._total_replayed: int = 0
        self._total_failed: int = 0
        self._lock = threading.Lock()

    @property
    def last_replay_ts(self) -> float:
        """Unix timestamp of the last successful replay attempt."""
        return self._last_replay_ts

    @property
    def total_replayed(self) -> int:
        return self._total_replayed

    @property
    def total_failed(self) -> int:
        return self._total_failed

    def is_alive(self, max_silence_secs: float = 300.0) -> bool:
        """Return True if the consumer has replayed within *max_silence_secs*.

        Returns True unconditionally when there are no pending entries.
        """
        if self._store.depth() == 0:
            return True
        if self._last_replay_ts == 0.0:
            return False
        return (time.time() - self._last_replay_ts) < max_silence_secs

    def replay_one(
        self,
        entry: DLQEntry,
        handler: Callable[[DLQEntry], bool],
    ) -> bool:
        """Replay a single entry using *handler*.

        PERMANENT entries are silently skipped (returns False).
        handler should return True on success, False on failure.
        On success the entry is resolved. On failure attempt_count is incremented.

        Returns True if the entry was successfully replayed.
        """
        if entry.failure_class == FailureClass.PERMANENT:
            return False

        with self._lock:
            now = time.time()
            elapsed = now - self._last_replay_ts
            if elapsed < self._min_interval:
                # Rate limit — caller should wait
                return False

            try:
                success = handler(entry)
            except Exception as exc:  # noqa: BLE001
                logger.warning("dlq: replay handler raised for %s: %s", entry.entry_id, exc)
                success = False

            if success:
                self._store.resolve(entry.entry_id)
                self._total_replayed += 1
                self._last_replay_ts = time.time()
                logger.info("dlq: replayed %s (%s)", entry.entry_id, entry.task_type)
            else:
                self._store.increment_attempt(entry.entry_id, "replay failed")
                self._total_failed += 1
                self._last_replay_ts = time.time()

            return success

    def replay_batch(
        self,
        handler: Callable[[DLQEntry], bool],
        task_type: str | None = None,
        max_entries: int = 50,
    ) -> dict[str, int]:
        """Replay up to *max_entries* pending entries.

        Rate limiting applies to the batch as a whole (gates how often a batch
        can be triggered), not between individual entries within the batch.
        PERMANENT entries are excluded by the store query.

        Args:
            handler:     Callable receiving a DLQEntry, returning True on success.
            task_type:   Optional filter for task type.
            max_entries: Maximum entries to attempt in this batch.

        Returns:
            Dict with keys ``replayed``, ``failed``, ``skipped`` (rate-limited).
        """
        # Rate-limit the batch invocation itself
        with self._lock:
            now = time.time()
            elapsed = now - self._last_replay_ts
            if self._last_replay_ts > 0 and elapsed < self._min_interval:
                return {"replayed": 0, "failed": 0, "skipped": -1}  # batch skipped
            # Mark that a batch is in progress by setting ts now
            self._last_replay_ts = now

        pending = self._store.get_pending(
            task_type=task_type,
            include_permanent=False,
            limit=max_entries,
        )
        replayed = 0
        failed = 0

        for entry in pending:
            try:
                success = handler(entry)
            except Exception as exc:  # noqa: BLE001
                logger.warning("dlq: replay handler raised for %s: %s", entry.entry_id, exc)
                success = False

            with self._lock:
                if success:
                    self._store.resolve(entry.entry_id)
                    self._total_replayed += 1
                    replayed += 1
                    logger.info("dlq: replayed %s (%s)", entry.entry_id, entry.task_type)
                else:
                    self._store.increment_attempt(entry.entry_id, "replay failed")
                    self._total_failed += 1
                    failed += 1

        with self._lock:
            self._last_replay_ts = time.time()

        return {"replayed": replayed, "failed": failed, "skipped": 0}


# ---------------------------------------------------------------------------
# classify_failure — pure function
# ---------------------------------------------------------------------------

_TRANSIENT_KEYWORDS = frozenset(
    ["timeout", "rate limit", "503", "429", "connection", "temporary"]
)
_PERMANENT_KEYWORDS = frozenset(
    ["invalid api key", "not found", "unauthorized", "400", "context length exceeded"]
)


def classify_failure(error: Exception, error_msg: str) -> FailureClass:
    """Classify an exception into TRANSIENT, PERMANENT, or AMBIGUOUS.

    Pure function — no side effects.

    Args:
        error:     The exception instance (type name may be used in future).
        error_msg: String representation of the error message.

    Returns:
        FailureClass enum value.
    """
    lower = error_msg.lower()

    for keyword in _TRANSIENT_KEYWORDS:
        if keyword in lower:
            return FailureClass.TRANSIENT

    for keyword in _PERMANENT_KEYWORDS:
        if keyword in lower:
            return FailureClass.PERMANENT

    return FailureClass.AMBIGUOUS


# ---------------------------------------------------------------------------
# Singleton store
# ---------------------------------------------------------------------------

_store_lock = threading.Lock()
_store: DLQStore | None = None


def _get_store() -> DLQStore:
    """Return the process-level singleton DLQStore (lazy init)."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = DLQStore()
    return _store


def _set_store(store: DLQStore) -> None:
    """Replace the singleton store (for tests / dependency injection)."""
    global _store
    with _store_lock:
        _store = store


# ---------------------------------------------------------------------------
# Module-level wrappers (primary public API)
# ---------------------------------------------------------------------------


def enqueue_failure(
    task_type: str,
    prompt: str,
    payload: dict,
    error: Exception,
    error_msg: str | None = None,
    ttl_days: int | None = None,
) -> str:
    """Enqueue a failed task into the DLQ.

    Args:
        task_type: Logical task category (e.g. "dispatch").
        prompt:    Original prompt text (first 200 chars hashed).
        payload:   Arbitrary task payload dict.
        error:     The exception that caused the failure.
        error_msg: Override error message (defaults to str(error)).
        ttl_days:  TTL override. Uses store default if None.

    Returns:
        The entry_id (UUID4 string) of the created entry.
    """
    store = _get_store()
    msg = error_msg if error_msg is not None else str(error)
    fc = classify_failure(error, msg)
    entry = store.make_entry(
        task_type=task_type,
        prompt=prompt,
        payload=payload,
        failure_class=fc,
        error_msg=msg,
        ttl_days=ttl_days,
    )
    store.enqueue(entry)
    logger.info(
        "dlq: enqueued %s task_type=%s class=%s",
        entry.entry_id,
        task_type,
        fc.value,
    )
    return entry.entry_id


def get_pending(
    task_type: str | None = None,
    include_permanent: bool = False,
    limit: int = 200,
) -> list[DLQEntry]:
    """Return unresolved, unexpired DLQ entries.

    Args:
        task_type:         Optional filter.
        include_permanent: Include PERMANENT failures (default False).
        limit:             Max entries to return.
    """
    return _get_store().get_pending(
        task_type=task_type,
        include_permanent=include_permanent,
        limit=limit,
    )


def resolve_entry(entry_id: str) -> bool:
    """Mark a DLQ entry as resolved.

    Returns True if the entry existed and was pending, False otherwise.
    """
    result = _get_store().resolve(entry_id)
    if result:
        logger.info("dlq: resolved %s", entry_id)
    return result


def replay_pending(
    handler: Callable[[DLQEntry], bool],
    task_type: str | None = None,
    max_entries: int = 50,
    rate_per_min: int = DLQ_DEFAULT_REPLAY_RATE,
) -> dict[str, int]:
    """Replay pending DLQ entries using *handler*.

    PERMANENT failures are never replayed.

    Args:
        handler:     Callable receiving a DLQEntry, returning True on success.
        task_type:   Optional task_type filter.
        max_entries: Max entries to attempt.
        rate_per_min: Replay rate cap.

    Returns:
        Dict with keys ``replayed``, ``failed``, ``skipped``.
    """
    store = _get_store()
    consumer = DLQConsumer(store=store, rate_per_min=rate_per_min)
    return consumer.replay_batch(
        handler=handler,
        task_type=task_type,
        max_entries=max_entries,
    )


def dlq_depth(task_type: str | None = None) -> int:
    """Return the count of unresolved, unexpired DLQ entries."""
    return _get_store().depth(task_type=task_type)


def dlq_alert_check(task_type: str | None = None) -> bool:
    """Return True if DLQ depth exceeds the alert threshold (50 entries)."""
    return dlq_depth(task_type=task_type) > DLQ_ALERT_THRESHOLD
