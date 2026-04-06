"""Tests for lore.teaching — pattern compilation for agent injection."""

import pytest

from lore import teaching


def test_compile_lesson_claude_md():
    """Compile a known pattern in claude_md format."""
    result = teaching.compile_lesson("circuit-breaker", format="claude_md")
    assert "error" not in result
    assert result["pattern"] == "circuit-breaker"
    assert result["format"] == "claude_md"
    assert result["archetype"] == "The Breaker"
    assert result["word_count"] > 0
    # Content should contain archetype name and imperative directives
    content = result["content"]
    assert "The Breaker" in content
    assert "Mandatory Behaviors" in content or "Pattern Description" in content
    assert "Fault isolation" in content


def test_compile_lesson_system_prompt():
    """Compile a known pattern in system_prompt format."""
    result = teaching.compile_lesson("circuit-breaker", format="system_prompt")
    assert "error" not in result
    assert result["format"] == "system_prompt"
    assert result["archetype"] == "The Breaker"
    # System prompt should be a dense paragraph, not markdown
    content = result["content"]
    assert "The Breaker" in content
    assert "# " not in content  # No markdown headers in system prompts


def test_compile_lesson_skill_format():
    """Compile in skill format has yaml frontmatter."""
    result = teaching.compile_lesson("circuit-breaker", format="skill")
    assert "error" not in result
    assert result["format"] == "skill"
    content = result["content"]
    assert content.startswith("---")
    assert "name:" in content
    assert "description:" in content


def test_compile_lesson_mcp_description():
    """Compile in mcp_description format is concise text."""
    result = teaching.compile_lesson("circuit-breaker", format="mcp_description")
    assert "error" not in result
    assert result["format"] == "mcp_description"
    content = result["content"]
    assert "The Breaker" in content
    assert len(content) > 20


def test_compile_lesson_unknown_pattern():
    """Unknown pattern returns error gracefully."""
    result = teaching.compile_lesson("nonexistent-pattern-xyz-999")
    assert "error" in result
    assert result["content"] == ""
    assert result["word_count"] == 0
    assert result["archetype"] is None
    assert result["has_scaffold"] is False


def test_compile_lesson_invalid_format():
    """Invalid format returns error."""
    result = teaching.compile_lesson("circuit-breaker", format="bad_format")
    assert "error" in result
    assert "bad_format" in result["error"]


def test_list_teachable_patterns():
    """Returns non-empty list with correct keys."""
    patterns = teaching.list_teachable_patterns()
    assert len(patterns) > 0
    for p in patterns:
        assert "pattern_id" in p
        assert "name" in p
        assert "has_archetype" in p
        assert "has_article" in p
        assert "has_scaffold" in p
        # All entries come from archetypes, so has_archetype is always True
        assert p["has_archetype"] is True


def test_fleet_brief():
    """Compile lessons for multiple explicit patterns."""
    result = teaching.compile_fleet_brief(["circuit-breaker", "reviewer-loop"])
    assert "lessons" in result
    assert "summary" in result
    assert "agent_count" in result
    assert len(result["lessons"]) >= 1  # At least one should compile
    for lesson in result["lessons"]:
        assert "pattern" in lesson
        assert "content" in lesson
        assert "format" in lesson


def test_fleet_brief_no_args():
    """Compile all teachable patterns when no args given."""
    result = teaching.compile_fleet_brief(None)
    assert "lessons" in result
    assert len(result["lessons"]) > 0


def test_compile_lesson_has_scaffold_flag():
    """circuit-breaker has a scaffold, verify the flag."""
    result = teaching.compile_lesson("circuit-breaker")
    assert result["has_scaffold"] is True

    # reviewer-loop also has a scaffold
    result2 = teaching.compile_lesson("reviewer-loop")
    assert result2["has_scaffold"] is True
