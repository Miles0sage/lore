"""Evolution audit utilities for the Codex."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re

from . import archetypes, proposals, scaffold
from .config import get_raw_dir, get_wiki_dir, get_workspace_root


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _article_title(path: Path) -> str:
    text = path.read_text(errors="replace")
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def build_evolution_report() -> dict:
    workspace = get_workspace_root()
    wiki_dir = get_wiki_dir()
    raw_dir = get_raw_dir()
    articles = sorted(wiki_dir.glob("*.md"))

    article_by_norm_title: dict[str, list[str]] = defaultdict(list)
    article_by_norm_stem: dict[str, list[str]] = defaultdict(list)
    article_titles: dict[str, str] = {}
    for article in articles:
        title = _article_title(article)
        article_titles[article.stem] = title
        article_by_norm_title[_normalize(title)].append(article.name)
        article_by_norm_stem[_normalize(article.stem)].append(article.name)

    duplicate_titles = [
        {"title_key": key, "files": files}
        for key, files in sorted(article_by_norm_title.items())
        if len(files) > 1
    ]
    duplicate_stems = [
        {"stem_key": key, "files": files}
        for key, files in sorted(article_by_norm_stem.items())
        if len(files) > 1
    ]

    pattern_aliases = {
        "circuit-breaker": ["circuit-breaker-pattern-for-ai-agents", "circuit-breaker"],
        "dead-letter-queue": ["dead-letter-queue-pattern-for-ai-agents", "dead-letter-queue"],
        "reviewer-loop": ["reviewer-loop-pattern", "reviewer-loop"],
        "three-layer-memory": ["three-layer-memory-stack", "three-layer-memory"],
        "handoff-pattern": ["handoff-pattern"],
        "supervisor-worker": ["supervisor-worker-pattern", "supervisor-worker"],
        "tool-health-monitoring": ["tool-health-monitoring-for-ai-agents", "tool-health-monitoring"],
        "model-routing": ["model-routing"],
        "sentinel": ["sentinel-observability-pattern", "sentinel"],
        "librarian": ["librarian-retrieval-pattern", "librarian"],
        "scout": ["scout-discovery-pattern", "scout"],
        "cartographer": ["cartographer-knowledge-graph-pattern", "cartographer"],
        "alchemist": ["alchemist-prompt-routing-pattern", "alchemist"],
        "timekeeper": ["timekeeper-scheduling-pattern", "timekeeper"],
        "architect": ["architect-system-design-pattern", "architect"],
    }

    article_stems = set(article_titles)
    archetype_coverage = []
    uncovered_archetypes = []
    for pattern_id, data in archetypes.ARCHETYPES.items():
        aliases = pattern_aliases.get(pattern_id, [pattern_id])
        covered_by = next((alias for alias in aliases if alias in article_stems), None)
        entry = {
            "pattern_id": pattern_id,
            "name": data["name"],
            "covered": bool(covered_by),
            "article_id": covered_by,
        }
        archetype_coverage.append(entry)
        if not covered_by:
            uncovered_archetypes.append(pattern_id)

    scaffold_article_gaps = []
    for pattern_entry in scaffold.list_patterns():
        pattern = pattern_entry["pattern"] if isinstance(pattern_entry, dict) else pattern_entry
        article_key = pattern.replace("_", "-")
        article_exists = any(
            article_key == stem or article_key in stem or stem in article_key
            for stem in article_stems
        )
        if not article_exists:
            scaffold_article_gaps.append(pattern)

    raw_count = len(list(raw_dir.glob("*.md"))) if raw_dir.exists() else 0
    proposal_summary = proposals.summarize_proposals()

    priorities = []
    if duplicate_titles:
        priorities.append("Deduplicate overlapping wiki articles before adding new content.")
    if duplicate_stems:
        priorities.append("Merge same-topic article variants and keep one canonical slug per concept.")
    if uncovered_archetypes:
        priorities.append("Add canonical articles for internal-only archetypes before expanding the cast.")
    if raw_count == 0:
        priorities.append("Seed `raw/` with research briefs so evolution has material to compile.")
    priorities.append("Keep the private build focused on ingestion quality, review gates, and measurable coverage.")
    priorities.append("Open source the static codex, basic search, and a small scaffold set; keep autonomous research private.")

    return {
        "workspace_root": str(workspace),
        "wiki_dir": str(wiki_dir),
        "raw_dir": str(raw_dir),
        "article_count": len(articles),
        "raw_count": raw_count,
        "proposal_summary": proposal_summary,
        "duplicate_titles": duplicate_titles,
        "duplicate_stems": duplicate_stems,
        "archetype_coverage": archetype_coverage,
        "uncovered_archetypes": uncovered_archetypes,
        "scaffold_article_gaps": scaffold_article_gaps,
        "priorities": priorities,
    }
