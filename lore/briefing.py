"""Morning brief helpers for Lore evolution."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _count_by_status(summary: dict[str, Any]) -> dict[str, int]:
    by_status = summary.get("by_status", {})
    return {str(key): int(value) for key, value in by_status.items()}


def _top_proposals(summary: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    candidates = summary.get("top_candidates") or []
    return [dict(item) for item in candidates[:limit]]


def build_morning_brief(
    evolution_report: dict[str, Any] | None = None,
    proposal_summary: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Combine the evolution report and proposal queue into an operator brief."""
    report = dict(evolution_report or {})
    summary = dict(proposal_summary or report.get("proposal_summary") or {})

    duplicate_titles = report.get("duplicate_titles", [])
    duplicate_stems = report.get("duplicate_stems", [])
    uncovered_archetypes = report.get("uncovered_archetypes", [])
    priorities = list(report.get("priorities", []))
    top_proposals = _top_proposals(summary)

    brief = {
        "generated_at": generated_at or _utc_now(),
        "workspace_root": report.get("workspace_root", ""),
        "article_count": int(report.get("article_count", 0)),
        "raw_count": int(report.get("raw_count", 0)),
        "proposal_count": int(summary.get("proposal_count", 0)),
        "active_proposal_count": int(summary.get("active_proposal_count", summary.get("proposal_count", 0))),
        "proposal_status_counts": _count_by_status(summary),
        "duplicate_title_groups": len(duplicate_titles),
        "duplicate_stem_groups": len(duplicate_stems),
        "duplicate_titles": duplicate_titles,
        "duplicate_stems": duplicate_stems,
        "uncovered_archetypes": uncovered_archetypes,
        "scaffold_article_gaps": list(report.get("scaffold_article_gaps", [])),
        "priority_actions": priorities,
        "top_proposals": top_proposals,
    }

    brief["headline"] = _build_headline(brief)
    brief["next_actions"] = _build_next_actions(brief)
    return brief


def _build_headline(brief: dict[str, Any]) -> str:
    proposal_count = brief["active_proposal_count"]
    duplicate_count = brief["duplicate_title_groups"] + brief["duplicate_stem_groups"]
    uncovered_count = len(brief["uncovered_archetypes"])

    if proposal_count and duplicate_count:
        return f"{proposal_count} proposals queued, {duplicate_count} duplicate groups, {uncovered_count} uncovered archetypes"
    if proposal_count:
        return f"{proposal_count} proposals queued, {uncovered_count} uncovered archetypes"
    if duplicate_count:
        return f"{duplicate_count} duplicate groups, {uncovered_count} uncovered archetypes"
    return f"{brief['article_count']} articles, {uncovered_count} uncovered archetypes"


def _build_next_actions(brief: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    if brief["top_proposals"]:
        actions.append("Review the top proposal queue items.")
    if brief["duplicate_title_groups"] or brief["duplicate_stem_groups"]:
        actions.append("Resolve duplicate topics before adding new canon.")
    if brief["uncovered_archetypes"]:
        actions.append("Seed canon coverage for missing archetypes.")
    if brief["raw_count"] == 0:
        actions.append("Seed raw proposals so evolution has material to compile.")
    if not actions:
        actions.append("Keep the daily evolution loop moving and ask NotebookLM for the next question.")
    return actions


def format_morning_brief(brief: dict[str, Any]) -> str:
    """Render a compact operator-facing morning brief."""
    lines = [
        "# Lore Morning Brief",
        "",
        f"Generated: {brief['generated_at']}",
        f"Headline: {brief['headline']}",
        "",
        "## Stats",
        f"- Articles: {brief['article_count']}",
        f"- Raw proposals: {brief['raw_count']}",
        f"- Proposal queue: {brief['active_proposal_count']}",
        f"- Duplicate title groups: {brief['duplicate_title_groups']}",
        f"- Duplicate stem groups: {brief['duplicate_stem_groups']}",
        "",
        "## Priorities",
    ]
    if brief["priority_actions"]:
        lines.extend(f"- {item}" for item in brief["priority_actions"])
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Top Proposals",
    ])
    if brief["top_proposals"]:
        for item in brief["top_proposals"]:
            lines.append(
                f"- {item.get('title', item.get('id', 'unknown'))} "
                f"({item.get('status', 'unknown')}, score {item.get('priority_score', 0)})"
            )
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Next Actions",
    ])
    lines.extend(f"- {item}" for item in brief["next_actions"])

    if brief["uncovered_archetypes"]:
        lines.extend([
            "",
            "## Uncovered Archetypes",
            "- " + ", ".join(brief["uncovered_archetypes"]),
        ])

    return "\n".join(lines).strip()


def build_and_format_morning_brief(
    evolution_report: dict[str, Any] | None = None,
    proposal_summary: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    brief = build_morning_brief(evolution_report=evolution_report, proposal_summary=proposal_summary)
    return brief, format_morning_brief(brief)
