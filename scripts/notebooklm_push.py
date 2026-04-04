#!/usr/bin/env python3
"""
notebooklm_push.py — Push recently modified wiki articles to a NotebookLM notebook.

Usage:
    python3 notebooklm_push.py --notebook-id <ID> [--wiki-dir <path>] [--hours <N>]

Behaviour:
- Scans <wiki-dir> for .md files modified within the last <hours> hours (default 24).
- Adds each file as a text source to the specified NotebookLM notebook.
- Uses the notebooklm-py library (same pattern as /root/google-mcp/tools_notebooklm.py).
- Falls back to a direct HTTP approach if the library is unavailable.
- Exits 0 on full success, 1 if any source failed to push.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("notebooklm_push")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------
class PushResult(NamedTuple):
    path: Path
    success: bool
    message: str


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------
def find_recent_articles(wiki_dir: Path, hours: float = 24.0) -> list[Path]:
    """Return .md files under wiki_dir modified within the last `hours` hours."""
    cutoff = time.time() - (hours * 3600)
    articles: list[Path] = []

    if not wiki_dir.is_dir():
        logger.error("Wiki directory not found: %s", wiki_dir)
        return articles

    for md_file in sorted(wiki_dir.glob("*.md")):
        try:
            mtime = md_file.stat().st_mtime
            if mtime >= cutoff:
                articles.append(md_file)
        except OSError as exc:
            logger.warning("Cannot stat %s: %s", md_file, exc)

    logger.info("Found %d article(s) modified in the last %.0f hours", len(articles), hours)
    return articles


def _make_source_title(path: Path) -> str:
    """Derive a human-readable title from the filename."""
    stem = path.stem  # e.g. "circuit-breaker-pattern-for-ai-agents"
    return stem.replace("-", " ").replace("_", " ").title()


def _read_article(path: Path) -> str | None:
    """Read article text, returning None on error."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Cannot read %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Push via notebooklm-py library (primary)
# ---------------------------------------------------------------------------
async def _push_via_library(notebook_id: str, articles: list[Path]) -> list[PushResult]:
    """Push articles using the notebooklm-py async client."""
    try:
        from notebooklm import NotebookLMClient  # type: ignore
    except ImportError as exc:
        raise RuntimeError(f"notebooklm library not available: {exc}") from exc

    results: list[PushResult] = []

    async with await NotebookLMClient.from_storage() as client:
        for path in articles:
            text = _read_article(path)
            if text is None:
                results.append(PushResult(path=path, success=False, message="read error"))
                continue

            title = _make_source_title(path)
            try:
                source = await client.sources.add_text(
                    notebook_id,
                    title=title,
                    content=text,
                )
                results.append(PushResult(
                    path=path,
                    success=True,
                    message=f"added source '{source.title}' (status: {source.status})",
                ))
                logger.info("Pushed: %s -> '%s'", path.name, source.title)
            except Exception as exc:  # noqa: BLE001
                results.append(PushResult(path=path, success=False, message=str(exc)))
                logger.error("Failed to push %s: %s", path.name, exc)

    return results


def push_via_library(notebook_id: str, articles: list[Path]) -> list[PushResult]:
    """Synchronous wrapper around _push_via_library."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        try:
            import nest_asyncio  # type: ignore
            nest_asyncio.apply()
            return asyncio.run(_push_via_library(notebook_id, articles))
        except ImportError:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _push_via_library(notebook_id, articles))
                return future.result(timeout=120)
    else:
        return asyncio.run(_push_via_library(notebook_id, articles))


# ---------------------------------------------------------------------------
# Push via google-mcp module (secondary fallback)
# ---------------------------------------------------------------------------
def push_via_google_mcp(notebook_id: str, articles: list[Path]) -> list[PushResult]:
    """Push using add_text_source from /root/google-mcp/tools_notebooklm.py."""
    google_mcp_path = Path("/root/google-mcp")
    if not google_mcp_path.is_dir():
        raise RuntimeError("google-mcp directory not found")

    if str(google_mcp_path) not in sys.path:
        sys.path.insert(0, str(google_mcp_path))

    from tools_notebooklm import add_text_source  # type: ignore

    results: list[PushResult] = []
    for path in articles:
        text = _read_article(path)
        if text is None:
            results.append(PushResult(path=path, success=False, message="read error"))
            continue

        title = _make_source_title(path)
        response = add_text_source(notebook_id, title=title, text=text)
        success = not response.startswith("Error")
        results.append(PushResult(path=path, success=success, message=response))
        if success:
            logger.info("Pushed (mcp): %s -> '%s'", path.name, title)
        else:
            logger.error("Failed (mcp) %s: %s", path.name, response)

    return results


# ---------------------------------------------------------------------------
# Push via direct HTTP (tertiary fallback)
# ---------------------------------------------------------------------------
def push_via_http(notebook_id: str, articles: list[Path]) -> list[PushResult]:
    """
    Fallback: call the NotebookLM internal API directly.

    Requires NOTEBOOKLM_COOKIE env var (value of the 'Cookie' header from an
    authenticated browser session), or GOOGLE_ACCESS_TOKEN for OAuth.
    This is a best-effort fallback and may break if Google changes their API.
    """
    import json
    import urllib.request

    cookie = os.environ.get("NOTEBOOKLM_COOKIE", "")
    token = os.environ.get("GOOGLE_ACCESS_TOKEN", "")

    if not cookie and not token:
        raise RuntimeError(
            "HTTP fallback requires NOTEBOOKLM_COOKIE or GOOGLE_ACCESS_TOKEN env var"
        )

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif cookie:
        headers["Cookie"] = cookie

    # NotebookLM internal API endpoint for adding text sources
    api_url = (
        f"https://notebooklm.google.com/api/notebook/{notebook_id}/source"
    )

    results: list[PushResult] = []
    for path in articles:
        text = _read_article(path)
        if text is None:
            results.append(PushResult(path=path, success=False, message="read error"))
            continue

        title = _make_source_title(path)
        payload = json.dumps({"title": title, "content": text, "sourceType": "TEXT"}).encode()

        try:
            req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
                results.append(PushResult(path=path, success=True, message=f"HTTP 200: {body[:120]}"))
                logger.info("Pushed (http): %s", path.name)
        except Exception as exc:  # noqa: BLE001
            results.append(PushResult(path=path, success=False, message=str(exc)))
            logger.error("Failed (http) %s: %s", path.name, exc)

    return results


# ---------------------------------------------------------------------------
# Orchestrator — try each backend in order
# ---------------------------------------------------------------------------
def push_articles(notebook_id: str, articles: list[Path]) -> list[PushResult]:
    """Try library -> google-mcp -> HTTP, returning the first that works."""
    backends = [
        ("notebooklm-py library", push_via_library),
        ("google-mcp module",     push_via_google_mcp),
        ("direct HTTP",           push_via_http),
    ]

    for name, backend_fn in backends:
        logger.info("Trying backend: %s", name)
        try:
            results = backend_fn(notebook_id, articles)
            logger.info("Backend '%s' succeeded", name)
            return results
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backend '%s' unavailable: %s", name, exc)

    # All backends failed — return failures for all articles
    logger.error("All NotebookLM backends failed")
    return [
        PushResult(path=p, success=False, message="all backends failed")
        for p in articles
    ]


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Push recently modified wiki articles to NotebookLM."
    )
    parser.add_argument(
        "--notebook-id",
        required=True,
        help="NotebookLM notebook ID (UUID)",
    )
    parser.add_argument(
        "--wiki-dir",
        default="/root/wikis/ai-agents/wiki",
        help="Path to wiki article directory (default: /root/wikis/ai-agents/wiki)",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=24.0,
        help="Look back this many hours for modified files (default: 24)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    wiki_dir = Path(args.wiki_dir)
    notebook_id: str = args.notebook_id
    hours: float = args.hours

    logger.info("notebooklm_push starting")
    logger.info("  notebook_id : %s", notebook_id)
    logger.info("  wiki_dir    : %s", wiki_dir)
    logger.info("  lookback    : %.0f hours", hours)

    articles = find_recent_articles(wiki_dir, hours=hours)

    if not articles:
        logger.info("No articles to push — nothing to do.")
        return 0

    results = push_articles(notebook_id, articles)

    # Report
    succeeded = [r for r in results if r.success]
    failed    = [r for r in results if not r.success]

    logger.info("Push complete: %d succeeded, %d failed", len(succeeded), len(failed))

    for r in succeeded:
        logger.info("  OK  %s — %s", r.path.name, r.message)

    for r in failed:
        logger.error("  ERR %s — %s", r.path.name, r.message)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
