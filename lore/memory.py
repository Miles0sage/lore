"""Three-layer memory stack for Lore agents.

Layers:
  working    — in-process buffer (fast, ephemeral, thread-safe)
  episodic   — SQLite-backed long-term store (persistent, queryable)
  procedural — SOUL.md file-backed rules store (structured key/value)

Usage (module-level wrappers)::

    from lore.memory import memory_write, memory_search, memory_checkpoint, memory_restore

    layer, entry = memory_write("always validate user input", session_id="s1")
    results = memory_search("validate")
    memory_checkpoint("s1")
    entries = memory_restore("s1")
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lore.config import get_memory_db_path, get_soul_path

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MemoryEntry — frozen dataclass (immutable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryEntry:
    """A single memory entry across any layer.

    Args:
        entry_id:   Unique identifier (uuid4 string).
        content:    The memory content.
        layer:      One of "working", "episodic", "procedural".
        session_id: Session that created this entry.
        created_at: Unix timestamp (float).
        tags:       Optional tuple of string tags.
    """

    entry_id: str
    content: str
    layer: str
    session_id: str
    created_at: float
    tags: tuple[str, ...] = field(default_factory=tuple)

    @staticmethod
    def new(
        content: str,
        layer: str,
        session_id: str,
        tags: tuple[str, ...] | list[str] = (),
    ) -> "MemoryEntry":
        """Factory — creates a new entry with a fresh UUID and current timestamp."""
        return MemoryEntry(
            entry_id=str(uuid.uuid4()),
            content=content,
            layer=layer,
            session_id=session_id,
            created_at=time.time(),
            tags=tuple(tags),
        )


# ---------------------------------------------------------------------------
# WorkingMemory — in-process ring buffer
# ---------------------------------------------------------------------------

_COMPACT_TARGET = 30  # entries to keep after compaction


class WorkingMemory:
    """Fast in-process buffer with automatic compaction.

    When the number of entries reaches *compact_threshold*, the oldest
    ``len - _COMPACT_TARGET`` entries are evicted and returned to the caller
    for persistence to EpisodicMemory.

    Args:
        max_size:          Hard cap (default 50).
        compact_threshold: Trigger compaction when len >= this (default 40).
    """

    def __init__(self, max_size: int = 50, compact_threshold: int = 40) -> None:
        self._max_size = max_size
        self._compact_threshold = compact_threshold
        self._entries: list[MemoryEntry] = []
        self._lock = threading.Lock()

    # -- Public API ----------------------------------------------------------

    def add(
        self,
        content: str,
        session_id: str,
        tags: tuple[str, ...] | list[str] = (),
    ) -> tuple[MemoryEntry, list[MemoryEntry]]:
        """Add an entry to working memory.

        Returns:
            ``(entry, evicted)`` where *evicted* is a (possibly empty) list
            of entries removed during compaction that the caller should
            persist to episodic memory.
        """
        entry = MemoryEntry.new(content, "working", session_id, tags)
        evicted: list[MemoryEntry] = []

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) >= self._compact_threshold:
                evicted = self._compact_locked()

        return entry, evicted

    def get_all(self) -> list[MemoryEntry]:
        """Return all entries, most recent first."""
        with self._lock:
            return list(reversed(self._entries))

    def search(self, query: str) -> list[MemoryEntry]:
        """Simple case-insensitive substring match on content."""
        q = query.lower()
        with self._lock:
            return [e for e in reversed(self._entries) if q in e.content.lower()]

    def remove(self, entry_ids: list[str]) -> None:
        """Remove entries by ID (used after persisting evicted entries)."""
        id_set = set(entry_ids)
        with self._lock:
            self._entries = [e for e in self._entries if e.entry_id not in id_set]

    def clear_session(self, session_id: str) -> list[MemoryEntry]:
        """Remove and return all entries for a session."""
        with self._lock:
            kept: list[MemoryEntry] = []
            removed: list[MemoryEntry] = []
            for e in self._entries:
                if e.session_id == session_id:
                    removed.append(e)
                else:
                    kept.append(e)
            self._entries = kept
        return removed

    def size(self) -> int:
        with self._lock:
            return len(self._entries)

    # -- Internal ------------------------------------------------------------

    def _compact_locked(self) -> list[MemoryEntry]:
        """Evict oldest entries down to _COMPACT_TARGET. Called under lock."""
        n = len(self._entries)
        evict_count = n - _COMPACT_TARGET
        if evict_count <= 0:
            return []
        evicted = self._entries[:evict_count]
        self._entries = self._entries[evict_count:]
        return evicted


# ---------------------------------------------------------------------------
# EpisodicMemory — SQLite-backed long-term store
# ---------------------------------------------------------------------------

_EPISODIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    entry_id   TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    layer      TEXT NOT NULL DEFAULT 'episodic',
    session_id TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL DEFAULT 0,
    tags       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_episodic_session ON episodic_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_episodic_created ON episodic_memory(created_at);
"""


class EpisodicMemory:
    """Persistent SQLite-backed store for long-term episodic memories.

    Uses WAL mode and thread-local connections for safety.

    Args:
        db_path: Path to the SQLite database. Defaults to
                 ``config.get_memory_db_path()``.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = get_memory_db_path()
        self._db_path = db_path
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
        conn.executescript(_EPISODIC_SCHEMA)
        conn.commit()

    # -- Public API ----------------------------------------------------------

    def store(self, entry: MemoryEntry) -> None:
        """Persist a MemoryEntry (upsert by entry_id)."""
        tags_str = ",".join(entry.tags)
        conn = self._conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO episodic_memory
                (entry_id, content, layer, session_id, created_at, tags)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entry.entry_id,
                entry.content,
                entry.layer,
                entry.session_id,
                entry.created_at,
                tags_str,
            ),
        )
        conn.commit()

    def search(
        self,
        query: str = "",
        session_id: str = "",
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Search episodic memory with optional filters.

        Args:
            query:      Substring match against content (case-insensitive).
            session_id: Filter by session.
            tags:       ALL listed tags must be present.
            limit:      Maximum number of results (most recent first).
        """
        if tags is None:
            tags = []

        conn = self._conn()
        sql = "SELECT * FROM episodic_memory WHERE 1=1"
        params: list[Any] = []

        if query:
            sql += " AND LOWER(content) LIKE ?"
            params.append(f"%{query.lower()}%")

        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        results = [self._row_to_entry(r) for r in rows]

        # Tag filtering (post-query — tags stored as CSV)
        if tags:
            results = [
                e for e in results if all(t in e.tags for t in tags)
            ]

        return results

    def by_session(self, session_id: str) -> list[MemoryEntry]:
        """Return all entries for a session, most recent first."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM episodic_memory WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def purge_old(self, days: int = 30) -> int:
        """Delete entries older than *days* days. Returns count deleted."""
        cutoff = time.time() - days * 86400
        conn = self._conn()
        cursor = conn.execute(
            "DELETE FROM episodic_memory WHERE created_at < ?", (cutoff,)
        )
        conn.commit()
        return cursor.rowcount

    # -- Internal ------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
        tags_raw: str = row["tags"] or ""
        tags = tuple(t for t in tags_raw.split(",") if t)
        return MemoryEntry(
            entry_id=row["entry_id"],
            content=row["content"],
            layer=row["layer"],
            session_id=row["session_id"],
            created_at=row["created_at"],
            tags=tags,
        )


# ---------------------------------------------------------------------------
# ProceduralMemory — SOUL.md file-backed rules store
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)


class ProceduralMemory:
    """Key/value rules store backed by a SOUL.md markdown file.

    Format::

        ## key
        value

        ## another-key
        another value

    Thread-safe via a module-level Lock.  The file is read/written on every
    operation to support multi-process access (no in-process cache).

    Args:
        soul_path: Path to SOUL.md. Defaults to ``config.get_soul_path()``.
    """

    def __init__(self, soul_path: Path | None = None) -> None:
        if soul_path is None:
            soul_path = get_soul_path()
        self._path = soul_path
        self._lock = threading.Lock()

    # -- Public API ----------------------------------------------------------

    def get(self, key: str) -> str | None:
        """Return the value for *key*, or None if not found."""
        sections = self._read_sections()
        return sections.get(key)

    def set(self, key: str, value: str) -> None:
        """Upsert a key/value section in SOUL.md."""
        with self._lock:
            sections = self._read_sections()
            sections[key] = value
            self._write_sections(sections)

    def get_all(self) -> dict[str, str]:
        """Return all key/value pairs."""
        return self._read_sections()

    def delete(self, key: str) -> bool:
        """Remove a section. Returns True if it existed."""
        with self._lock:
            sections = self._read_sections()
            if key not in sections:
                return False
            del sections[key]
            self._write_sections(sections)
        return True

    # -- Internal ------------------------------------------------------------

    def _read_sections(self) -> dict[str, str]:
        """Parse SOUL.md into a dict of {key: value}."""
        if not self._path.exists():
            return {}

        text = self._path.read_text(encoding="utf-8")
        sections: dict[str, str] = {}
        matches = list(_SECTION_RE.finditer(text))

        for i, m in enumerate(matches):
            key = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            value = text[start:end].strip()
            sections[key] = value

        return sections

    def _write_sections(self, sections: dict[str, str]) -> None:
        """Serialize sections back to SOUL.md, preserving insertion order."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for key, value in sections.items():
            lines.append(f"## {key}\n{value}\n\n")
        self._path.write_text("".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# MemoryRouter — auto-routes writes to the correct layer
# ---------------------------------------------------------------------------

_PROCEDURAL_KEYWORDS = frozenset(["always", "never", "rule:", "pattern:"])


def _is_procedural(content: str) -> bool:
    """Return True if content looks like a procedural rule."""
    lower = content.lower()
    return any(kw in lower for kw in _PROCEDURAL_KEYWORDS)


def _route_layer(content: str) -> str:
    """Determine which layer to write to based on content heuristics."""
    if _is_procedural(content):
        return "procedural"
    if len(content) < 200:
        return "working"
    return "episodic"


class MemoryRouter:
    """Auto-routes memory writes to the correct layer.

    Routing rules (applied in order):
    1. Contains "always", "never", "rule:", or "pattern:" → procedural
    2. content length < 200 AND no rule keywords → working
    3. All other content → episodic

    Args:
        working:    WorkingMemory instance (created if None).
        episodic:   EpisodicMemory instance (created if None).
        procedural: ProceduralMemory instance (created if None).
    """

    def __init__(
        self,
        working: WorkingMemory | None = None,
        episodic: EpisodicMemory | None = None,
        procedural: ProceduralMemory | None = None,
    ) -> None:
        self.working = working or WorkingMemory()
        self.episodic = episodic or EpisodicMemory()
        self.procedural = procedural or ProceduralMemory()

    # -- Public API ----------------------------------------------------------

    def write(
        self,
        content: str,
        session_id: str,
        tags: tuple[str, ...] | list[str] = (),
    ) -> tuple[str, MemoryEntry]:
        """Write *content* to the appropriate layer.

        Returns:
            ``(layer_name, entry)``
        """
        layer = _route_layer(content)

        if layer == "procedural":
            # Procedural entries use a generated key from content
            key = _derive_procedural_key(content)
            self.procedural.set(key, content)
            entry = MemoryEntry.new(content, "procedural", session_id, tags)
            return "procedural", entry

        if layer == "working":
            entry, evicted = self.working.add(content, session_id, tags)
            # Auto-persist evicted entries to episodic
            for e in evicted:
                self.episodic.store(
                    MemoryEntry(
                        entry_id=e.entry_id,
                        content=e.content,
                        layer="episodic",
                        session_id=e.session_id,
                        created_at=e.created_at,
                        tags=e.tags,
                    )
                )
            return "working", entry

        # episodic
        entry = MemoryEntry.new(content, "episodic", session_id, tags)
        self.episodic.store(entry)
        return "episodic", entry

    def search_all(self, query: str) -> dict[str, list[Any]]:
        """Search all three layers and return results keyed by layer name."""
        working_results = self.working.search(query)
        episodic_results = self.episodic.search(query)

        # Procedural: search key + value
        proc_all = self.procedural.get_all()
        q = query.lower()
        proc_results: list[dict[str, str]] = [
            {"key": k, "value": v}
            for k, v in proc_all.items()
            if q in k.lower() or q in v.lower()
        ]

        return {
            "working": working_results,
            "episodic": episodic_results,
            "procedural": proc_results,
        }

    def checkpoint(self, session_id: str) -> int:
        """Evict all working memory for *session_id* to episodic.

        Returns the number of entries persisted.
        """
        evicted = self.working.clear_session(session_id)
        for e in evicted:
            self.episodic.store(
                MemoryEntry(
                    entry_id=e.entry_id,
                    content=e.content,
                    layer="episodic",
                    session_id=e.session_id,
                    created_at=e.created_at,
                    tags=e.tags,
                )
            )
        return len(evicted)

    def restore(self, session_id: str, limit: int = 20) -> list[MemoryEntry]:
        """Load recent episodic entries for *session_id* into working memory.

        Returns the list of entries that were loaded.
        """
        entries = self.episodic.search(session_id=session_id, limit=limit)
        for e in entries:
            # Restore as working memory entries (ignore eviction during restore)
            self.working.add(e.content, e.session_id, e.tags)
        return entries


# ---------------------------------------------------------------------------
# Procedural key derivation helper
# ---------------------------------------------------------------------------

_STRIP_RE = re.compile(r"[^\w\s-]")
_WS_RE = re.compile(r"\s+")


def _derive_procedural_key(content: str) -> str:
    """Derive a short slug key from procedural content."""
    # Take first 60 chars, slugify
    snippet = content[:60].lower()
    snippet = _STRIP_RE.sub("", snippet)
    snippet = _WS_RE.sub("-", snippet).strip("-")
    return snippet or "rule"


# ---------------------------------------------------------------------------
# Module-level singleton + wrappers
# ---------------------------------------------------------------------------

_router_lock = threading.Lock()
_router: MemoryRouter | None = None


def _get_router() -> MemoryRouter:
    """Return the process-level singleton MemoryRouter (lazy init)."""
    global _router
    if _router is None:
        with _router_lock:
            if _router is None:
                _router = MemoryRouter()
    return _router


def _set_router(router: MemoryRouter) -> None:
    """Replace the singleton router (for tests / dependency injection)."""
    global _router
    with _router_lock:
        _router = router


def memory_write(
    content: str,
    session_id: str = "default",
    tags: tuple[str, ...] | list[str] = (),
) -> tuple[str, MemoryEntry]:
    """Write *content* to the appropriate memory layer.

    Returns:
        ``(layer_name, entry)``
    """
    return _get_router().write(content, session_id, tags)


def memory_search(query: str) -> dict[str, list[Any]]:
    """Search all three layers for *query*.

    Returns:
        ``{"working": [...], "episodic": [...], "procedural": [...]}``
    """
    return _get_router().search_all(query)


def memory_checkpoint(session_id: str = "default") -> int:
    """Flush working memory for *session_id* to episodic storage.

    Returns:
        Number of entries persisted.
    """
    return _get_router().checkpoint(session_id)


def memory_restore(session_id: str = "default") -> list[MemoryEntry]:
    """Restore recent episodic entries for *session_id* into working memory.

    Returns:
        List of restored MemoryEntry objects.
    """
    return _get_router().restore(session_id)
