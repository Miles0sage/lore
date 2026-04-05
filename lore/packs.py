"""Source-pack and question-pack generation for Lore themes."""

from __future__ import annotations

from typing import Any

from . import search


THEME_QUERIES = {
    "memory": "memory episodic procedural retrieval stack",
    "routing": "model routing supervisor worker handoff",
    "reliability": "circuit breaker dead letter queue observability tool health",
    "research": "scout cartographer librarian notebooklm source pack",
    "deployment": "deployment sandboxing secure agent execution environment isolation",
    "sandboxing": "sandbox docker firecracker gvisor secure execution lethal trifecta",
    "evals": "evaluation telemetry acceptance revision rate dead letter queue routing metrics",
}


def build_theme_pack(theme: str, limit: int = 5) -> dict[str, Any]:
    query = THEME_QUERIES.get(theme, theme)
    results = search.search(query, limit=limit)
    article_ids = [item["id"] for item in results]
    articles = [search.read_article(article_id) for article_id in article_ids]
    articles = [article for article in articles if article is not None]

    source_pack = {
        "theme": theme,
        "query": query,
        "articles": [
            {
                "id": article["id"],
                "title": article["title"],
                "summary": article["content"][:240].replace("\n", " ").strip(),
            }
            for article in articles
        ],
    }

    question_pack = {
        "theme": theme,
        "questions": [
            f"What are the canonical patterns in Lore for {theme}?",
            f"Which articles in Lore overlap most in the {theme} theme and should be merged or clarified?",
            f"What should Lore learn next in the {theme} theme?",
            f"What operational guidance should be added to strengthen Lore's {theme} canon?",
        ],
    }

    return {
        "theme": theme,
        "source_pack": source_pack,
        "question_pack": question_pack,
    }
