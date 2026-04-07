from lore import search


def test_search_finds_circuit_breaker_article(monkeypatch):
    monkeypatch.delenv("LORE_WIKI_DIR", raising=False)

    results = search.search("circuit breaker failure cascade", limit=3)

    assert results
    assert results[0]["id"] == "circuit-breaker-pattern-for-ai-agents"


def test_read_article_returns_content(monkeypatch):
    monkeypatch.delenv("LORE_WIKI_DIR", raising=False)

    article = search.read_article("model-routing")

    assert article is not None
    assert article["title"] == "Model Routing"
    assert "##" in article["content"]


def test_load_articles_uses_cache_until_wiki_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(search, "get_wiki_dir", lambda: tmp_path)
    monkeypatch.setattr(search, "_article_cache", None)
    monkeypatch.setattr(search, "_article_cache_key", None)

    article = tmp_path / "first.md"
    article.write_text("# First\n\nCached content")

    first = search._load_articles()
    second = search._load_articles()

    assert first is second

    updated = tmp_path / "second.md"
    updated.write_text("# Second\n\nFresh content")

    third = search._load_articles()

    assert third is not first
    assert {item["id"] for item in third} == {"first", "second"}
