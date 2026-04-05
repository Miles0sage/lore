from pathlib import Path

from lore.packs import build_theme_pack


def test_build_theme_pack_returns_source_and_question_packs(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    (workspace / "wiki" / "model-routing.md").write_text("# Model Routing\n\nRouting canon.\n")
    (workspace / "wiki" / "supervisor-worker-pattern.md").write_text("# Supervisor Worker Pattern\n\nWorker routing canon.\n")
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    pack = build_theme_pack("routing", limit=3)

    assert pack["theme"] == "routing"
    assert pack["source_pack"]["articles"]
    assert pack["question_pack"]["questions"]
