"""Shared path resolution for local and deployed LORE workspaces."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _looks_like_workspace(path: Path) -> bool:
    return (path / "wiki").is_dir() or (path / "raw").is_dir() or (path / "dwiki.yaml").is_file()


def _looks_like_wiki_dir(path: Path) -> bool:
    return path.is_dir() and path.name == "wiki"


def get_workspace_root() -> Path:
    """Resolve the active LORE workspace root.

    Supports either:
    - `LORE_WIKI_DIR` pointing at a dwiki workspace root
    - `LORE_WIKI_DIR` pointing directly at the `wiki/` directory
    - no env var, in which case the checked-out repo is used
    """
    raw_value = os.environ.get("LORE_WIKI_DIR", "").strip()
    if raw_value:
        candidate = Path(raw_value).expanduser().resolve()
        if _looks_like_workspace(candidate):
            return candidate
        if _looks_like_wiki_dir(candidate):
            return candidate.parent
    return REPO_ROOT


def get_wiki_dir() -> Path:
    workspace = get_workspace_root()
    wiki_dir = workspace / "wiki"
    if wiki_dir.is_dir():
        return wiki_dir
    if _looks_like_wiki_dir(workspace):
        return workspace
    return wiki_dir


def get_raw_dir() -> Path:
    return get_workspace_root() / "raw"


def get_evolve_log_path() -> Path:
    return Path(os.environ.get("LORE_EVOLVE_LOG_FILE", "/var/log/lore-evolve.log"))


def get_telemetry_dir() -> Path:
    return get_workspace_root() / ".lore"


def get_router_log_path() -> Path:
    return get_telemetry_dir() / "router_events.jsonl"


def get_audit_dir() -> Path:
    return get_telemetry_dir() / "audits"


def get_dlq_db_path(base_dir: Path | None = None) -> Path:
    telemetry_dir = (base_dir / ".lore") if base_dir is not None else get_telemetry_dir()
    return telemetry_dir / "dlq.db"


def get_circuit_db_path(base_dir: Path | None = None) -> Path:
    telemetry_dir = (base_dir / ".lore") if base_dir is not None else get_telemetry_dir()
    return telemetry_dir / "circuit_breaker.db"


def get_memory_db_path(base_dir: Path | None = None) -> Path:
    telemetry_dir = (base_dir / ".lore") if base_dir is not None else get_telemetry_dir()
    return telemetry_dir / "memory.db"


def get_soul_path(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else get_workspace_root()
    return root / "SOUL.md"


def get_observability_log_path(base_dir: Path | None = None) -> Path:
    telemetry_dir = (base_dir / ".lore") if base_dir is not None else get_telemetry_dir()
    return telemetry_dir / "observability.jsonl"


def get_circuit_metrics_log_path(base_dir: Path | None = None) -> Path:
    telemetry_dir = (base_dir / ".lore") if base_dir is not None else get_telemetry_dir()
    return telemetry_dir / "circuit_metrics.jsonl"
