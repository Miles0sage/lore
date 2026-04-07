"""Tests for lore.evolve — autonomous evolution daemon."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lore.evolve import (
    _extract_gap_patterns,
    _load_audit_files,
    _existing_template_names,
    _propose_stub,
    run_evolution,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_audit(tmp_path: Path, filename: str, patterns: list[str]) -> Path:
    """Write a minimal audit JSON file with the given scaffold patterns."""
    lore_actions = [
        {"type": "scaffold", "pattern": p, "command": f"lore scaffold {p}", "why": "test"}
        for p in patterns
    ]
    data = {
        "root": str(tmp_path),
        "report": {"summary": "test", "top_findings": [], "missing_capabilities": []},
        "lore_actions": lore_actions,
    }
    path = tmp_path / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_load_audit_files_empty_dir(tmp_path: Path) -> None:
    audits = _load_audit_files(tmp_path)
    assert audits == []


def test_load_audit_files_missing_dir(tmp_path: Path) -> None:
    audits = _load_audit_files(tmp_path / "nonexistent")
    assert audits == []


def test_load_audit_files_skips_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("not json", encoding="utf-8")
    audits = _load_audit_files(tmp_path)
    assert audits == []


def test_load_audit_files_loads_valid(tmp_path: Path) -> None:
    _make_audit(tmp_path, "audit1.json", ["circuit_breaker"])
    audits = _load_audit_files(tmp_path)
    assert len(audits) == 1
    assert audits[0]["lore_actions"][0]["pattern"] == "circuit_breaker"


def test_extract_gap_patterns_counts_correctly(tmp_path: Path) -> None:
    audits = [
        {"lore_actions": [{"type": "scaffold", "pattern": "circuit_breaker"}]},
        {"lore_actions": [{"type": "scaffold", "pattern": "circuit_breaker"}]},
        {"lore_actions": [{"type": "scaffold", "pattern": "dead_letter_queue"}]},
        {"lore_actions": [{"type": "install", "pattern": "circuit_breaker"}]},  # non-scaffold, ignored
    ]
    counts = _extract_gap_patterns(audits)
    assert counts["circuit_breaker"] == 2
    assert counts["dead_letter_queue"] == 1
    assert "circuit_breaker" not in {k for k, v in counts.items() if v > 2}


def test_extract_gap_patterns_empty(tmp_path: Path) -> None:
    counts = _extract_gap_patterns([])
    assert len(counts) == 0


def test_existing_template_names_includes_known_templates(tmp_path: Path) -> None:
    names = _existing_template_names(tmp_path)
    # TEMPLATES from scaffold always includes these core patterns
    assert "circuit_breaker" in names
    assert "dead_letter_queue" in names


def test_existing_template_names_includes_files_in_dir(tmp_path: Path) -> None:
    (tmp_path / "my_custom_pattern.py").write_text("# stub", encoding="utf-8")
    names = _existing_template_names(tmp_path)
    assert "my_custom_pattern" in names


def test_propose_stub_structure() -> None:
    stub = _propose_stub("my_pattern", 3)
    assert stub["pattern"] == "my_pattern"
    assert stub["frequency"] == 3
    assert stub["stub_filename"] == "my_pattern.py"
    assert "my_pattern" in stub["stub_content"]
    assert "def build_my_pattern" in stub["stub_content"]


# ---------------------------------------------------------------------------
# Integration tests for run_evolution
# ---------------------------------------------------------------------------

def test_run_evolution_no_audits(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    result = run_evolution(audit_dir=audit_dir, template_dir=tmp_path / "templates")
    assert result["audits_analyzed"] == 0
    assert result["top_gaps"] == []
    assert result["proposed_patterns"] == []
    assert Path(result["report_path"]).exists()


def test_run_evolution_proposes_new_pattern(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    # A novel pattern that won't exist in TEMPLATES
    novel = "flux_capacitor_pattern"
    _make_audit(tmp_path / "audits", "a1.json", [novel])
    _make_audit(tmp_path / "audits", "a2.json", [novel])

    result = run_evolution(audit_dir=audit_dir, template_dir=template_dir)
    assert result["audits_analyzed"] == 2
    proposed_names = [s["pattern"] for s in result["proposed_patterns"]]
    assert novel in proposed_names


def test_run_evolution_skips_existing_templates(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    # circuit_breaker is in TEMPLATES — should NOT be proposed even if frequent
    _make_audit(tmp_path / "audits", "a1.json", ["circuit_breaker"])
    _make_audit(tmp_path / "audits", "a2.json", ["circuit_breaker"])

    result = run_evolution(audit_dir=audit_dir, template_dir=template_dir)
    proposed_names = [s["pattern"] for s in result["proposed_patterns"]]
    assert "circuit_breaker" not in proposed_names


def test_run_evolution_min_frequency_threshold(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    novel = "rare_pattern_xyz"
    _make_audit(tmp_path / "audits", "a1.json", [novel])  # only appears once

    result = run_evolution(audit_dir=audit_dir, template_dir=template_dir, min_frequency=2)
    proposed_names = [s["pattern"] for s in result["proposed_patterns"]]
    assert novel not in proposed_names


def test_run_evolution_writes_report(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()

    result = run_evolution(audit_dir=audit_dir)
    report_path = Path(result["report_path"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Lore Evolution Report" in content
    assert "Audits analyzed" in content


def test_run_evolution_report_contains_proposals(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audits"
    audit_dir.mkdir()
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    novel = "quantum_entanglement_router"
    _make_audit(tmp_path / "audits", "a1.json", [novel])
    _make_audit(tmp_path / "audits", "a2.json", [novel])

    result = run_evolution(audit_dir=audit_dir, template_dir=template_dir)
    report_path = Path(result["report_path"])
    content = report_path.read_text(encoding="utf-8")
    assert novel in content
