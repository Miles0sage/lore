"""Tests for lore/dlq.py — Dead Letter Queue module."""

from __future__ import annotations

import dataclasses
import time
import uuid
from pathlib import Path

import pytest

from lore.dlq import (
    DLQ_ALERT_THRESHOLD,
    DLQConsumer,
    DLQEntry,
    DLQStore,
    FailureClass,
    classify_failure,
    dlq_alert_check,
    dlq_depth,
    enqueue_failure,
    get_pending,
    replay_pending,
    resolve_entry,
    _set_store,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_store(tmp_path: Path) -> DLQStore:
    """DLQStore backed by a temp directory; injected into module singleton."""
    store = DLQStore(db_path=tmp_path / "dlq.db", ttl_days=7)
    _set_store(store)
    return store


@pytest.fixture()
def sample_entry(tmp_store: DLQStore) -> DLQEntry:
    return tmp_store.make_entry(
        task_type="dispatch",
        prompt="Hello world",
        payload={"model": "gpt-4"},
        failure_class=FailureClass.TRANSIENT,
        error_msg="connection timeout",
    )


# ---------------------------------------------------------------------------
# classify_failure
# ---------------------------------------------------------------------------


class TestClassifyFailure:
    def test_transient_timeout(self):
        assert classify_failure(Exception(), "request timeout after 30s") == FailureClass.TRANSIENT

    def test_transient_rate_limit(self):
        assert classify_failure(Exception(), "rate limit exceeded") == FailureClass.TRANSIENT

    def test_transient_503(self):
        assert classify_failure(Exception(), "server returned 503") == FailureClass.TRANSIENT

    def test_transient_429(self):
        assert classify_failure(Exception(), "HTTP 429 too many requests") == FailureClass.TRANSIENT

    def test_transient_connection(self):
        assert classify_failure(Exception(), "connection refused") == FailureClass.TRANSIENT

    def test_transient_temporary(self):
        assert classify_failure(Exception(), "temporary failure in name resolution") == FailureClass.TRANSIENT

    def test_permanent_invalid_api_key(self):
        assert classify_failure(Exception(), "invalid api key provided") == FailureClass.PERMANENT

    def test_permanent_not_found(self):
        assert classify_failure(Exception(), "resource not found") == FailureClass.PERMANENT

    def test_permanent_unauthorized(self):
        assert classify_failure(Exception(), "401 unauthorized access") == FailureClass.PERMANENT

    def test_permanent_400(self):
        assert classify_failure(Exception(), "bad request 400") == FailureClass.PERMANENT

    def test_permanent_context_length(self):
        assert classify_failure(Exception(), "context length exceeded maximum") == FailureClass.PERMANENT

    def test_ambiguous_unknown(self):
        assert classify_failure(Exception(), "something went wrong internally") == FailureClass.AMBIGUOUS

    def test_ambiguous_empty(self):
        assert classify_failure(Exception(), "") == FailureClass.AMBIGUOUS

    def test_pure_no_side_effects(self):
        """classify_failure must be pure — repeated calls return same result."""
        msg = "connection timeout"
        exc = Exception(msg)
        r1 = classify_failure(exc, msg)
        r2 = classify_failure(exc, msg)
        assert r1 == r2 == FailureClass.TRANSIENT

    def test_case_insensitive(self):
        assert classify_failure(Exception(), "TIMEOUT occurred") == FailureClass.TRANSIENT
        assert classify_failure(Exception(), "INVALID API KEY") == FailureClass.PERMANENT


# ---------------------------------------------------------------------------
# DLQEntry — frozen dataclass
# ---------------------------------------------------------------------------


class TestDLQEntry:
    def test_frozen(self, sample_entry: DLQEntry):
        with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
            sample_entry.task_type = "mutated"  # type: ignore[misc]

    def test_fields_present(self, sample_entry: DLQEntry):
        assert sample_entry.entry_id
        assert sample_entry.task_type == "dispatch"
        assert len(sample_entry.prompt_hash) == 64  # SHA-256 hex
        assert sample_entry.payload == {"model": "gpt-4"}
        assert sample_entry.failure_class == FailureClass.TRANSIENT
        assert sample_entry.attempt_count == 1
        assert sample_entry.last_error == "connection timeout"
        assert sample_entry.created_at > 0
        assert sample_entry.expires_at > sample_entry.created_at
        assert sample_entry.resolved_at is None

    def test_entry_id_is_uuid4(self, sample_entry: DLQEntry):
        parsed = uuid.UUID(sample_entry.entry_id, version=4)
        assert str(parsed) == sample_entry.entry_id

    def test_prompt_hash_sha256(self, tmp_store: DLQStore):
        import hashlib
        prompt = "test prompt"
        entry = tmp_store.make_entry(
            task_type="t",
            prompt=prompt,
            payload={},
            failure_class=FailureClass.AMBIGUOUS,
            error_msg="err",
        )
        expected = hashlib.sha256(prompt[:200].encode()).hexdigest()
        assert entry.prompt_hash == expected

    def test_prompt_truncated_to_200(self, tmp_store: DLQStore):
        import hashlib
        long_prompt = "x" * 500
        entry = tmp_store.make_entry(
            task_type="t",
            prompt=long_prompt,
            payload={},
            failure_class=FailureClass.AMBIGUOUS,
            error_msg="err",
        )
        expected = hashlib.sha256(("x" * 200).encode()).hexdigest()
        assert entry.prompt_hash == expected


# ---------------------------------------------------------------------------
# DLQStore — SQLite persistence
# ---------------------------------------------------------------------------


class TestDLQStorePersistence:
    def test_enqueue_and_retrieve(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        fetched = tmp_store.get_entry(sample_entry.entry_id)
        assert fetched is not None
        assert fetched.entry_id == sample_entry.entry_id
        assert fetched.task_type == sample_entry.task_type
        assert fetched.payload == sample_entry.payload
        assert fetched.failure_class == sample_entry.failure_class

    def test_get_entry_missing(self, tmp_store: DLQStore):
        assert tmp_store.get_entry("nonexistent-id") is None

    def test_resolve_marks_resolved(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        result = tmp_store.resolve(sample_entry.entry_id)
        assert result is True
        fetched = tmp_store.get_entry(sample_entry.entry_id)
        assert fetched is not None
        assert fetched.resolved_at is not None

    def test_resolve_already_resolved(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        tmp_store.resolve(sample_entry.entry_id)
        # Second resolve should return False (already resolved)
        result = tmp_store.resolve(sample_entry.entry_id)
        assert result is False

    def test_resolve_nonexistent(self, tmp_store: DLQStore):
        result = tmp_store.resolve("no-such-id")
        assert result is False

    def test_get_pending_excludes_resolved(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        tmp_store.resolve(sample_entry.entry_id)
        pending = tmp_store.get_pending()
        assert all(e.entry_id != sample_entry.entry_id for e in pending)

    def test_get_pending_excludes_permanent(self, tmp_store: DLQStore):
        entry = tmp_store.make_entry(
            task_type="t", prompt="p", payload={},
            failure_class=FailureClass.PERMANENT, error_msg="bad key"
        )
        tmp_store.enqueue(entry)
        pending = tmp_store.get_pending(include_permanent=False)
        assert all(e.failure_class != FailureClass.PERMANENT for e in pending)

    def test_get_pending_include_permanent(self, tmp_store: DLQStore):
        entry = tmp_store.make_entry(
            task_type="t", prompt="p", payload={},
            failure_class=FailureClass.PERMANENT, error_msg="bad key"
        )
        tmp_store.enqueue(entry)
        pending = tmp_store.get_pending(include_permanent=True)
        assert any(e.entry_id == entry.entry_id for e in pending)

    def test_get_pending_task_type_filter(self, tmp_store: DLQStore):
        e1 = tmp_store.make_entry("alpha", "p", {}, FailureClass.TRANSIENT, "err")
        e2 = tmp_store.make_entry("beta", "p", {}, FailureClass.TRANSIENT, "err")
        tmp_store.enqueue(e1)
        tmp_store.enqueue(e2)
        alpha_pending = tmp_store.get_pending(task_type="alpha")
        assert all(e.task_type == "alpha" for e in alpha_pending)
        assert any(e.entry_id == e1.entry_id for e in alpha_pending)

    def test_depth_count(self, tmp_store: DLQStore):
        for i in range(5):
            e = tmp_store.make_entry("t", f"prompt{i}", {}, FailureClass.TRANSIENT, "err")
            tmp_store.enqueue(e)
        assert tmp_store.depth() == 5

    def test_depth_excludes_resolved(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        tmp_store.resolve(sample_entry.entry_id)
        assert tmp_store.depth() == 0

    def test_increment_attempt(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        tmp_store.increment_attempt(sample_entry.entry_id, "new error")
        fetched = tmp_store.get_entry(sample_entry.entry_id)
        assert fetched is not None
        assert fetched.attempt_count == 2
        assert fetched.last_error == "new error"

    def test_wal_mode_enabled(self, tmp_store: DLQStore):
        conn = tmp_store._conn()
        row = conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0] == "wal"

    def test_payload_roundtrip(self, tmp_store: DLQStore):
        payload = {"nested": {"key": [1, 2, 3]}, "flag": True}
        entry = tmp_store.make_entry("t", "p", payload, FailureClass.AMBIGUOUS, "err")
        tmp_store.enqueue(entry)
        fetched = tmp_store.get_entry(entry.entry_id)
        assert fetched is not None
        assert fetched.payload == payload


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    def test_expired_entry_excluded_from_pending(self, tmp_path: Path):
        store = DLQStore(db_path=tmp_path / "dlq.db", ttl_days=1)
        _set_store(store)
        entry = store.make_entry("t", "p", {}, FailureClass.TRANSIENT, "err")
        # Manually create entry with past expires_at
        expired_entry = dataclasses.replace(
            entry,
            entry_id=str(uuid.uuid4()),
            expires_at=time.time() - 1,  # already expired
        )
        store.enqueue(expired_entry)
        pending = store.get_pending()
        assert all(e.entry_id != expired_entry.entry_id for e in pending)

    def test_expired_entry_excluded_from_depth(self, tmp_path: Path):
        store = DLQStore(db_path=tmp_path / "dlq.db", ttl_days=1)
        _set_store(store)
        entry = store.make_entry("t", "p", {}, FailureClass.TRANSIENT, "err")
        expired_entry = dataclasses.replace(
            entry,
            entry_id=str(uuid.uuid4()),
            expires_at=time.time() - 1,
        )
        store.enqueue(expired_entry)
        assert store.depth() == 0

    def test_purge_expired_removes_rows(self, tmp_path: Path):
        store = DLQStore(db_path=tmp_path / "dlq.db")
        _set_store(store)
        entry = store.make_entry("t", "p", {}, FailureClass.TRANSIENT, "err")
        expired_entry = dataclasses.replace(
            entry,
            entry_id=str(uuid.uuid4()),
            expires_at=time.time() - 1,
        )
        store.enqueue(expired_entry)
        deleted = store.purge_expired()
        assert deleted == 1

    def test_ttl_clamped_to_max(self, tmp_path: Path):
        store = DLQStore(db_path=tmp_path / "dlq.db", ttl_days=999)
        # store._ttl_days should be clamped to DLQ_MAX_TTL_DAYS
        from lore.dlq import DLQ_MAX_TTL_DAYS
        assert store._ttl_days == DLQ_MAX_TTL_DAYS


# ---------------------------------------------------------------------------
# DLQConsumer — rate limiting and replay
# ---------------------------------------------------------------------------


class TestDLQConsumer:
    def test_replay_one_success(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        consumer = DLQConsumer(store=tmp_store, rate_per_min=600)  # fast rate

        replayed = consumer.replay_one(sample_entry, handler=lambda e: True)
        assert replayed is True
        assert consumer.total_replayed == 1

        fetched = tmp_store.get_entry(sample_entry.entry_id)
        assert fetched is not None
        assert fetched.resolved_at is not None

    def test_replay_one_failure(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        consumer = DLQConsumer(store=tmp_store, rate_per_min=600)

        replayed = consumer.replay_one(sample_entry, handler=lambda e: False)
        assert replayed is False
        assert consumer.total_failed == 1

        fetched = tmp_store.get_entry(sample_entry.entry_id)
        assert fetched is not None
        assert fetched.resolved_at is None

    def test_replay_skips_permanent(self, tmp_store: DLQStore):
        entry = tmp_store.make_entry(
            "t", "p", {}, FailureClass.PERMANENT, "invalid api key"
        )
        tmp_store.enqueue(entry)
        consumer = DLQConsumer(store=tmp_store, rate_per_min=600)

        replayed = consumer.replay_one(entry, handler=lambda e: True)
        assert replayed is False
        # Entry should remain unresolved
        fetched = tmp_store.get_entry(entry.entry_id)
        assert fetched is not None
        assert fetched.resolved_at is None

    def test_rate_limiting(self, tmp_store: DLQStore):
        """Consumer should block replays faster than the configured rate."""
        e1 = tmp_store.make_entry("t", "p1", {}, FailureClass.TRANSIENT, "err")
        e2 = tmp_store.make_entry("t", "p2", {}, FailureClass.TRANSIENT, "err")
        tmp_store.enqueue(e1)
        tmp_store.enqueue(e2)

        # 1/min rate = 60 second interval; second replay should be rate-limited
        consumer = DLQConsumer(store=tmp_store, rate_per_min=1)
        r1 = consumer.replay_one(e1, handler=lambda e: True)
        r2 = consumer.replay_one(e2, handler=lambda e: True)
        # First should succeed, second should be rate-limited (returns False)
        assert r1 is True
        assert r2 is False

    def test_replay_batch_results(self, tmp_store: DLQStore):
        for i in range(5):
            e = tmp_store.make_entry("t", f"p{i}", {}, FailureClass.TRANSIENT, "err")
            tmp_store.enqueue(e)

        consumer = DLQConsumer(store=tmp_store, rate_per_min=600)
        results = consumer.replay_batch(handler=lambda e: True, max_entries=10)
        assert results["replayed"] == 5
        assert results["failed"] == 0
        assert results["skipped"] == 0

    def test_replay_batch_excludes_permanent(self, tmp_store: DLQStore):
        perm = tmp_store.make_entry("t", "p", {}, FailureClass.PERMANENT, "bad key")
        trans = tmp_store.make_entry("t", "q", {}, FailureClass.TRANSIENT, "timeout")
        tmp_store.enqueue(perm)
        tmp_store.enqueue(trans)

        consumer = DLQConsumer(store=tmp_store, rate_per_min=600)
        results = consumer.replay_batch(handler=lambda e: True)
        # Only transient replayed; permanent excluded from get_pending
        assert results["replayed"] == 1

    def test_liveness_no_pending(self, tmp_store: DLQStore):
        consumer = DLQConsumer(store=tmp_store, rate_per_min=10)
        assert consumer.is_alive() is True  # no pending = alive

    def test_liveness_never_replayed(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        consumer = DLQConsumer(store=tmp_store, rate_per_min=10)
        assert consumer.is_alive(max_silence_secs=60) is False

    def test_liveness_after_replay(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        consumer = DLQConsumer(store=tmp_store, rate_per_min=600)
        consumer.replay_one(sample_entry, handler=lambda e: True)
        assert consumer.is_alive(max_silence_secs=60) is True

    def test_handler_exception_counted_as_failure(self, tmp_store: DLQStore, sample_entry: DLQEntry):
        tmp_store.enqueue(sample_entry)
        consumer = DLQConsumer(store=tmp_store, rate_per_min=600)

        def bad_handler(e: DLQEntry) -> bool:
            raise RuntimeError("handler blew up")

        result = consumer.replay_one(sample_entry, handler=bad_handler)
        assert result is False
        assert consumer.total_failed == 1


# ---------------------------------------------------------------------------
# Module-level wrappers
# ---------------------------------------------------------------------------


class TestModuleWrappers:
    def test_enqueue_failure_returns_id(self, tmp_store: DLQStore):
        entry_id = enqueue_failure(
            task_type="dispatch",
            prompt="hello",
            payload={"k": "v"},
            error=ConnectionError("connection timeout"),
        )
        assert entry_id
        assert uuid.UUID(entry_id, version=4)

    def test_enqueue_failure_classifies_correctly(self, tmp_store: DLQStore):
        entry_id = enqueue_failure(
            task_type="dispatch",
            prompt="hello",
            payload={},
            error=Exception("invalid api key"),
        )
        pending = get_pending(include_permanent=True)
        match = next((e for e in pending if e.entry_id == entry_id), None)
        assert match is not None
        assert match.failure_class == FailureClass.PERMANENT

    def test_get_pending_returns_list(self, tmp_store: DLQStore):
        enqueue_failure("t", "p", {}, Exception("timeout"))
        result = get_pending()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_resolve_entry(self, tmp_store: DLQStore):
        entry_id = enqueue_failure("t", "p", {}, Exception("connection error"))
        assert resolve_entry(entry_id) is True
        pending = get_pending()
        assert all(e.entry_id != entry_id for e in pending)

    def test_resolve_entry_missing(self, tmp_store: DLQStore):
        assert resolve_entry("no-such-entry") is False

    def test_replay_pending_succeeds(self, tmp_store: DLQStore):
        enqueue_failure("t", "p", {}, Exception("timeout"))
        results = replay_pending(handler=lambda e: True, rate_per_min=600)
        assert results["replayed"] >= 1

    def test_replay_pending_skips_permanent(self, tmp_store: DLQStore):
        enqueue_failure("t", "p", {}, Exception("invalid api key"))
        results = replay_pending(handler=lambda e: True, rate_per_min=600)
        assert results["replayed"] == 0

    def test_dlq_depth_count(self, tmp_store: DLQStore):
        initial = dlq_depth()
        enqueue_failure("t", "p1", {}, Exception("timeout"))
        enqueue_failure("t", "p2", {}, Exception("connection error"))
        assert dlq_depth() == initial + 2

    def test_dlq_depth_task_type_filter(self, tmp_store: DLQStore):
        enqueue_failure("alpha", "p", {}, Exception("timeout"))
        enqueue_failure("beta", "p", {}, Exception("timeout"))
        assert dlq_depth("alpha") >= 1
        assert dlq_depth("beta") >= 1

    def test_dlq_alert_check_below_threshold(self, tmp_store: DLQStore):
        assert dlq_alert_check() is False

    def test_dlq_alert_check_above_threshold(self, tmp_path: Path):
        store = DLQStore(db_path=tmp_path / "alert_dlq.db")
        _set_store(store)
        for i in range(DLQ_ALERT_THRESHOLD + 1):
            e = store.make_entry("t", f"p{i}", {}, FailureClass.TRANSIENT, "err")
            store.enqueue(e)
        assert dlq_alert_check() is True

    def test_dlq_alert_threshold_is_50(self):
        assert DLQ_ALERT_THRESHOLD == 50


# ---------------------------------------------------------------------------
# SQLite multi-thread safety smoke test
# ---------------------------------------------------------------------------


class TestSQLiteSafety:
    def test_concurrent_enqueue(self, tmp_path: Path):
        import threading

        store = DLQStore(db_path=tmp_path / "concurrent.db")
        errors = []

        def worker(i: int) -> None:
            try:
                e = store.make_entry(f"t{i}", f"p{i}", {}, FailureClass.TRANSIENT, "err")
                store.enqueue(e)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent enqueue errors: {errors}"
        assert store.depth() == 20
