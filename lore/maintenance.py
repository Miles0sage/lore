"""Weekly maintenance reporting for Lore canon health."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from . import briefing, evolution


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_weekly_report(report: dict[str, Any] | None = None) -> dict[str, Any]:
    base_report = report or evolution.build_evolution_report()
    morning_brief = briefing.build_morning_brief(
        evolution_report=base_report,
        proposal_summary=base_report.get("proposal_summary"),
    )

    duplicate_groups = len(base_report.get("duplicate_titles", [])) + len(base_report.get("duplicate_stems", []))
    low_value_proposals = [
        proposal
        for proposal in base_report.get("proposal_summary", {}).get("top_candidates", [])
        if float(proposal.get("priority_score", 0)) < 0.5
    ]

    weekly = {
        "generated_at": _utc_now(),
        "article_count": base_report.get("article_count", 0),
        "raw_count": base_report.get("raw_count", 0),
        "proposal_count": base_report.get("proposal_summary", {}).get("proposal_count", 0),
        "duplicate_groups": duplicate_groups,
        "uncovered_archetypes": list(base_report.get("uncovered_archetypes", [])),
        "low_value_proposals": low_value_proposals,
        "priority_actions": list(base_report.get("priorities", [])),
        "next_actions": list(morning_brief.get("next_actions", [])),
        "headline": f"{duplicate_groups} duplicate groups, {len(base_report.get('uncovered_archetypes', []))} canon gaps, {base_report.get('proposal_summary', {}).get('proposal_count', 0)} proposals",
    }
    return weekly


def format_weekly_report(weekly: dict[str, Any]) -> str:
    lines = [
        "# Lore Weekly Canon Report",
        "",
        f"Generated: {weekly['generated_at']}",
        f"Headline: {weekly['headline']}",
        "",
        "## Health",
        f"- Canon articles: {weekly['article_count']}",
        f"- Raw proposals: {weekly['raw_count']}",
        f"- Proposal queue: {weekly['proposal_count']}",
        f"- Duplicate groups: {weekly['duplicate_groups']}",
        "",
        "## Priority Actions",
    ]
    lines.extend(f"- {item}" for item in weekly["priority_actions"] or ["None"])
    lines.extend([
        "",
        "## Next Actions",
    ])
    lines.extend(f"- {item}" for item in weekly["next_actions"] or ["None"])

    if weekly["uncovered_archetypes"]:
        lines.extend([
            "",
            "## Uncovered Archetypes",
            "- " + ", ".join(weekly["uncovered_archetypes"]),
        ])

    if weekly["low_value_proposals"]:
        lines.extend([
            "",
            "## Low Value Proposals",
        ])
        for proposal in weekly["low_value_proposals"]:
            lines.append(
                f"- {proposal.get('title', proposal.get('id', 'unknown'))} (score {proposal.get('priority_score', 0)})"
            )

    return "\n".join(lines).strip()
