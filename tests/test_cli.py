"""Tests for the LORE CLI — standalone, zero-dependency command line."""

import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
CLI = [PYTHON, "-m", "lore.cli"]
REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*CLI, *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
        check=check,
    )


def test_scaffold_stdout():
    """scaffold circuit_breaker outputs Python code to stdout."""
    result = _run("scaffold", "circuit_breaker")
    assert result.returncode == 0
    assert "CircuitBreaker" in result.stdout
    assert "class CircuitState" in result.stdout


def test_scaffold_list():
    """scaffold --list shows all 15 patterns."""
    result = _run("scaffold", "--list")
    assert result.returncode == 0
    assert "circuit_breaker" in result.stdout
    assert "dead_letter_queue" in result.stdout
    assert "supervisor_worker" in result.stdout
    assert "19 patterns available" in result.stdout


def test_scaffold_framework():
    """scaffold circuit_breaker --framework langgraph outputs LangGraph code."""
    result = _run("scaffold", "circuit_breaker", "--framework", "langgraph")
    assert result.returncode == 0
    assert "LangGraph" in result.stdout


def test_scaffold_invalid_pattern():
    """scaffold with invalid pattern returns error."""
    result = _run("scaffold", "nonexistent_pattern_xyz", check=False)
    assert result.returncode != 0
    assert "Error" in result.stderr


def test_scaffold_output_dir(tmp_path):
    """scaffold -o writes file to directory."""
    result = subprocess.run(
        [*CLI, "scaffold", "circuit_breaker", "-o", str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0
    out_file = tmp_path / "circuit_breaker.py"
    assert out_file.exists()
    assert "CircuitBreaker" in out_file.read_text()


def test_search():
    """search 'circuit breaker' returns results."""
    result = _run("search", "circuit", "breaker")
    assert result.returncode == 0
    assert "result" in result.stdout.lower()


def test_search_no_query():
    """search with empty query handled gracefully."""
    # argparse will error on missing required arg
    result = _run("search", check=False)
    assert result.returncode != 0


def test_read():
    """read a valid article returns content."""
    result = _run("read", "circuit-breaker-pattern-for-ai-agents")
    assert result.returncode == 0
    assert len(result.stdout) > 100


def test_read_invalid():
    """read nonexistent article returns error."""
    result = _run("read", "nonexistent-article-that-does-not-exist-xyz", check=False)
    assert result.returncode != 0
    assert "Error" in result.stderr


def test_list():
    """list shows articles."""
    result = _run("list")
    assert result.returncode == 0
    assert "circuit-breaker" in result.stdout
    assert "articles in the Codex" in result.stdout


def test_archetype():
    """archetype circuit-breaker returns JSON data."""
    result = _run("archetype", "circuit-breaker")
    assert result.returncode == 0
    assert "The Breaker" in result.stdout
    assert "Guardian of the Gate" in result.stdout


def test_archetype_all():
    """archetype --all lists all archetypes."""
    result = _run("archetype", "--all")
    assert result.returncode == 0
    assert "The Breaker" in result.stdout
    assert "The Commander" in result.stdout
    assert "15 archetypes" in result.stdout


def test_story():
    """story circuit-breaker returns narrative chapter."""
    result = _run("story", "circuit-breaker")
    assert result.returncode == 0
    assert "The Breaker" in result.stdout
    assert "Guardian of the Gate" in result.stdout
    assert "## The Lore" in result.stdout
    assert "## Powers" in result.stdout


def test_story_invalid():
    """story with invalid pattern returns error."""
    result = _run("story", "nonexistent-xyz", check=False)
    assert result.returncode != 0
    assert "Error" in result.stderr


def test_no_command():
    """Running with no command shows help."""
    result = _run(check=False)
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "LORE" in result.stdout
