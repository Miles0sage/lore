from lore.notebook import (
    build_notebooklm_sync_pack,
    collect_sync_candidates,
    generate_followup_questions,
    summarize_sync_candidates,
)


def test_collect_sync_candidates_uses_approved_proposals_and_articles():
    report = {
        "workspace_root": "/tmp/workspace",
        "article_count": 24,
        "raw_count": 3,
        "duplicate_titles": [{"title_key": "handoff-pattern", "files": ["handoff-pattern.md"]}],
        "uncovered_archetypes": ["architect", "timekeeper"],
    }
    proposals = [
        {
            "id": "2026-04-05-timekeeper-scheduling-pattern",
            "title": "Timekeeper Scheduling Pattern",
            "status": "approved",
            "proposal_type": "article",
            "priority_score": 0.96,
            "review_notes": "Ready for canon",
            "path": "/tmp/workspace/raw/2026-04-05-timekeeper-scheduling-pattern.md",
        },
        {
            "id": "2026-04-05-low-priority-note",
            "title": "Low Priority Note",
            "status": "proposed",
            "proposal_type": "note",
            "priority_score": 0.11,
        },
    ]
    articles = [
        {
            "title": "Approved Article",
            "priority_score": 0.8,
            "summary": "Canonical addition.",
            "path": "/tmp/workspace/wiki/approved-article.md",
        }
    ]

    sync_state = collect_sync_candidates(
        proposal_queue=proposals,
        approved_articles=articles,
        report=report,
    )

    assert sync_state["article_count"] == 24
    assert sync_state["proposal_summary"]["count"] == 2
    assert len(sync_state["candidates"]) == 2
    assert sync_state["candidates"][0]["title"] in {"Timekeeper Scheduling Pattern", "Approved Article"}


def test_summarize_sync_candidates_and_followups():
    sync_state = {
        "article_count": 24,
        "raw_count": 3,
        "proposal_summary": {"count": 2, "approved_count": 1},
        "candidates": [
            {
                "kind": "article",
                "title": "Timekeeper Scheduling Pattern",
                "status": "approved",
                "priority": 0.96,
                "summary": "Canonical addition.",
            }
        ],
        "duplicate_titles": [{"title_key": "handoff-pattern", "files": ["handoff-pattern.md"]}],
        "uncovered_archetypes": ["architect", "timekeeper"],
    }

    summary = summarize_sync_candidates(sync_state)
    questions = generate_followup_questions(sync_state, limit=4)

    assert "NotebookLM Sync Brief" in summary
    assert "Timekeeper Scheduling Pattern" in summary
    assert questions[0].startswith("What is the strongest next synthesis question")
    assert len(questions) == 4


def test_build_notebooklm_sync_pack_round_trips():
    pack = build_notebooklm_sync_pack(
        proposal_queue=[
            {
                "id": "2026-04-05-scout-loop",
                "title": "Scout Loop",
                "status": "approved",
                "priority_score": 0.7,
                "proposal_type": "article",
            }
        ],
        approved_articles=[
            {"title": "Canon Article", "summary": "Approved canon."},
        ],
        report={"article_count": 24, "raw_count": 1, "duplicate_titles": [], "uncovered_archetypes": []},
    )

    assert pack["title"] == "Lore Canon Sync Pack"
    assert "NotebookLM Sync Brief" in pack["summary"]
    assert pack["followup_questions"]
    assert "router_status" in pack
