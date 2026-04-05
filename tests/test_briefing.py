from lore.briefing import build_and_format_morning_brief, build_morning_brief, format_morning_brief


def test_build_morning_brief_combines_evolution_and_proposals():
    evolution_report = {
        "workspace_root": "/root/lore",
        "article_count": 24,
        "raw_count": 2,
        "duplicate_titles": [{"title_key": "handoff-pattern", "files": ["handoff-pattern.md", "handoff-pattern-2.md"]}],
        "duplicate_stems": [],
        "uncovered_archetypes": ["architect", "timekeeper"],
        "scaffold_article_gaps": ["circuit_breaker"],
        "priorities": ["Deduplicate overlapping wiki articles before adding new content."],
    }
    proposal_summary = {
        "proposal_count": 3,
        "active_proposal_count": 3,
        "by_status": {"proposed": 2, "in_review": 1},
        "top_candidates": [
            {"id": "p1", "title": "Timekeeper Scheduling Pattern", "status": "in_review", "priority_score": 0.96},
            {"id": "p2", "title": "Architect Memory Notes", "status": "proposed", "priority_score": 0.87},
        ],
    }

    brief = build_morning_brief(evolution_report=evolution_report, proposal_summary=proposal_summary, generated_at="2026-04-05T07:00:00Z")

    assert brief["generated_at"] == "2026-04-05T07:00:00Z"
    assert brief["headline"] == "3 proposals queued, 1 duplicate groups, 2 uncovered archetypes"
    assert brief["proposal_count"] == 3
    assert brief["active_proposal_count"] == 3
    assert brief["proposal_status_counts"]["in_review"] == 1
    assert brief["top_proposals"][0]["id"] == "p1"
    assert "Review the top proposal queue items." in brief["next_actions"]
    assert "Resolve duplicate topics before adding new canon." in brief["next_actions"]
    assert "Seed canon coverage for missing archetypes." in brief["next_actions"]


def test_format_morning_brief_renders_operator_sections():
    brief = {
        "generated_at": "2026-04-05T07:00:00Z",
        "headline": "2 proposals queued, 1 duplicate groups, 1 uncovered archetypes",
        "article_count": 24,
        "raw_count": 1,
        "proposal_count": 2,
        "active_proposal_count": 2,
        "duplicate_title_groups": 1,
        "duplicate_stem_groups": 0,
        "priority_actions": ["Deduplicate overlapping wiki articles before adding new content."],
        "top_proposals": [{"title": "Timekeeper Scheduling Pattern", "status": "in_review", "priority_score": 0.96}],
        "next_actions": ["Review the top proposal queue items."],
        "uncovered_archetypes": ["timekeeper"],
    }

    text = format_morning_brief(brief)

    assert "# Lore Morning Brief" in text
    assert "## Stats" in text
    assert "## Priorities" in text
    assert "## Top Proposals" in text
    assert "## Next Actions" in text
    assert "Timekeeper Scheduling Pattern" in text
    assert "timekeeper" in text


def test_build_and_format_morning_brief_returns_both_forms():
    evolution_report = {"article_count": 1, "raw_count": 0, "duplicate_titles": [], "duplicate_stems": [], "uncovered_archetypes": []}
    proposal_summary = {"proposal_count": 0, "by_status": {}, "top_candidates": []}

    brief, text = build_and_format_morning_brief(evolution_report=evolution_report, proposal_summary=proposal_summary)

    assert brief["article_count"] == 1
    assert "Lore Morning Brief" in text
