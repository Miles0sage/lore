from lore.evolution import build_evolution_report


def test_evolution_report_no_longer_flags_duplicate_titles(monkeypatch):
    monkeypatch.delenv("LORE_WIKI_DIR", raising=False)

    report = build_evolution_report()
    assert report["duplicate_titles"] == []


def test_evolution_report_covers_core_patterns(monkeypatch):
    monkeypatch.delenv("LORE_WIKI_DIR", raising=False)

    report = build_evolution_report()
    coverage = {entry["pattern_id"]: entry["covered"] for entry in report["archetype_coverage"]}

    assert coverage["circuit-breaker"] is True
    assert coverage["dead-letter-queue"] is True
    assert coverage["reviewer-loop"] is True
