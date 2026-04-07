"""LORE search — BM25 over the Codex wiki files."""

import math
import re
from pathlib import Path

from .config import get_wiki_dir

_article_cache: list[dict] | None = None
_article_cache_key: tuple[tuple[str, int, int], ...] | None = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _wiki_cache_key(wiki_dir: Path) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (path.name, stat.st_mtime_ns, stat.st_size)
        for path in sorted(wiki_dir.glob("*.md"))
        for stat in [path.stat()]
    )


def _load_articles() -> list[dict]:
    global _article_cache, _article_cache_key

    wiki_dir = get_wiki_dir()
    cache_key = _wiki_cache_key(wiki_dir)
    if _article_cache is not None and cache_key == _article_cache_key:
        return _article_cache

    articles = []
    for path in sorted(wiki_dir.glob("*.md")):
        text = path.read_text(errors="replace")
        # Strip YAML frontmatter
        body = re.sub(r"^---.*?---\n", "", text, flags=re.DOTALL)
        # Extract title
        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_match.group(1) if title_match else path.stem
        articles.append({
            "id": path.stem,
            "title": title,
            "body": body,
            "tokens": _tokenize(body),
            "path": str(path),
        })
    _article_cache = articles
    _article_cache_key = cache_key
    return _article_cache


def search(query: str, limit: int = 5) -> list[dict]:
    """BM25 search over Codex articles."""
    articles = _load_articles()
    if not articles:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # BM25 parameters
    k1, b = 1.5, 0.75
    N = len(articles)
    avgdl = sum(len(a["tokens"]) for a in articles) / N

    # IDF per query token
    def idf(token: str) -> float:
        df = sum(1 for a in articles if token in a["tokens"])
        return math.log((N - df + 0.5) / (df + 0.5) + 1)

    scored = []
    for article in articles:
        dl = len(article["tokens"])
        freq = {}
        for t in article["tokens"]:
            freq[t] = freq.get(t, 0) + 1

        score = 0.0
        for token in query_tokens:
            tf = freq.get(token, 0)
            if tf == 0:
                continue
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * dl / avgdl)
            score += idf(token) * numerator / denominator

        if score > 0:
            # Boost when query terms appear in title or id (strong relevance signal)
            id_tokens = _tokenize(article["id"])
            title_tokens = _tokenize(article["title"])
            title_matches = sum(1 for t in query_tokens if t in title_tokens)
            id_matches = sum(1 for t in query_tokens if t in id_tokens)
            boost = 1.0 + 0.15 * title_matches + 0.10 * id_matches
            score *= boost

            # Extract snippet around first match
            snippet = _extract_snippet(article["body"], query_tokens)
            scored.append({
                "id": article["id"],
                "title": article["title"],
                "snippet": snippet,
                "score": round(score, 3),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def read_article(article_id: str) -> dict | None:
    """Read a full article from the Codex."""
    wiki_dir = get_wiki_dir()
    path = wiki_dir / f"{article_id}.md"
    if not path.exists():
        # Try fuzzy
        matches = list(wiki_dir.glob(f"*{article_id}*.md"))
        if not matches:
            return None
        path = matches[0]

    text = path.read_text(errors="replace")
    body = re.sub(r"^---.*?---\n", "", text, flags=re.DOTALL)
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    title = title_match.group(1) if title_match else path.stem
    return {"id": path.stem, "title": title, "content": body.strip()}


def list_articles() -> list[dict]:
    """List all articles in the Codex."""
    articles = _load_articles()
    return [{"id": a["id"], "title": a["title"]} for a in articles]


def _extract_snippet(body: str, tokens: list[str], length: int = 200) -> str:
    """Extract a snippet around the first token match."""
    body_lower = body.lower()
    best_pos = len(body)
    for token in tokens:
        pos = body_lower.find(token)
        if 0 <= pos < best_pos:
            best_pos = pos

    start = max(0, best_pos - 60)
    end = min(len(body), start + length)
    snippet = body[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(body):
        snippet = snippet + "..."
    return snippet
