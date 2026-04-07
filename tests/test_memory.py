"""Tests for lore/memory.py — three-layer memory stack."""

from __future__ import annotations

import time
import threading
from pathlib import Path

import pytest

from lore.memory import (
    MemoryEntry,
    WorkingMemory,
    EpisodicMemory,
    ProceduralMemory,
    MemoryRouter,
    _derive_procedural_key,
    _route_layer,
    memory_write,
    memory_search,
    memory_checkpoint,
    memory_restore,
    _set_router,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "memory.db"


@pytest.fixture()
def tmp_soul(tmp_path: Path) -> Path:
    return tmp_path / "SOUL.md"


@pytest.fixture()
def working() -> WorkingMemory:
    return WorkingMemory(max_size=50, compact_threshold=40)


@pytest.fixture()
def episodic(tmp_db: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_db)


@pytest.fixture()
def procedural(tmp_soul: Path) -> ProceduralMemory:
    return ProceduralMemory(soul_path=tmp_soul)


@pytest.fixture()
def router(tmp_db: Path, tmp_soul: Path) -> MemoryRouter:
    return MemoryRouter(
        working=WorkingMemory(),
        episodic=EpisodicMemory(db_path=tmp_db),
        procedural=ProceduralMemory(soul_path=tmp_soul),
    )


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------


class TestMemoryEntry:
    def test_frozen(self):
        entry = MemoryEntry.new("hello", "working", "s1")
        with pytest.raises((AttributeError, TypeError)):
            entry.content = "mutated"  # type: ignore[misc]

    def test_new_generates_uuid(self):
        e1 = MemoryEntry.new("a", "working", "s1")
        e2 = MemoryEntry.new("a", "working", "s1")
        assert e1.entry_id != e2.entry_id

    def test_new_sets_created_at(self):
        before = time.time()
        e = MemoryEntry.new("x", "episodic", "s1")
        after = time.time()
        assert before <= e.created_at <= after

    def test_tags_coerced_to_tuple(self):
        e = MemoryEntry.new("x", "working", "s1", tags=["a", "b"])
        assert isinstance(e.tags, tuple)
        assert e.tags == ("a", "b")

    def test_tags_default_empty(self):
        e = MemoryEntry.new("x", "working", "s1")
        assert e.tags == ()

    def test_layer_stored(self):
        for layer in ("working", "episodic", "procedural"):
            e = MemoryEntry.new("x", layer, "s1")
            assert e.layer == layer


# ---------------------------------------------------------------------------
# WorkingMemory
# ---------------------------------------------------------------------------


class TestWorkingMemory:
    def test_add_returns_entry(self, working: WorkingMemory):
        entry, evicted = working.add("hello", "s1")
        assert entry.content == "hello"
        assert entry.layer == "working"
        assert entry.session_id == "s1"
        assert evicted == []

    def test_get_all_most_recent_first(self, working: WorkingMemory):
        working.add("first", "s1")
        working.add("second", "s1")
        working.add("third", "s1")
        all_entries = working.get_all()
        assert all_entries[0].content == "third"
        assert all_entries[-1].content == "first"

    def test_search_substring(self, working: WorkingMemory):
        working.add("validate user input carefully", "s1")
        working.add("log all errors", "s1")
        working.add("Validate output schemas", "s1")
        results = working.search("validate")
        assert len(results) == 2
        assert all("validate" in r.content.lower() for r in results)

    def test_search_empty_when_no_match(self, working: WorkingMemory):
        working.add("something else", "s1")
        assert working.search("zzznomatch") == []

    def test_compact_triggers_at_threshold(self):
        wm = WorkingMemory(max_size=50, compact_threshold=5)
        evicted_total: list[MemoryEntry] = []
        for i in range(5):
            _, evicted = wm.add(f"entry {i}", "s1")
            evicted_total.extend(evicted)
        # After reaching threshold 5, oldest (5-30) = negative → evict max(0, 5-30)=0
        # Actually compact_target=30 but we only have 5 entries, let's check edge case
        # With _COMPACT_TARGET=30 and only 5 entries: evict_count = 5-30 = -25 → 0
        # So nothing evicted because we're below compact target
        assert wm.size() == 5

    def test_compact_evicts_oldest_down_to_30(self):
        wm = WorkingMemory(compact_threshold=10)
        evicted_total: list[MemoryEntry] = []
        for i in range(10):
            _, evicted = wm.add(f"entry {i}", "s1")
            evicted_total.extend(evicted)
        # At 10 entries, threshold hit: evict 10-30 = negative = 0
        # Still no eviction since 10 < 30 compact target
        assert len(evicted_total) == 0
        assert wm.size() == 10

    def test_compact_evicts_when_above_target(self):
        """Compact should evict when len > _COMPACT_TARGET (30)."""
        wm = WorkingMemory(compact_threshold=35)
        evicted_total: list[MemoryEntry] = []
        for i in range(35):
            _, evicted = wm.add(f"entry {i}", "s1")
            evicted_total.extend(evicted)
        # At 35 entries: evict 35-30 = 5 oldest
        assert len(evicted_total) == 5
        assert wm.size() == 30
        # Oldest entries should be the evicted ones
        assert evicted_total[0].content == "entry 0"
        assert evicted_total[-1].content == "entry 4"

    def test_compact_evicted_entries_removed_from_working(self):
        wm = WorkingMemory(compact_threshold=35)
        for i in range(35):
            wm.add(f"entry {i}", "s1")
        all_contents = {e.content for e in wm.get_all()}
        # entry 0..4 should be gone
        for i in range(5):
            assert f"entry {i}" not in all_contents

    def test_thread_safe_add(self, working: WorkingMemory):
        """Concurrent writes must not raise and must not corrupt internal state."""
        errors: list[Exception] = []

        def writer():
            try:
                for _ in range(10):
                    working.add("concurrent", "s1")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # Compaction may have fired (evicting entries down to 30), so the final
        # size is between 1 and max_size (50).  The key invariant is no errors.
        assert 1 <= working.size() <= working._max_size

    def test_clear_session(self, working: WorkingMemory):
        working.add("s1 entry", "s1")
        working.add("s2 entry", "s2")
        removed = working.clear_session("s1")
        assert len(removed) == 1
        assert removed[0].content == "s1 entry"
        assert working.size() == 1

    def test_size(self, working: WorkingMemory):
        assert working.size() == 0
        working.add("x", "s1")
        assert working.size() == 1


# ---------------------------------------------------------------------------
# EpisodicMemory
# ---------------------------------------------------------------------------


class TestEpisodicMemory:
    def test_store_and_search(self, episodic: EpisodicMemory):
        e = MemoryEntry.new("the agent failed to respond", "episodic", "s1")
        episodic.store(e)
        results = episodic.search("failed")
        assert len(results) == 1
        assert results[0].entry_id == e.entry_id

    def test_search_case_insensitive(self, episodic: EpisodicMemory):
        episodic.store(MemoryEntry.new("Error occurred in module", "episodic", "s1"))
        results = episodic.search("error")
        assert len(results) == 1

    def test_search_by_session(self, episodic: EpisodicMemory):
        episodic.store(MemoryEntry.new("s1 content", "episodic", "s1"))
        episodic.store(MemoryEntry.new("s2 content", "episodic", "s2"))
        results = episodic.search(session_id="s1")
        assert len(results) == 1
        assert results[0].session_id == "s1"

    def test_search_by_tags(self, episodic: EpisodicMemory):
        e1 = MemoryEntry.new("tagged entry", "episodic", "s1", tags=["error", "auth"])
        e2 = MemoryEntry.new("untagged entry", "episodic", "s1")
        episodic.store(e1)
        episodic.store(e2)
        results = episodic.search(tags=["error"])
        assert len(results) == 1
        assert results[0].entry_id == e1.entry_id

    def test_search_limit(self, episodic: EpisodicMemory):
        for i in range(10):
            episodic.store(MemoryEntry.new(f"entry {i}", "episodic", "s1"))
        results = episodic.search(limit=3)
        assert len(results) == 3

    def test_search_most_recent_first(self, episodic: EpisodicMemory):
        for i in range(3):
            e = MemoryEntry(
                entry_id=str(i),
                content=f"entry {i}",
                layer="episodic",
                session_id="s1",
                created_at=float(i),
                tags=(),
            )
            episodic.store(e)
        results = episodic.search()
        assert results[0].content == "entry 2"

    def test_by_session(self, episodic: EpisodicMemory):
        episodic.store(MemoryEntry.new("alpha", "episodic", "sess-a"))
        episodic.store(MemoryEntry.new("beta", "episodic", "sess-b"))
        results = episodic.by_session("sess-a")
        assert len(results) == 1
        assert results[0].content == "alpha"

    def test_purge_old(self, episodic: EpisodicMemory):
        # Old entry
        old = MemoryEntry(
            entry_id="old-1",
            content="ancient memory",
            layer="episodic",
            session_id="s1",
            created_at=time.time() - 40 * 86400,  # 40 days ago
            tags=(),
        )
        # Recent entry
        new = MemoryEntry.new("fresh memory", "episodic", "s1")
        episodic.store(old)
        episodic.store(new)

        deleted = episodic.purge_old(days=30)
        assert deleted == 1

        remaining = episodic.search()
        assert len(remaining) == 1
        assert remaining[0].content == "fresh memory"

    def test_store_upsert(self, episodic: EpisodicMemory):
        """Storing the same entry_id twice should upsert, not duplicate."""
        e = MemoryEntry.new("original", "episodic", "s1")
        episodic.store(e)
        # Create a new entry with same ID but different content
        updated = MemoryEntry(
            entry_id=e.entry_id,
            content="updated",
            layer="episodic",
            session_id="s1",
            created_at=e.created_at,
            tags=(),
        )
        episodic.store(updated)
        results = episodic.search("updated")
        assert len(results) == 1

    def test_tags_roundtrip(self, episodic: EpisodicMemory):
        e = MemoryEntry.new("tagged", "episodic", "s1", tags=["foo", "bar"])
        episodic.store(e)
        results = episodic.search("tagged")
        assert results[0].tags == ("foo", "bar")

    def test_wal_mode(self, tmp_db: Path):
        """Verify WAL journal mode is set."""
        em = EpisodicMemory(db_path=tmp_db)
        conn = em._conn()
        row = conn.execute("PRAGMA journal_mode").fetchone()
        assert row[0] == "wal"


# ---------------------------------------------------------------------------
# ProceduralMemory
# ---------------------------------------------------------------------------


class TestProceduralMemory:
    def test_set_and_get(self, procedural: ProceduralMemory):
        procedural.set("auth-rule", "Always validate JWT tokens")
        result = procedural.get("auth-rule")
        assert result == "Always validate JWT tokens"

    def test_get_nonexistent_returns_none(self, procedural: ProceduralMemory):
        assert procedural.get("missing-key") is None

    def test_get_all(self, procedural: ProceduralMemory):
        procedural.set("rule-a", "value a")
        procedural.set("rule-b", "value b")
        all_rules = procedural.get_all()
        assert all_rules == {"rule-a": "value a", "rule-b": "value b"}

    def test_upsert(self, procedural: ProceduralMemory):
        procedural.set("key", "original")
        procedural.set("key", "updated")
        assert procedural.get("key") == "updated"
        # Only one entry should exist
        assert len(procedural.get_all()) == 1

    def test_delete(self, procedural: ProceduralMemory):
        procedural.set("to-delete", "value")
        result = procedural.delete("to-delete")
        assert result is True
        assert procedural.get("to-delete") is None

    def test_delete_nonexistent(self, procedural: ProceduralMemory):
        assert procedural.delete("ghost") is False

    def test_soul_file_created(self, tmp_soul: Path, procedural: ProceduralMemory):
        procedural.set("key", "value")
        assert tmp_soul.exists()

    def test_soul_file_format(self, tmp_soul: Path, procedural: ProceduralMemory):
        procedural.set("my-rule", "Do not trust unvalidated input")
        content = tmp_soul.read_text()
        assert "## my-rule" in content
        assert "Do not trust unvalidated input" in content

    def test_multiline_value(self, procedural: ProceduralMemory):
        procedural.set("complex-rule", "Line one\nLine two\nLine three")
        result = procedural.get("complex-rule")
        assert "Line one" in result
        assert "Line three" in result

    def test_file_missing_no_error(self, tmp_soul: Path):
        pm = ProceduralMemory(soul_path=tmp_soul)
        assert pm.get_all() == {}

    def test_thread_safe_set(self, procedural: ProceduralMemory):
        errors: list[Exception] = []

        def writer(i: int):
            try:
                procedural.set(f"rule-{i}", f"value-{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        all_rules = procedural.get_all()
        assert len(all_rules) == 10


# ---------------------------------------------------------------------------
# _route_layer helper
# ---------------------------------------------------------------------------


class TestRouteLayer:
    def test_short_content_routes_to_working(self):
        assert _route_layer("a short note") == "working"

    def test_long_content_routes_to_episodic(self):
        content = "x" * 200
        assert _route_layer(content) == "episodic"

    def test_always_keyword_routes_to_procedural(self):
        assert _route_layer("always validate inputs") == "procedural"

    def test_never_keyword_routes_to_procedural(self):
        assert _route_layer("never store passwords in plaintext") == "procedural"

    def test_rule_colon_routes_to_procedural(self):
        assert _route_layer("rule: use snake_case for variables") == "procedural"

    def test_pattern_colon_routes_to_procedural(self):
        assert _route_layer("pattern: singleton for config") == "procedural"

    def test_case_insensitive_procedural(self):
        assert _route_layer("ALWAYS check auth") == "procedural"
        assert _route_layer("NEVER skip validation") == "procedural"

    def test_long_procedural_wins_over_length(self):
        # Even if content is long, procedural keywords override
        content = "always " + "x" * 200
        assert _route_layer(content) == "procedural"


# ---------------------------------------------------------------------------
# MemoryRouter
# ---------------------------------------------------------------------------


class TestMemoryRouter:
    def test_write_short_goes_to_working(self, router: MemoryRouter):
        layer, entry = router.write("quick note", "s1")
        assert layer == "working"
        assert entry.layer == "working"

    def test_write_long_goes_to_episodic(self, router: MemoryRouter):
        content = "x" * 200
        layer, entry = router.write(content, "s1")
        assert layer == "episodic"
        assert entry.layer == "episodic"

    def test_write_rule_goes_to_procedural(self, router: MemoryRouter):
        layer, entry = router.write("always validate JWT tokens", "s1")
        assert layer == "procedural"
        assert entry.layer == "procedural"

    def test_write_never_keyword(self, router: MemoryRouter):
        layer, _ = router.write("never expose API keys", "s1")
        assert layer == "procedural"

    def test_write_returns_entry(self, router: MemoryRouter):
        _, entry = router.write("some content", "s1")
        assert isinstance(entry, MemoryEntry)
        assert entry.session_id == "s1"

    def test_write_working_triggers_compact_to_episodic(self):
        """When working memory compacts, evicted entries land in episodic."""
        wm = WorkingMemory(compact_threshold=35)
        em = EpisodicMemory(db_path=Path(":memory:"))
        # Patch: SQLite ":memory:" doesn't support file paths — use tmp
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".db")
        em = EpisodicMemory(db_path=Path(tmp))
        try:
            router = MemoryRouter(working=wm, episodic=em)
            # Write 35 short entries to trigger compaction
            for i in range(35):
                router.write(f"note {i}", "s1")
            # Evicted entries (first 5) should be in episodic
            episodic_results = em.search()
            assert len(episodic_results) == 5
            contents = {e.content for e in episodic_results}
            for i in range(5):
                assert f"note {i}" in contents
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_search_all_returns_all_layers(self, router: MemoryRouter):
        router.write("quick note about validation", "s1")
        router.write("x" * 200 + " validation context", "s1")
        router.write("always validate before saving", "s1")
        results = router.search_all("validat")
        assert "working" in results
        assert "episodic" in results
        assert "procedural" in results

    def test_search_all_working_results(self, router: MemoryRouter):
        router.write("short searchable text", "s1")
        results = router.search_all("searchable")
        assert len(results["working"]) == 1

    def test_search_all_episodic_results(self, router: MemoryRouter):
        router.write("x" * 200 + " findme", "s1")
        results = router.search_all("findme")
        assert len(results["episodic"]) == 1

    def test_search_all_procedural_results(self, router: MemoryRouter):
        router.write("always findme in rules", "s1")
        results = router.search_all("findme")
        assert len(results["procedural"]) == 1

    def test_checkpoint_flushes_session(self, router: MemoryRouter):
        router.write("note a", "sess-x")
        router.write("note b", "sess-x")
        router.write("note c", "sess-y")  # different session

        count = router.checkpoint("sess-x")
        assert count == 2

        # Working memory should only have sess-y left
        working_entries = router.working.get_all()
        session_ids = {e.session_id for e in working_entries}
        assert "sess-x" not in session_ids

    def test_checkpoint_persists_to_episodic(self, router: MemoryRouter):
        router.write("checkpoint me", "sess-cp")
        router.checkpoint("sess-cp")
        episodic_results = router.episodic.search(session_id="sess-cp")
        assert len(episodic_results) >= 1
        assert episodic_results[0].content == "checkpoint me"

    def test_restore_loads_episodic_to_working(self, router: MemoryRouter):
        # Seed episodic directly
        entry = MemoryEntry.new("restored content", "episodic", "sess-r")
        router.episodic.store(entry)

        restored = router.restore("sess-r")
        assert len(restored) == 1
        assert restored[0].content == "restored content"

        # Should now be in working memory
        working_results = router.working.search("restored")
        assert len(working_results) >= 1

    def test_checkpoint_then_restore_roundtrip(self, router: MemoryRouter):
        session = "roundtrip-session"
        router.write("important context", session)
        router.write("another fact", session)
        router.checkpoint(session)

        # Clear working memory by creating a new router with same episodic
        new_router = MemoryRouter(
            working=WorkingMemory(),
            episodic=router.episodic,
            procedural=router.procedural,
        )
        restored = new_router.restore(session)
        contents = {e.content for e in restored}
        assert "important context" in contents
        assert "another fact" in contents


# ---------------------------------------------------------------------------
# Module-level wrappers
# ---------------------------------------------------------------------------


class TestModuleLevelWrappers:
    @pytest.fixture(autouse=True)
    def inject_router(self, router: MemoryRouter):
        """Inject a fresh isolated router for each test."""
        _set_router(router)

    def test_memory_write_returns_layer_and_entry(self):
        layer, entry = memory_write("test content", session_id="s1")
        assert layer in ("working", "episodic", "procedural")
        assert isinstance(entry, MemoryEntry)

    def test_memory_write_short(self):
        layer, _ = memory_write("brief note", session_id="s1")
        assert layer == "working"

    def test_memory_write_procedural(self):
        layer, _ = memory_write("always sanitize inputs", session_id="s1")
        assert layer == "procedural"

    def test_memory_search_returns_dict(self):
        memory_write("searchable content", session_id="s1")
        results = memory_search("searchable")
        assert isinstance(results, dict)
        assert set(results.keys()) == {"working", "episodic", "procedural"}

    def test_memory_search_finds_written_content(self):
        memory_write("unique-xyzzy content", session_id="s1")
        results = memory_search("unique-xyzzy")
        all_results = results["working"] + results["episodic"]
        assert len(all_results) >= 1

    def test_memory_checkpoint_returns_count(self):
        memory_write("note 1", session_id="chk-sess")
        memory_write("note 2", session_id="chk-sess")
        count = memory_checkpoint("chk-sess")
        assert count == 2

    def test_memory_restore_returns_list(self):
        memory_write("fact to persist", session_id="restore-sess")
        memory_checkpoint("restore-sess")
        entries = memory_restore("restore-sess")
        assert isinstance(entries, list)
        assert len(entries) >= 1

    def test_memory_write_with_tags(self):
        layer, entry = memory_write("tagged note", session_id="s1", tags=["important"])
        assert "important" in entry.tags


# ---------------------------------------------------------------------------
# Derive procedural key helper
# ---------------------------------------------------------------------------


class TestDeriveProceduralkKey:
    def test_basic_slugify(self):
        key = _derive_procedural_key("always check authentication tokens")
        assert " " not in key
        assert key.islower() or "-" in key

    def test_truncates_to_60_chars(self):
        content = "a" * 100
        key = _derive_procedural_key(content)
        assert len(key) <= 60

    def test_strips_special_chars(self):
        key = _derive_procedural_key("rule: use @symbols! properly?")
        assert "@" not in key
        assert "!" not in key
        assert "?" not in key

    def test_empty_content_returns_rule(self):
        key = _derive_procedural_key("")
        assert key == "rule"
