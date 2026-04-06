"""Tests for lore.claude_code — Claude Code integration module."""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from lore import claude_code


# ── generate_claude_md_rules ──────────────────────────────────────────────────


def test_generate_rules_all():
    """Generates rules for all patterns; must contain Circuit Breaker and ALWAYS directives."""
    rules = claude_code.generate_claude_md_rules()
    assert isinstance(rules, str)
    assert len(rules) > 100
    # Must contain the Breaker archetype header
    assert "The Breaker" in rules or "Circuit Breaker" in rules or "circuit" in rules.lower()
    # Must contain imperative directives
    assert "ALWAYS" in rules
    assert "NEVER" in rules or "MUST" in rules


def test_generate_rules_specific():
    """Generates rules for just circuit_breaker; only that pattern should dominate."""
    rules = claude_code.generate_claude_md_rules(["circuit_breaker"])
    assert "The Breaker" in rules
    assert "ALWAYS" in rules
    # Should not mention The Archivist header in a single-pattern request
    # (The Archivist is dead_letter_queue)
    assert "The Archivist" not in rules


def test_generate_rules_dead_letter_queue():
    """Generates rules for dead_letter_queue pattern."""
    rules = claude_code.generate_claude_md_rules(["dead_letter_queue"])
    assert "The Archivist" in rules
    assert "ALWAYS" in rules
    assert "dead letter" in rules.lower() or "DLQ" in rules or "dlq" in rules.lower()


def test_generate_rules_multiple_patterns():
    """Generates rules for multiple patterns, each should appear."""
    rules = claude_code.generate_claude_md_rules(["circuit_breaker", "reviewer_loop"])
    assert "The Breaker" in rules
    assert "The Council" in rules
    assert "ALWAYS" in rules


def test_generate_rules_hyphen_form():
    """Accepts hyphenated pattern IDs (circuit-breaker form)."""
    rules = claude_code.generate_claude_md_rules(["circuit-breaker"])
    assert "The Breaker" in rules
    assert "ALWAYS" in rules


def test_generate_rules_unknown_pattern_graceful():
    """Unknown pattern should not crash — returns partial result."""
    # Should not raise
    rules = claude_code.generate_claude_md_rules(["nonexistent_pattern_xyz_999"])
    assert isinstance(rules, str)


# ── generate_hook_script ──────────────────────────────────────────────────────


def test_generate_hook_circuit_breaker():
    """Generates a valid Python hook script for circuit_breaker."""
    result = claude_code.generate_hook_script("circuit_breaker")
    assert "error" not in result
    assert result["hook_type"] == "PreToolUse"
    assert "Bash" in result["matcher"]
    script = result["script"]
    assert isinstance(script, str)
    assert len(script) > 100
    # Must be valid Python
    try:
        ast.parse(script)
    except SyntaxError as e:
        pytest.fail(f"Generated hook script is not valid Python: {e}")
    # Must contain core logic
    assert "json.load(sys.stdin)" in script
    assert "sys.exit" in script


def test_generate_hook_dead_letter_queue():
    """Generates a valid Python hook for dead_letter_queue."""
    result = claude_code.generate_hook_script("dead_letter_queue")
    assert "error" not in result
    script = result["script"]
    ast.parse(script)  # Must be valid Python
    assert "The Archivist" in script or "dead_letter" in script.lower() or "DLQ" in script


def test_generate_hook_sentinel_observability():
    """Generates a valid Python hook for sentinel_observability."""
    result = claude_code.generate_hook_script("sentinel_observability")
    assert "error" not in result
    script = result["script"]
    ast.parse(script)
    assert "Sentinel" in script or "observability" in script.lower()


def test_generate_hook_reviewer_loop():
    """Generates a valid Python hook for reviewer_loop."""
    result = claude_code.generate_hook_script("reviewer_loop")
    assert "error" not in result
    script = result["script"]
    ast.parse(script)
    assert "Council" in script or "reviewer" in script.lower()


def test_generate_hook_hyphen_form():
    """Accepts hyphenated form (circuit-breaker) as alias."""
    result = claude_code.generate_hook_script("circuit-breaker")
    # hyphen form normalizes to circuit_breaker which is supported
    assert "error" not in result
    ast.parse(result["script"])


def test_generate_hook_unknown():
    """Returns error dict for unknown pattern without crashing."""
    result = claude_code.generate_hook_script("nonexistent_pattern_xyz")
    assert "error" in result
    assert "supported_patterns" in result or "Supported" in result.get("error", "")


# ── generate_skill_file ───────────────────────────────────────────────────────


def test_generate_skill_circuit_breaker():
    """Generates skill file with valid YAML frontmatter for circuit_breaker."""
    skill = claude_code.generate_skill_file("circuit_breaker")
    assert isinstance(skill, str)
    # Must start with YAML frontmatter
    assert skill.startswith("---")
    # Must contain required frontmatter fields
    assert "name:" in skill
    assert "description:" in skill
    assert "pattern:" in skill
    # Must close frontmatter
    lines = skill.split("\n")
    assert lines[0] == "---"
    # Find closing ---
    closing = [i for i, l in enumerate(lines[1:], 1) if l == "---"]
    assert closing, "Skill file must have closing --- for YAML frontmatter"
    # Body must contain the archetype name
    assert "The Breaker" in skill


def test_generate_skill_all_patterns():
    """Generates valid skill files for all patterns that have curated rules."""
    for pattern in claude_code._PATTERN_RULES:
        skill = claude_code.generate_skill_file(pattern)
        assert skill.startswith("---"), f"Skill for {pattern} must start with ---"
        assert "name:" in skill, f"Skill for {pattern} must have name field"
        assert "---" in skill[3:], f"Skill for {pattern} must close frontmatter"


def test_generate_skill_contains_rules():
    """Skill file contains the imperative rules section."""
    skill = claude_code.generate_skill_file("dead_letter_queue")
    assert "The Archivist" in skill
    assert "ALWAYS" in skill or "NEVER" in skill or "MUST" in skill


def test_generate_skill_contains_scaffold_hint():
    """Skill file mentions lore scaffold command."""
    skill = claude_code.generate_skill_file("circuit_breaker")
    assert "lore scaffold" in skill or "lore_scaffold" in skill


# ── generate_mcp_config ───────────────────────────────────────────────────────


def test_generate_mcp_config():
    """Returns a valid MCP config dict with lore server entry."""
    config = claude_code.generate_mcp_config()
    assert isinstance(config, dict)
    assert "mcpServers" in config
    lore = config["mcpServers"]["lore"]
    assert lore["command"] == "python3"
    assert "-m" in lore["args"]
    assert "lore.server" in lore["args"]


# ── install_rules ─────────────────────────────────────────────────────────────


def test_install_rules_creates_files(tmp_path):
    """install_rules writes CLAUDE.md + hooks + skills to tmp dir."""
    result = claude_code.install_rules(str(tmp_path), patterns=["circuit_breaker", "dead_letter_queue"])

    # CLAUDE.md must exist
    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.exists(), "CLAUDE.md must be written"
    content = claude_md.read_text()
    assert "The Breaker" in content
    assert "ALWAYS" in content

    # Hooks directory must exist with scripts
    hooks_dir = tmp_path / ".claude" / "hooks"
    assert hooks_dir.is_dir()
    hook_files = list(hooks_dir.glob("*.py"))
    assert len(hook_files) >= 1, "At least one hook script must be written"

    # Skills directory must exist with files
    skills_dir = tmp_path / ".claude" / "skills"
    assert skills_dir.is_dir()
    skill_files = list(skills_dir.glob("*.md"))
    assert len(skill_files) >= 2, "At least two skill files must be written"

    # Summary dict must have expected keys
    assert "claude_md" in result
    assert "hooks_written" in result
    assert "skills_written" in result
    assert "summary" in result


def test_install_rules_appends_to_existing_claude_md(tmp_path):
    """install_rules appends to existing CLAUDE.md without overwriting existing content."""
    claude_md = tmp_path / "CLAUDE.md"
    existing_content = "# My Project\n\nExisting rules go here.\n"
    claude_md.write_text(existing_content)

    claude_code.install_rules(str(tmp_path), patterns=["circuit_breaker"])

    updated = claude_md.read_text()
    # Original content must still be present
    assert "My Project" in updated
    assert "Existing rules go here." in updated
    # Lore rules must also be present
    assert "The Breaker" in updated


def test_install_rules_all_patterns(tmp_path):
    """install_rules with None patterns installs all available patterns."""
    result = claude_code.install_rules(str(tmp_path))
    assert len(result["patterns_installed"]) >= 4
    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.exists()


def test_install_rules_hook_is_valid_python(tmp_path):
    """Hook scripts written to disk are valid Python."""
    claude_code.install_rules(str(tmp_path), patterns=["circuit_breaker"])
    hooks_dir = tmp_path / ".claude" / "hooks"
    for hook_file in hooks_dir.glob("*.py"):
        source = hook_file.read_text()
        try:
            ast.parse(source)
        except SyntaxError as e:
            pytest.fail(f"Hook file {hook_file.name} is not valid Python: {e}")


# ── CLI: lore rules ───────────────────────────────────────────────────────────


def test_cli_rules_all():
    """lore rules (no args) prints rules to stdout."""
    result = subprocess.run(
        [sys.executable, "-m", "lore.cli", "rules"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI exited {result.returncode}: {result.stderr}"
    assert "ALWAYS" in result.stdout
    assert "The Breaker" in result.stdout or "circuit" in result.stdout.lower()


def test_cli_rules_specific_pattern():
    """lore rules --patterns circuit_breaker prints only that pattern's rules."""
    result = subprocess.run(
        [sys.executable, "-m", "lore.cli", "rules", "--patterns", "circuit_breaker"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI exited {result.returncode}: {result.stderr}"
    assert "The Breaker" in result.stdout
    assert "ALWAYS" in result.stdout


def test_cli_install(tmp_path):
    """lore install --dir <dir> creates expected files."""
    result = subprocess.run(
        [sys.executable, "-m", "lore.cli", "install", "--dir", str(tmp_path), "--patterns", "circuit_breaker"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI exited {result.returncode}: {result.stderr}"
    assert (tmp_path / "CLAUDE.md").exists()
    assert "Installed" in result.stdout or "pattern" in result.stdout.lower()
