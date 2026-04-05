#!/usr/bin/env python3
"""
Push recently modified wiki articles into a NotebookLM notebook.

Usage:
    python3 scripts/notebooklm_push.py --notebook-id <ID> [--wiki-dir <path>] [--hours <N>]
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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("notebooklm_push")


class PushResult(NamedTuple):
    path: Path
    success: bool
    message: str


def find_recent_articles(wiki_dir: Path, hours: float = 24.0) -> list[Path]:
    cutoff = time.time() - (hours * 3600)
    articles: list[Path] = []

    if not wiki_dir.is_dir():
        logger.error("Wiki directory not found: %s", wiki_dir)
        return articles

    for md_file in sorted(wiki_dir.glob("*.md")):
        try:
            if md_file.stat().st_mtime >= cutoff:
                articles.append(md_file)
        except OSError as exc:
            logger.warning("Cannot stat %s: %s", md_file, exc)

    logger.info("Found %d article(s) modified in the last %.0f hours", len(articles), hours)
    return articles


def _make_source_title(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def _read_article(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Cannot read %s: %s", path, exc)
        return None


async def _push_via_library(notebook_id: str, articles: list[Path]) -> list[PushResult]:
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
                results.append(PushResult(path=path, success=True, message=f"{source.title} ({source.status})"))
                logger.info("Pushed: %s -> %s", path.name, source.title)
            except Exception as exc:  # noqa: BLE001
                results.append(PushResult(path=path, success=False, message=str(exc)))
                logger.error("Failed to push %s: %s", path.name, exc)
    return results


def push_via_library(notebook_id: str, articles: list[Path]) -> list[PushResult]:
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

    return asyncio.run(_push_via_library(notebook_id, articles))


def push_via_google_mcp(notebook_id: str, articles: list[Path]) -> list[PushResult]:
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
    return results


def push_via_http(notebook_id: str, articles: list[Path]) -> list[PushResult]:
    import json
    import urllib.request

    cookie = os.environ.get("NOTEBOOKLM_COOKIE", "")
    token = os.environ.get("GOOGLE_ACCESS_TOKEN", "")
    if not cookie and not token:
        raise RuntimeError("HTTP fallback requires NOTEBOOKLM_COOKIE or GOOGLE_ACCESS_TOKEN")

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        headers["Cookie"] = cookie

    api_url = f"https://notebooklm.google.com/api/notebook/{notebook_id}/source"
    results: list[PushResult] = []
    for path in articles:
        text = _read_article(path)
        if text is None:
            results.append(PushResult(path=path, success=False, message="read error"))
            continue

        payload = json.dumps(
            {"title": _make_source_title(path), "content": text, "sourceType": "TEXT"}
        ).encode()
        try:
            req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
            results.append(PushResult(path=path, success=True, message=f"HTTP 200: {body[:120]}"))
        except Exception as exc:  # noqa: BLE001
            results.append(PushResult(path=path, success=False, message=str(exc)))
    return results


def push_articles(notebook_id: str, articles: list[Path]) -> list[PushResult]:
    backends = [
        ("notebooklm-py library", push_via_library),
        ("google-mcp module", push_via_google_mcp),
        ("direct HTTP", push_via_http),
    ]

    for name, backend_fn in backends:
        logger.info("Trying backend: %s", name)
        try:
            return backend_fn(notebook_id, articles)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Backend '%s' unavailable: %s", name, exc)

    return [PushResult(path=path, success=False, message="all backends failed") for path in articles]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook-id", required=True)
    parser.add_argument("--wiki-dir", default=str(Path(__file__).resolve().parents[1] / "wiki"))
    parser.add_argument("--hours", type=float, default=24.0)
    args = parser.parse_args()

    articles = find_recent_articles(Path(args.wiki_dir), args.hours)
    if not articles:
        logger.info("No recent articles to push")
        return 0

    results = push_articles(args.notebook_id, articles)
    failures = [result for result in results if not result.success]
    for result in results:
        prefix = "OK" if result.success else "FAIL"
        logger.info("%s %s :: %s", prefix, result.path.name, result.message)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
