# LORE SCAFFOLD: three_layer_memory
"""
Three-Layer Memory — The Stack, Consciousness of the Agent

Episodic + semantic + procedural memory. Without The Stack, every session
is the agent's first day alive.

Layer 1: Working memory (ephemeral, current session)
Layer 2: Episodic memory (what happened before, retrieved by similarity)
Layer 3: Procedural memory (permanent learned behaviors)

Usage:
    stack = MemoryStack()
    stack.add_episodic("User prefers Python over TypeScript", {"topic": "preference"})
    results = stack.search_semantic("language preference")
    stack.update_procedural("always_use_python", "Use Python for all new projects")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryEntry:
    """Immutable memory record."""
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    layer: str = "episodic"  # episodic | semantic | procedural
    relevance: float = 1.0


class MemoryStack:
    """Three-layer memory system for agent continuity."""

    def __init__(self, max_episodic: int = 1000, max_working: int = 50):
        self._working: list[MemoryEntry] = []
        self._episodic: list[MemoryEntry] = []
        self._procedural: dict[str, MemoryEntry] = {}
        self._max_episodic = max_episodic
        self._max_working = max_working

    def add_working(self, content: str, metadata: dict | None = None) -> None:
        """Add to working memory (Layer 1, ephemeral)."""
        entry = MemoryEntry(content=content, metadata=dict(metadata or {}), layer="working")
        self._working = [*self._working, entry][-self._max_working:]

    def add_episodic(self, content: str, metadata: dict | None = None) -> None:
        """Add to episodic memory (Layer 2, persistent across sessions)."""
        entry = MemoryEntry(content=content, metadata=dict(metadata or {}), layer="episodic")
        self._episodic = [*self._episodic, entry][-self._max_episodic:]

    def search_semantic(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search episodic memory by keyword similarity.

        In production, replace with vector similarity search (pgvector, Pinecone, etc.).
        """
        query_lower = query.lower()
        scored = []
        for entry in self._episodic:
            # Simple keyword overlap scoring — replace with embeddings
            words = set(query_lower.split())
            content_words = set(entry.content.lower().split())
            overlap = len(words & content_words)
            if overlap > 0:
                scored.append((overlap / max(len(words), 1), entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def update_procedural(self, key: str, content: str, metadata: dict | None = None) -> None:
        """Update procedural memory (Layer 3, permanent learned behaviors)."""
        self._procedural = {
            **self._procedural,
            key: MemoryEntry(content=content, metadata=dict(metadata or {}), layer="procedural"),
        }

    def get_procedural(self, key: str) -> MemoryEntry | None:
        """Retrieve a procedural memory by key."""
        return self._procedural.get(key)

    def compact(self) -> dict:
        """Compact memory: summarize old episodic entries, clear working memory."""
        stats = {
            "working_cleared": len(self._working),
            "episodic_count": len(self._episodic),
            "procedural_count": len(self._procedural),
        }
        self._working = []
        # Keep only recent half of episodic memory
        if len(self._episodic) > self._max_episodic // 2:
            self._episodic = self._episodic[-(self._max_episodic // 2):]
            stats["episodic_compacted_to"] = len(self._episodic)
        return stats

    def context_window(self) -> list[MemoryEntry]:
        """Build context window: procedural first, then recent episodic, then working."""
        procedural = list(self._procedural.values())
        recent_episodic = self._episodic[-10:]
        return [*procedural, *recent_episodic, *self._working]
