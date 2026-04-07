"""Tests for the expanded scaffold system — 15 patterns + framework variants."""

import pytest

from lore.scaffold import (
    FRAMEWORK_TEMPLATES,
    TEMPLATES,
    get_template,
    list_patterns,
)

# All 15 pattern names
ALL_PATTERNS = [
    "circuit_breaker",
    "dead_letter_queue",
    "reviewer_loop",
    "supervisor_worker",
    "tool_health_monitor",
    "handoff_pattern",
    "model_routing",
    "three_layer_memory",
    "sentinel_observability",
    "librarian_retrieval",
    "scout_discovery",
    "cartographer_knowledge_graph",
    "timekeeper_scheduling",
    "architect_system_design",
    "alchemist_prompt_routing",
]

# Expected framework variants
EXPECTED_FRAMEWORK_VARIANTS = {
    "circuit_breaker_langgraph",
    "supervisor_worker_langgraph",
    "reviewer_loop_langgraph",
    "supervisor_worker_crewai",
    "reviewer_loop_crewai",
    "handoff_pattern_crewai",
    "handoff_pattern_openai_agents",
    "model_routing_openai_agents",
    "supervisor_worker_openai_agents",
}


class TestAllPatternsExist:
    """Verify all 15 patterns have templates."""

    @pytest.mark.parametrize("pattern", ALL_PATTERNS)
    def test_template_exists(self, pattern: str) -> None:
        template = get_template(pattern)
        assert template is not None, f"Missing template for pattern: {pattern}"
        assert len(template) > 0, f"Empty template for pattern: {pattern}"

    def test_total_pattern_count(self) -> None:
        assert len(TEMPLATES) == 19, f"Expected 19 patterns, got {len(TEMPLATES)}"


class TestListPatterns:
    """Verify list_patterns returns correct metadata."""

    def test_returns_15_entries(self) -> None:
        patterns = list_patterns()
        assert len(patterns) == 19, f"Expected 19 entries, got {len(patterns)}"

    def test_each_entry_has_required_fields(self) -> None:
        for entry in list_patterns():
            assert "pattern" in entry
            assert "archetype" in entry
            assert "frameworks" in entry
            assert "lines" in entry

    def test_all_entries_include_python_framework(self) -> None:
        for entry in list_patterns():
            assert "python" in entry["frameworks"], (
                f"Pattern {entry['pattern']} missing 'python' in frameworks"
            )

    def test_framework_metadata_matches(self) -> None:
        patterns = {p["pattern"]: p for p in list_patterns()}
        assert "langgraph" in patterns["circuit_breaker"]["frameworks"]
        assert "crewai" in patterns["supervisor_worker"]["frameworks"]
        assert "openai_agents" in patterns["handoff_pattern"]["frameworks"]


class TestFrameworkVariants:
    """Verify framework-specific templates exist and are valid."""

    @pytest.mark.parametrize("key", sorted(EXPECTED_FRAMEWORK_VARIANTS))
    def test_framework_variant_exists(self, key: str) -> None:
        assert key in FRAMEWORK_TEMPLATES, f"Missing framework variant: {key}"
        assert len(FRAMEWORK_TEMPLATES[key]) > 0

    def test_total_framework_variant_count(self) -> None:
        assert len(FRAMEWORK_TEMPLATES) == len(EXPECTED_FRAMEWORK_VARIANTS), (
            f"Expected {len(EXPECTED_FRAMEWORK_VARIANTS)} framework variants, "
            f"got {len(FRAMEWORK_TEMPLATES)}"
        )

    def test_get_template_returns_framework_variant(self) -> None:
        template = get_template("circuit_breaker", framework="langgraph")
        assert template is not None
        assert "langgraph" in template.lower() or "StateGraph" in template

    def test_unknown_framework_falls_back_to_python(self) -> None:
        python_template = get_template("circuit_breaker", framework="python")
        fallback_template = get_template("circuit_breaker", framework="nonexistent_framework")
        assert fallback_template == python_template

    def test_unavailable_variant_falls_back_to_python(self) -> None:
        # dead_letter_queue has no langgraph variant
        python_template = get_template("dead_letter_queue", framework="python")
        fallback_template = get_template("dead_letter_queue", framework="langgraph")
        assert fallback_template == python_template


class TestTemplateQuality:
    """Verify each template is valid Python and not trivially short."""

    @pytest.mark.parametrize("pattern", ALL_PATTERNS)
    def test_template_is_valid_python(self, pattern: str) -> None:
        template = get_template(pattern)
        assert template is not None
        # compile() raises SyntaxError if invalid
        compile(template, f"{pattern}.py", "exec")

    @pytest.mark.parametrize("pattern", ALL_PATTERNS)
    def test_template_is_substantial(self, pattern: str) -> None:
        template = get_template(pattern)
        assert template is not None
        line_count = template.count("\n")
        assert line_count > 30, (
            f"Template {pattern} has only {line_count} lines (expected >30)"
        )

    @pytest.mark.parametrize("key", sorted(EXPECTED_FRAMEWORK_VARIANTS))
    def test_framework_template_is_valid_python(self, key: str) -> None:
        template = FRAMEWORK_TEMPLATES[key]
        compile(template, f"{key}.py", "exec")

    @pytest.mark.parametrize("key", sorted(EXPECTED_FRAMEWORK_VARIANTS))
    def test_framework_template_is_substantial(self, key: str) -> None:
        template = FRAMEWORK_TEMPLATES[key]
        line_count = template.count("\n")
        assert line_count > 30, (
            f"Framework template {key} has only {line_count} lines (expected >30)"
        )


class TestNewPatternsHaveScaffoldHeader:
    """New templates should have LORE SCAFFOLD header comment."""

    NEW_PATTERNS = [
        "handoff_pattern",
        "model_routing",
        "three_layer_memory",
        "sentinel_observability",
        "librarian_retrieval",
        "scout_discovery",
        "cartographer_knowledge_graph",
        "timekeeper_scheduling",
        "architect_system_design",
        "alchemist_prompt_routing",
    ]

    @pytest.mark.parametrize("pattern", NEW_PATTERNS)
    def test_has_scaffold_header(self, pattern: str) -> None:
        template = get_template(pattern)
        assert template is not None
        assert f"# LORE SCAFFOLD: {pattern}" in template

    @pytest.mark.parametrize("pattern", NEW_PATTERNS)
    def test_has_future_annotations(self, pattern: str) -> None:
        template = get_template(pattern)
        assert template is not None
        assert "from __future__ import annotations" in template


class TestBackwardCompatibility:
    """Original 5 patterns should still work exactly as before."""

    ORIGINAL_PATTERNS = [
        "circuit_breaker",
        "dead_letter_queue",
        "reviewer_loop",
        "supervisor_worker",
        "tool_health_monitor",
    ]

    @pytest.mark.parametrize("pattern", ORIGINAL_PATTERNS)
    def test_original_pattern_still_exists(self, pattern: str) -> None:
        template = get_template(pattern)
        assert template is not None
        assert len(template) > 0

    def test_get_template_default_framework_is_python(self) -> None:
        """get_template(pattern) without framework should return python version."""
        for pattern in self.ORIGINAL_PATTERNS:
            default = get_template(pattern)
            explicit = get_template(pattern, framework="python")
            assert default == explicit
