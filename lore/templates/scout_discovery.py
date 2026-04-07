# LORE SCAFFOLD: scout_discovery
"""
Scout Discovery — The Scout, Autonomous Research Agent

Parallel source discovery. The Scout fires multiple research sources
concurrently, collects results, merges them, and resolves conflicts.

Usage:
    scout = ScoutCoordinator()
    scout.register_source("web", web_search_fn)
    scout.register_source("arxiv", arxiv_search_fn)
    results = await scout.discover("circuit breaker patterns in distributed systems")
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class SearchSource(Protocol):
    """Protocol for search sources."""
    def search(self, query: str, limit: int) -> list[dict]: ...


@dataclass(frozen=True)
class DiscoveryResult:
    """Immutable result from a single source."""
    source: str
    query: str
    results: tuple[dict, ...]
    duration_seconds: float
    success: bool
    error: str = ""


@dataclass(frozen=True)
class MergedDiscovery:
    """Immutable merged results from all sources."""
    query: str
    sources_queried: tuple[str, ...]
    total_results: int
    results: tuple[dict, ...]
    duration_seconds: float


class ScoutCoordinator:
    """Coordinates parallel discovery across multiple sources."""

    def __init__(self, max_workers: int = 5, timeout_seconds: float = 30.0):
        self._sources: dict[str, Callable[[str, int], list[dict]]] = {}
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds

    def register_source(self, name: str, search_fn: Callable[[str, int], list[dict]]) -> None:
        """Register a search source."""
        self._sources = {**self._sources, name: search_fn}

    def _search_one(self, name: str, fn: Callable, query: str, limit: int) -> DiscoveryResult:
        """Execute a single source search with error handling."""
        start = time.monotonic()
        try:
            results = fn(query, limit)
            return DiscoveryResult(
                source=name, query=query, results=tuple(results),
                duration_seconds=time.monotonic() - start, success=True,
            )
        except Exception as e:
            return DiscoveryResult(
                source=name, query=query, results=(),
                duration_seconds=time.monotonic() - start, success=False, error=str(e),
            )

    async def discover(self, query: str, limit_per_source: int = 10) -> MergedDiscovery:
        """Run all sources in parallel and merge results."""
        start = time.monotonic()
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            tasks = [
                loop.run_in_executor(pool, self._search_one, name, fn, query, limit_per_source)
                for name, fn in self._sources.items()
            ]
            source_results: list[DiscoveryResult] = await asyncio.gather(*tasks)

        # Merge and deduplicate results
        all_results: list[dict] = []
        seen_keys: set[str] = set()
        for sr in source_results:
            if sr.success:
                for item in sr.results:
                    key = str(item.get("id", item.get("title", item.get("url", id(item)))))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_results.append({**item, "_source": sr.source})

        return MergedDiscovery(
            query=query,
            sources_queried=tuple(self._sources.keys()),
            total_results=len(all_results),
            results=tuple(all_results),
            duration_seconds=time.monotonic() - start,
        )
