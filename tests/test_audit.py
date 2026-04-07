from __future__ import annotations

import json
from pathlib import Path

from lore import audit


def test_collect_audit_files_skips_build_outputs(tmp_path: Path):
    (tmp_path / "lore").mkdir()
    (tmp_path / "build").mkdir()
    (tmp_path / "lore" / "server.py").write_text("print('ok')\n")
    (tmp_path / "README.md").write_text("# Demo\n")
    (tmp_path / "build" / "generated.py").write_text("print('skip')\n")

    files = audit.collect_audit_files(tmp_path, max_files=10)
    rels = {str(path.relative_to(tmp_path)) for path in files}

    assert "lore/server.py" in rels
    assert "README.md" in rels
    assert "build/generated.py" not in rels


def test_run_audit_parses_and_persists_report(tmp_path: Path, monkeypatch):
    (tmp_path / "lore").mkdir()
    (tmp_path / "lore" / "server.py").write_text("print('ok')\n")

    monkeypatch.setattr(audit, "get_audit_dir", lambda: tmp_path / ".lore" / "audits")

    def fake_runner(prompt: str, *, cwd: Path, model: str) -> str:
        assert "Repository bundle" in prompt
        assert cwd == tmp_path
        assert model == "gemini-test"
        return json.dumps(
                {
                    "summary": "Main risk is missing audit output plumbing.",
                    "product_direction": "Build audit first.",
                    "top_findings": [{"severity": "high", "title": "Missing command", "files": ["lore/server.py"], "why": "No entry point", "fix": "Add circuit breaker and observability hooks"}],
                    "missing_capabilities": ["verification loop"],
                    "reusable_assets": [{"source": "google-mcp", "asset": "gemini adapter", "value": "large-context reads"}],
                    "next_builds": ["Ship lore audit"],
                }
        )

    result = audit.run_audit(tmp_path, question="Audit this repo", model="gemini-test", runner=fake_runner)

    assert result["backend"] == "gemini_cli"
    assert result["report"]["summary"] == "Main risk is missing audit output plumbing."
    assert result["lore_actions"]
    report_path = Path(result["report_path"])
    assert report_path.exists()


def test_extract_json_object_handles_fenced_output():
    parsed = audit._extract_json_object(
        "```json\n{\"summary\":\"ok\",\"product_direction\":\"x\",\"top_findings\":[],\"missing_capabilities\":[],\"reusable_assets\":[],\"next_builds\":[]}\n```"
    )
    assert parsed["summary"] == "ok"


def test_suggest_lore_actions_maps_patterns():
    actions = audit.suggest_lore_actions(
        {
            "summary": "The system lacks circuit breaker, dead letter queue, and observability.",
            "top_findings": [],
            "missing_capabilities": ["verification loop"],
        }
    )
    commands = {entry["command"] for entry in actions}
    assert "lore scaffold circuit_breaker" in commands
    assert "lore scaffold dead_letter_queue" in commands
    assert any(command.startswith("lore install --patterns") for command in commands)
