"""Rejection tracker — persists rejected proposals so the quality gate learns from them.

The rejection log is a JSONL file at .lore/rejection_log.jsonl.
DeepSeek reads it during triage to avoid re-proposing already-rejected content.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_telemetry_dir


def _log_path() -> Path:
    return get_telemetry_dir() / "rejection_log.jsonl"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _tokenize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def record_rejection(
    proposal_id: str,
    title: str,
    source: str = "",
    reason: str = "",
    reviewer: str = "",
) -> dict[str, Any]:
    """Append a rejection record to the log."""
    entry = {
        "ts": _utc_now(),
        "proposal_id": proposal_id,
        "title": title,
        "source": source,
        "reason": reason,
        "reviewer": reviewer,
        "tokens": sorted(_tokenize(title)),
    }
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def load_rejections(limit: int = 200) -> list[dict[str, Any]]:
    """Return recent rejection records."""
    path = _log_path()
    if not path.exists():
        return []
    rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    records: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        row = row.strip()
        if not row:
            continue
        try:
            records.append(json.loads(row))
        except json.JSONDecodeError:
            continue
    return records


def is_rejected_topic(title: str, threshold: float = 0.55) -> tuple[bool, str]:
    """Check if a title is too similar to a previously rejected proposal.

    Returns (is_similar, matched_title).
    """
    title_tokens = _tokenize(title)
    if not title_tokens:
        return False, ""

    for record in load_rejections():
        known_tokens = set(record.get("tokens", []))
        if not known_tokens:
            continue
        overlap = len(title_tokens & known_tokens) / len(title_tokens | known_tokens)
        if overlap >= threshold:
            return True, record["title"]

    return False, ""


def rejection_summary(limit: int = 20) -> str:
    """Return a compact rejection log summary for injection into DeepSeek prompts."""
    records = load_rejections(limit=limit)
    if not records:
        return ""
    titles = [r["title"] for r in records[-limit:]]
    return "Previously rejected topics (do not re-propose similar content):\n" + "\n".join(
        f"- {t}" for t in titles
    )
