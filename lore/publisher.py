"""Publishing helpers for promoting reviewed proposals into canon."""

from __future__ import annotations

from pathlib import Path
import re

from .config import get_wiki_dir
from . import proposals


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "canon-entry"


def publish_proposal(proposal_id: str, reviewer: str = "", notes: str = "") -> dict:
    proposal = proposals.get_proposal(proposal_id)
    if proposal is None:
        raise FileNotFoundError(f"Proposal not found: {proposal_id}")
    if proposal.status not in {"approved", "published"}:
        raise ValueError("Proposal must be approved before publication")

    wiki_dir = get_wiki_dir()
    wiki_dir.mkdir(parents=True, exist_ok=True)
    article_id = _slugify(proposal.title)
    article_path = wiki_dir / f"{article_id}.md"

    content = proposal.content.strip()
    if not content.startswith("# "):
        content = f"# {proposal.title}\n\n{content}"
    article_path.write_text(content.rstrip() + "\n")

    reviewed = proposals.review_proposal(
        proposal.id,
        "published",
        reviewer=reviewer or proposal.reviewer,
        notes=notes or proposal.review_notes,
    )
    return {
        "proposal_id": proposal.id,
        "article_id": article_id,
        "article_path": str(article_path),
        "published": True,
        "proposal": reviewed,
    }
