from pathlib import Path

from lore import proposals, publisher


def test_publish_proposal_writes_article_and_updates_status(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "raw").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    created = proposals.create_proposal("Scout Research Loop", "## Why\n\nUseful body", source="repo")
    proposals.review_proposal(created["id"], "approved", reviewer="miles", notes="Ship it")

    published = publisher.publish_proposal(created["id"], reviewer="miles", notes="Published to canon")

    assert published["published"] is True
    assert published["proposal"]["status"] == "published"
    article_path = workspace / "wiki" / "scout-research-loop.md"
    assert article_path.exists()
    assert "Scout Research Loop" in article_path.read_text()


def test_publish_requires_approved_status(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "raw").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    created = proposals.create_proposal("Unreviewed Entry", "Body")

    try:
        publisher.publish_proposal(created["id"])
    except ValueError as exc:
        assert "approved" in str(exc)
    else:
        raise AssertionError("Expected publish_proposal to reject unapproved proposals")
