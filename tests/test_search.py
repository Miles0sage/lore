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
