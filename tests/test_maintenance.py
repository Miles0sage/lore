from lore.maintenance import build_weekly_report, format_weekly_report


def test_weekly_report_builds_from_evolution_report():
    report = {
        "article_count": 24,
        "raw_count": 2,
        "duplicate_titles": [{"title_key": "crewai", "files": ["crewai.md", "crewai-2.md"]}],
        "duplicate_stems": [],
        "uncovered_archetypes": ["architect", "timekeeper"],
        "priorities": ["Deduplicate overlapping wiki articles before adding new content."],
        "proposal_summary": {
            "proposal_count": 3,
            "by_status": {"proposed": 2, "in_review": 1},
            "top_candidates": [{"title": "Low Value", "priority_score": 0.2}],
        },
    }
    weekly = build_weekly_report(report)

    assert weekly["duplicate_groups"] == 1
    assert weekly["proposal_count"] == 3
    assert "architect" in weekly["uncovered_archetypes"]
    assert weekly["low_value_proposals"]


def test_format_weekly_report_contains_sections():
    weekly = {
        "generated_at": "2026-04-05T00:00:00Z",
        "headline": "1 duplicate groups, 2 canon gaps, 3 proposals",
        "article_count": 24,
        "raw_count": 2,
        "proposal_count": 3,
        "duplicate_groups": 1,
        "priority_actions": ["Deduplicate overlapping wiki articles before adding new content."],
        "next_actions": ["Review the top proposal queue items."],
        "uncovered_archetypes": ["architect", "timekeeper"],
        "low_value_proposals": [{"title": "Low Value", "priority_score": 0.2}],
    }
    text = format_weekly_report(weekly)

    assert "# Lore Weekly Canon Report" in text
    assert "## Health" in text
    assert "## Priority Actions" in text
    assert "## Next Actions" in text
    assert "## Low Value Proposals" in text
