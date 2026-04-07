from pathlib import Path

from lore.config import REPO_ROOT, get_audit_dir, get_raw_dir, get_router_log_path, get_telemetry_dir, get_wiki_dir, get_workspace_root


def test_default_workspace_points_at_repo_root(monkeypatch):
    monkeypatch.delenv("LORE_WIKI_DIR", raising=False)

    assert get_workspace_root() == REPO_ROOT
    assert get_wiki_dir() == REPO_ROOT / "wiki"
    assert get_raw_dir() == REPO_ROOT / "raw"


def test_wiki_env_can_point_directly_at_wiki_dir(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    wiki_dir = workspace / "wiki"
    wiki_dir.mkdir(parents=True)

    monkeypatch.setenv("LORE_WIKI_DIR", str(wiki_dir))

    assert get_workspace_root() == workspace.resolve()
    assert get_wiki_dir() == wiki_dir.resolve()


def test_telemetry_paths_resolve_inside_workspace(monkeypatch, tmp_path: Path):
    workspace = tmp_path / "workspace"
    (workspace / "wiki").mkdir(parents=True)
    monkeypatch.setenv("LORE_WIKI_DIR", str(workspace))

    assert get_telemetry_dir() == workspace.resolve() / ".lore"
    assert get_router_log_path() == workspace.resolve() / ".lore" / "router_events.jsonl"
    assert get_audit_dir() == workspace.resolve() / ".lore" / "audits"
