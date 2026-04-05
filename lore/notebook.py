"""NotebookLM-oriented helper utilities for Lore.

This module stays pure-Python and intentionally does not depend on the
NotebookLM client. It prepares summaries, sync briefs, and follow-up prompts
for approved canon changes so higher-level scripts can push them into a
private notebook later.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import re

from . import evolution, proposals, routing


@dataclass(frozen=True)
class SyncCandidate:
    """A single item that could be pushed into NotebookLM."""

    kind: str
    title: str
    status: str
    priority: float
    summary: str
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "summary": self.summary,
            "path": self.path,
        }


def _truncate(value: str, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalise_status(value: object, default: str = "") -> str:
    text = str(value or default).strip()
    return text or default


def _proposal_to_candidate(item: Mapping[str, object]) -> SyncCandidate:
    title = str(item.get("title", item.get("id", "Untitled Proposal")))
    summary = item.get("review_notes") or item.get("content") or item.get("publish_recommendation") or ""
    return SyncCandidate(
        kind=str(item.get("proposal_type", "proposal")),
        title=title,
        status=_normalise_status(item.get("status"), "proposed"),
        priority=_as_float(item.get("priority_score"), 0.0),
        summary=_truncate(str(summary), 160),
        path=str(item.get("path", "")),
    )


def _article_to_candidate(item: Mapping[str, object], status: str = "published") -> SyncCandidate:
    title = str(item.get("title", item.get("id", "Untitled Article")))
    summary = item.get("summary") or item.get("snippet") or item.get("content") or ""
    priority = _as_float(item.get("priority_score"), 0.5)
    if not priority:
        priority = 0.5
    return SyncCandidate(
        kind="canon",
        title=title,
        status=status,
        priority=priority,
        summary=_truncate(str(summary), 160),
        path=str(item.get("path", "")),
    )


def collect_sync_candidates(
    *,
    proposal_queue: Sequence[Mapping[str, object]] | None = None,
    approved_articles: Sequence[Mapping[str, object]] | None = None,
    report: Mapping[str, object] | None = None,
) -> dict:
    """Collect NotebookLM sync candidates from proposals and approved canon changes.

    The result is designed to be stable input for a push script or briefing
    generator.
    """
    proposals_list = list(proposal_queue or [])
    articles_list = list(approved_articles or [])
    if report is None:
        report = evolution.build_evolution_report()

    candidates: list[SyncCandidate] = []
    for proposal in proposals_list:
        if _normalise_status(proposal.get("status"), "") in {"approved", "published", "merged"}:
            candidates.append(_proposal_to_candidate(proposal))

    for article in articles_list:
        candidates.append(_article_to_candidate(article))

    proposal_summary = {
        "count": len(proposals_list),
        "active_count": sum(
            1 for item in proposals_list if _normalise_status(item.get("status"), "") in {"proposed", "in_review", "approved"}
        ),
        "approved_count": sum(1 for item in proposals_list if _normalise_status(item.get("status"), "") == "approved"),
        "top_priority": max((_as_float(item.get("priority_score"), 0.0) for item in proposals_list), default=0.0),
    }

    return {
        "workspace_root": report.get("workspace_root", ""),
        "article_count": report.get("article_count", 0),
        "raw_count": report.get("raw_count", 0),
        "duplicate_titles": list(report.get("duplicate_titles", [])),
        "uncovered_archetypes": list(report.get("uncovered_archetypes", [])),
        "proposal_summary": proposal_summary,
        "candidates": [candidate.to_dict() for candidate in candidates],
    }


def summarize_sync_candidates(sync_state: Mapping[str, object]) -> str:
    """Render sync candidates into a concise operator-facing summary."""
    candidates = list(sync_state.get("candidates", []))
    duplicates = list(sync_state.get("duplicate_titles", []))
    uncovered = list(sync_state.get("uncovered_archetypes", []))
    proposal_summary = dict(sync_state.get("proposal_summary", {}))

    lines = [
        "NotebookLM Sync Brief",
        f"Articles: {sync_state.get('article_count', 0)}",
        f"Raw items: {sync_state.get('raw_count', 0)}",
        f"Proposals: {proposal_summary.get('count', 0)} total, {proposal_summary.get('approved_count', 0)} approved",
        f"Active queue: {proposal_summary.get('active_count', 0)}",
    ]

    if candidates:
        lines.append("Sync candidates:")
        for candidate in candidates[:10]:
            lines.append(
                f"- [{candidate.get('kind', 'item')}] {candidate.get('title', 'Untitled')}"
                f" ({candidate.get('status', 'unknown')}, p={_as_float(candidate.get('priority')):.2f})"
            )
            if candidate.get("summary"):
                lines.append(f"  {candidate['summary']}")

    if duplicates:
        lines.append("Duplicate topic groups:")
        for group in duplicates[:5]:
            files = ", ".join(group.get("files", []))
            lines.append(f"- {group.get('title_key', 'unknown')}: {files}")

    if uncovered:
        lines.append("Missing canon coverage:")
        lines.append(", ".join(uncovered[:10]))

    return "\n".join(lines)


def generate_followup_questions(sync_state: Mapping[str, object], limit: int = 5) -> list[str]:
    """Generate the next questions to ask NotebookLM after canon changes."""
    candidates = list(sync_state.get("candidates", []))
    uncovered = list(sync_state.get("uncovered_archetypes", []))
    duplicates = list(sync_state.get("duplicate_titles", []))
    article_count = sync_state.get("article_count", 0)
    raw_count = sync_state.get("raw_count", 0)

    questions: list[str] = []
    if candidates:
        top = candidates[0]
        questions.append(
            f"What is the strongest next synthesis question for the new {top.get('kind', 'canon')} change "
            f"'{top.get('title', 'untitled')}'?"
        )
    if uncovered:
        questions.append(
            f"Which missing archetype article should we write first from this set: {', '.join(uncovered[:5])}?"
        )
    if duplicates:
        questions.append(
            f"How should we merge or de-duplicate the overlapping topic group '{duplicates[0].get('title_key', 'unknown')}'?"
        )
    questions.append(
        f"What should Lore learn next after reviewing {article_count} canon articles and {raw_count} raw items?"
    )
    questions.append(
        "What proposal patterns should be accepted or rejected more aggressively to keep the canon high-signal?"
    )
    return questions[:limit]


def build_notebooklm_sync_pack(
    *,
    proposal_queue: Sequence[Mapping[str, object]] | None = None,
    approved_articles: Sequence[Mapping[str, object]] | None = None,
    report: Mapping[str, object] | None = None,
) -> dict:
    """Build a structured NotebookLM sync pack."""
    sync_state = collect_sync_candidates(
        proposal_queue=proposal_queue,
        approved_articles=approved_articles,
        report=report,
    )
    return {
        "title": "Lore Canon Sync Pack",
        "summary": summarize_sync_candidates(sync_state),
        "followup_questions": generate_followup_questions(sync_state),
        "sync_state": sync_state,
        "router_status": routing.build_router_status(limit=100),
    }
