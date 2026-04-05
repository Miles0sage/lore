from pathlib import Path

from lore import proposals


def test_create_proposal_writes_frontmatter_and_scores(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "raw").mkdir(parents=True)
    (workspace / "wiki" / "model-routing.md").write_text("# Model Routing\n\nCanonical article.\n")
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    proposal = proposals.create_proposal(
        "Adaptive RAG Routing",
        "Proposal body",
        source="paper",
        owner="codex",
        confidence=0.8,
    )

    assert proposal["status"] == "proposed"
    assert proposal["source"] == "paper"
    assert proposal["owner"] == "codex"
    assert proposal["priority_score"] > 0
    assert (workspace / "raw" / f"{proposal['id']}.md").exists()


def test_list_proposals_orders_by_priority(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "raw").mkdir(parents=True)
    (workspace / "wiki" / "circuit-breaker.md").write_text("# Circuit Breaker\n\nCanon.\n")
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    proposals.create_proposal("Circuit Breaker Retry Notes", "Low novelty", source="note", confidence=0.4)
    high = proposals.create_proposal("Timekeeper Scheduling Pattern", "High novelty", source="paper", confidence=0.9)

    listed = proposals.list_proposals(limit=2)

    assert listed
    assert listed[0]["id"] == high["id"]


def test_review_proposal_updates_status_and_notes(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "raw").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    created = proposals.create_proposal("Scout Research Loop", "Body", source="repo")
    reviewed = proposals.review_proposal(created["id"], "approved", reviewer="miles", notes="Ready for canon")

    assert reviewed["status"] == "approved"
    assert reviewed["reviewer"] == "miles"
    assert reviewed["review_notes"] == "Ready for canon"


def test_summarize_proposals_counts_statuses(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "raw").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    first = proposals.create_proposal("Architect ADR Memory", "Body")
    proposals.review_proposal(first["id"], "in_review", reviewer="codex")
    proposals.create_proposal("Observability Taxonomy", "Body")

    summary = proposals.summarize_proposals()

    assert summary["proposal_count"] == 2
    assert summary["active_proposal_count"] == 2
    assert summary["by_status"]["in_review"] == 1
    assert summary["by_status"]["proposed"] == 1
