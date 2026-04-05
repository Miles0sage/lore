"""Proposal queue and review utilities for Lore evolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re

from .config import get_raw_dir, get_wiki_dir

PROPOSAL_STATUSES = (
    "proposed",
    "in_review",
    "approved",
    "rejected",
    "merged",
    "published",
    "archived",
)

SOURCE_QUALITY_SCORES = {
    "paper": 1.0,
    "official-docs": 0.95,
    "repo": 0.9,
    "video": 0.65,
    "manual": 0.6,
    "note": 0.5,
}

STRATEGIC_BONUS_KEYWORDS = {
    "rag",
    "retrieval",
    "memory",
    "observability",
    "evaluation",
    "routing",
    "scheduler",
    "timekeeper",
    "librarian",
    "architect",
    "agent",
}


@dataclass
class Proposal:
    id: str
    title: str
    path: Path
    content: str
    source: str
    owner: str
    proposal_type: str
    status: str
    confidence: float
    created_at: str
    updated_at: str
    reviewer: str
    review_notes: str
    novelty_score: float
    overlap_score: float
    evidence_score: float
    strategic_score: float
    priority_score: float
    publish_recommendation: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "path": str(self.path),
            "source": self.source,
            "owner": self.owner,
            "proposal_type": self.proposal_type,
            "status": self.status,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "reviewer": self.reviewer,
            "review_notes": self.review_notes,
            "novelty_score": self.novelty_score,
            "overlap_score": self.overlap_score,
            "evidence_score": self.evidence_score,
            "strategic_score": self.strategic_score,
            "priority_score": self.priority_score,
            "publish_recommendation": self.publish_recommendation,
        }


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "proposal"


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    marker = "\n---\n"
    end = text.find(marker, 4)
    if end == -1:
        return {}, text

    frontmatter = text[4:end]
    body = text[end + len(marker):]
    data: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data, body


def _render_frontmatter(data: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in data.items():
        safe_value = str(value).replace("\n", " ").strip()
        lines.append(f"{key}: {safe_value}")
    lines.append("---")
    return "\n".join(lines)


def _article_titles() -> list[str]:
    titles: list[str] = []
    for path in sorted(get_wiki_dir().glob("*.md")):
        text = path.read_text(errors="replace")
        title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), path.stem)
        titles.append(title)
    return titles


def _title_similarity(left: str, right: str) -> float:
    left_tokens = set(re.findall(r"[a-z0-9]+", left.lower()))
    right_tokens = set(re.findall(r"[a-z0-9]+", right.lower()))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _compute_scores(title: str, source: str, confidence: float) -> dict[str, float | str]:
    similarities = [_title_similarity(title, existing) for existing in _article_titles()]
    overlap_score = max(similarities, default=0.0)
    novelty_score = 1.0 - overlap_score
    evidence_score = SOURCE_QUALITY_SCORES.get(source, 0.55)
    strategic_score = 0.5
    title_tokens = set(re.findall(r"[a-z0-9]+", title.lower()))
    if title_tokens & STRATEGIC_BONUS_KEYWORDS:
        strategic_score = 0.9

    priority_score = (
        novelty_score * 0.4
        + evidence_score * 0.2
        + strategic_score * 0.2
        + max(0.0, min(confidence, 1.0)) * 0.2
    )
    publish_recommendation = "review_now" if priority_score >= 0.7 else "review_later"
    if overlap_score >= 0.7:
        publish_recommendation = "merge_candidate"

    return {
        "novelty_score": round(novelty_score, 3),
        "overlap_score": round(overlap_score, 3),
        "evidence_score": round(evidence_score, 3),
        "strategic_score": round(strategic_score, 3),
        "priority_score": round(priority_score, 3),
        "publish_recommendation": publish_recommendation,
    }


def _proposal_path(proposal_id: str) -> Path:
    return get_raw_dir() / f"{proposal_id}.md"


def _load_from_path(path: Path) -> Proposal:
    text = path.read_text(errors="replace")
    metadata, body = _split_frontmatter(text)
    title = metadata.get("title") or next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), path.stem)
    confidence = float(metadata.get("confidence", "0.5"))
    scores = _compute_scores(title, metadata.get("source", "note"), confidence)

    return Proposal(
        id=path.stem,
        title=title,
        path=path,
        content=body.strip(),
        source=metadata.get("source", "note"),
        owner=metadata.get("owner", "unknown"),
        proposal_type=metadata.get("proposal_type", "article"),
        status=metadata.get("status", "proposed"),
        confidence=confidence,
        created_at=metadata.get("created_at", ""),
        updated_at=metadata.get("updated_at", ""),
        reviewer=metadata.get("reviewer", ""),
        review_notes=metadata.get("review_notes", ""),
        novelty_score=float(metadata.get("novelty_score", scores["novelty_score"])),
        overlap_score=float(metadata.get("overlap_score", scores["overlap_score"])),
        evidence_score=float(metadata.get("evidence_score", scores["evidence_score"])),
        strategic_score=float(metadata.get("strategic_score", scores["strategic_score"])),
        priority_score=float(metadata.get("priority_score", scores["priority_score"])),
        publish_recommendation=metadata.get("publish_recommendation", str(scores["publish_recommendation"])),
    )


def get_proposal(proposal_id: str) -> Proposal | None:
    path = _proposal_path(proposal_id)
    if path.exists():
        return _load_from_path(path)

    raw_dir = get_raw_dir()
    matches = sorted(raw_dir.glob(f"*{proposal_id}*.md")) if raw_dir.exists() else []
    if matches:
        return _load_from_path(matches[0])
    return None


def list_proposals(status: str | None = None, limit: int = 20) -> list[dict]:
    raw_dir = get_raw_dir()
    if not raw_dir.exists():
        return []

    proposals = [_load_from_path(path) for path in sorted(raw_dir.glob("*.md"))]
    if status:
        proposals = [proposal for proposal in proposals if proposal.status == status]
    proposals.sort(key=lambda proposal: (proposal.priority_score, proposal.updated_at), reverse=True)
    return [proposal.to_dict() for proposal in proposals[:limit]]


def create_proposal(
    title: str,
    content: str,
    source: str = "manual",
    owner: str = "unknown",
    confidence: float = 0.6,
    proposal_type: str = "article",
) -> dict:
    raw_dir = get_raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)

    proposal_id = f"{datetime.now(UTC).strftime('%Y-%m-%d')}-{_slugify(title)}"
    path = _proposal_path(proposal_id)
    timestamp = _utc_now()
    scores = _compute_scores(title, source, confidence)

    metadata = {
        "title": title,
        "source": source,
        "owner": owner,
        "proposal_type": proposal_type,
        "status": "proposed",
        "confidence": f"{confidence:.2f}",
        "created_at": timestamp,
        "updated_at": timestamp,
        "reviewer": "",
        "review_notes": "",
        "novelty_score": scores["novelty_score"],
        "overlap_score": scores["overlap_score"],
        "evidence_score": scores["evidence_score"],
        "strategic_score": scores["strategic_score"],
        "priority_score": scores["priority_score"],
        "publish_recommendation": scores["publish_recommendation"],
    }
    body = f"# {title}\n\n{content.strip()}\n"
    path.write_text(f"{_render_frontmatter(metadata)}\n{body}")
    return _load_from_path(path).to_dict()


def review_proposal(proposal_id: str, status: str, reviewer: str = "", notes: str = "") -> dict:
    if status not in PROPOSAL_STATUSES:
        raise ValueError(f"Invalid proposal status: {status}")

    proposal = get_proposal(proposal_id)
    if proposal is None:
        raise FileNotFoundError(f"Proposal not found: {proposal_id}")

    metadata = {
        "title": proposal.title,
        "source": proposal.source,
        "owner": proposal.owner,
        "proposal_type": proposal.proposal_type,
        "status": status,
        "confidence": f"{proposal.confidence:.2f}",
        "created_at": proposal.created_at or _utc_now(),
        "updated_at": _utc_now(),
        "reviewer": reviewer,
        "review_notes": notes,
        "novelty_score": f"{proposal.novelty_score:.3f}",
        "overlap_score": f"{proposal.overlap_score:.3f}",
        "evidence_score": f"{proposal.evidence_score:.3f}",
        "strategic_score": f"{proposal.strategic_score:.3f}",
        "priority_score": f"{proposal.priority_score:.3f}",
        "publish_recommendation": proposal.publish_recommendation,
    }
    proposal.path.write_text(f"{_render_frontmatter(metadata)}\n{proposal.content.strip()}\n")
    return _load_from_path(proposal.path).to_dict()


def summarize_proposals() -> dict:
    raw_dir = get_raw_dir()
    proposals = [_load_from_path(path) for path in sorted(raw_dir.glob("*.md"))] if raw_dir.exists() else []
    by_status = {status: 0 for status in PROPOSAL_STATUSES}
    for proposal in proposals:
        by_status[proposal.status] = by_status.get(proposal.status, 0) + 1

    active_proposals = [
        proposal
        for proposal in proposals
        if proposal.status in {"proposed", "in_review", "approved"}
    ]
    top_candidates = [
        proposal.to_dict()
        for proposal in active_proposals
    ][:5]

    return {
        "proposal_count": len(proposals),
        "active_proposal_count": len(active_proposals),
        "by_status": by_status,
        "top_candidates": top_candidates,
    }
