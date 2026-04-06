"""
LORE Claude Code Integration — Generate native Claude Code artifacts from Codex patterns.

Transforms archetypes and wiki knowledge into:
- CLAUDE.md imperative rules blocks
- PreToolUse hook scripts (Python, reads JSON from stdin)
- Claude Code skill files (YAML frontmatter + markdown)
- MCP config snippets

Usage (CLI):
    lore install --dir /my/project --patterns circuit_breaker,dead_letter_queue
    lore rules --patterns circuit_breaker

Usage (Python):
    from lore.claude_code import generate_claude_md_rules, install_rules
"""

from __future__ import annotations

import ast
import json
import textwrap
from pathlib import Path
from typing import Any

from . import archetypes, teaching


# ── Imperative rule sets per pattern ─────────────────────────────────────────

_PATTERN_RULES: dict[str, list[str]] = {
    "circuit_breaker": [
        "ALWAYS wrap every external API call, LLM call, and HTTP request in a circuit breaker",
        "NEVER allow infinite retry loops — set max_retries on every HTTP client and LLM call",
        "MUST implement three states: CLOSED (pass-through), OPEN (fail fast), HALF_OPEN (probe)",
        "ALWAYS configure a failure_threshold (recommended: 3 failures) before opening the circuit",
        "NEVER silently degrade — when the circuit opens, raise a clear CircuitOpenError",
        "ALWAYS set a cooldown/reset_timeout so the circuit can recover after failures pass",
        "NEVER retry on the same failing endpoint without a backoff — use exponential delay",
    ],
    "dead_letter_queue": [
        "ALWAYS capture failed tasks in a dead letter queue — never silently drop failures",
        "MUST record: error type, attempt count, original payload, and timestamp on every DLQ entry",
        "NEVER destroy a failed message — seal it in the archive with full context",
        "ALWAYS implement a DLQ consumer that can replay or audit archived failures",
        "MUST cap the DLQ size or implement rotation — an unbounded archive is a memory leak",
        "NEVER exceed max_retries without routing to the DLQ — define a hard ceiling",
    ],
    "reviewer_loop": [
        "ALWAYS implement a review pass after every generated output — never ship the first draft",
        "MUST define a quality threshold score; outputs below threshold MUST be regenerated",
        "NEVER allow more than N iterations without escalating to a human — cap all review loops",
        "ALWAYS use a different model or temperature for the reviewer than the creator",
        "MUST return structured critique with the score so the creator can improve specifically",
        "NEVER skip the reviewer when token budget is tight — quality gates exist for production safety",
    ],
    "sentinel_observability": [
        "ALWAYS instrument every agent action with the four golden signals: error rate, latency, token consumption, semantic validation score",
        "NEVER deploy an agent without observability — systems without The Sentinel fail 76% of the time in production",
        "MUST emit structured logs (JSON) from every agent decision point",
        "ALWAYS track token spend per task type — runaway token consumption is a production incident",
        "MUST wire The Sentinel to signal The Breaker when error rates exceed thresholds",
        "NEVER suppress errors to keep agents running — surface them and let The Breaker decide",
        "ALWAYS alert when the dead letter queue depth exceeds a configured ceiling",
    ],
}

# Aliases: underscore keys map to hyphenated archetype IDs
_PATTERN_ALIASES: dict[str, str] = {
    "circuit_breaker": "circuit-breaker",
    "dead_letter_queue": "dead-letter-queue",
    "reviewer_loop": "reviewer-loop",
    "sentinel_observability": "sentinel",
    "three_layer_memory": "three-layer-memory",
    "supervisor_worker": "supervisor-worker",
    "tool_health_monitoring": "tool-health-monitoring",
    "model_routing": "model-routing",
    "handoff_pattern": "handoff-pattern",
    "librarian": "librarian",
    "scout": "scout",
    "cartographer": "cartographer",
    "alchemist": "alchemist",
    "timekeeper": "timekeeper",
    "architect": "architect",
}

# Patterns that have custom hook support
_HOOKABLE_PATTERNS = {
    "circuit_breaker",
    "dead_letter_queue",
    "sentinel_observability",
    "reviewer_loop",
}


# ── Public API ────────────────────────────────────────────────────────────────


def generate_claude_md_rules(patterns: list[str] | None = None) -> str:
    """Generate a CLAUDE.md rules block from Lore patterns.

    Args:
        patterns: List of pattern IDs (underscore or hyphen form), or None for all.

    Returns:
        Full CLAUDE.md rules block as a string.
    """
    if patterns is None:
        patterns = list(_PATTERN_RULES.keys())

    sections: list[str] = [
        "# LORE — AI Agent Reliability Rules",
        "",
        "These rules are generated from the LORE Codex (github.com/Miles0sage/lore).",
        "Each pattern is a battle-tested reliability primitive. Follow them exactly.",
        "",
    ]

    for pattern in patterns:
        # Normalize to underscore form for lookup
        normalized = pattern.replace("-", "_")
        arch_id = _PATTERN_ALIASES.get(normalized, pattern.replace("_", "-"))
        arch = archetypes.get_archetype(arch_id)

        rule_list = _PATTERN_RULES.get(normalized)

        # If no curated rules, generate from archetype data
        if rule_list is None and arch is not None:
            rule_list = _rules_from_archetype(arch)

        if rule_list is None:
            # Try teaching module as last resort
            lesson = teaching.compile_lesson(arch_id, format="claude_md")
            if "error" not in lesson:
                sections.append(lesson["content"])
                sections.append("")
            continue

        archetype_name = arch["name"] if arch else pattern
        archetype_title = arch.get("title", "") if arch else ""
        header = f"## {archetype_name} ({archetype_title})" if archetype_title else f"## {archetype_name}"

        sections.append(header)
        sections.append("")
        if arch:
            sections.append(f"**Pattern:** `{arch_id}`  ")
            sections.append(f"**Power:** {arch.get('power', '')}  ")
            sections.append(f"**Known Weakness:** {arch.get('weakness', '')}  ")
            sections.append("")
        for rule in rule_list:
            # Ensure rules start with an imperative directive keyword
            sections.append(f"- {rule}")
        sections.append("")

    return "\n".join(sections)


def generate_hook_script(pattern: str) -> dict[str, Any]:
    """Generate a Claude Code PreToolUse hook script that enforces a pattern.

    Args:
        pattern: Pattern ID (e.g. "circuit_breaker").

    Returns:
        Dict with hook_type, matcher, script (Python string), and pattern.
    """
    normalized = pattern.replace("-", "_")

    if normalized not in _HOOKABLE_PATTERNS:
        return {
            "error": (
                f"No hook template for pattern '{pattern}'. "
                f"Supported: {', '.join(sorted(_HOOKABLE_PATTERNS))}"
            ),
            "pattern": pattern,
            "supported_patterns": sorted(_HOOKABLE_PATTERNS),
        }

    script = _HOOK_SCRIPTS[normalized]

    return {
        "hook_type": "PreToolUse",
        "matcher": "Bash|Write|Edit",
        "script": script,
        "pattern": normalized,
    }


def generate_skill_file(pattern: str) -> str:
    """Generate a Claude Code skill file (YAML frontmatter + markdown) for a pattern.

    Args:
        pattern: Pattern ID (e.g. "circuit_breaker" or "circuit-breaker").

    Returns:
        Full skill file content string.
    """
    normalized = pattern.replace("-", "_")
    arch_id = _PATTERN_ALIASES.get(normalized, pattern.replace("_", "-"))
    arch = archetypes.get_archetype(arch_id)

    slug = arch_id
    name = arch["name"] if arch else pattern
    title = arch.get("title", pattern) if arch else pattern
    description = f"{name} — {title}" if title != pattern else name

    rule_list = _PATTERN_RULES.get(normalized, [])
    if not rule_list and arch:
        rule_list = _rules_from_archetype(arch)

    lines: list[str] = [
        "---",
        f"name: {slug}",
        f'description: "{description}"',
        f"pattern: {arch_id}",
        "---",
        "",
        f"# {name}: {title}" if title != pattern else f"# {name}",
        "",
    ]

    if arch:
        lines.append(f"**Pattern:** `{arch_id}`")
        lines.append(f"**Power:** {arch.get('power', '')}")
        lines.append(f"**Weakness:** {arch.get('weakness', '')}")
        lines.append("")
        lines.append("## Lore")
        lines.append("")
        lines.append(arch.get("lore", ""))
        lines.append("")

    if rule_list:
        lines.append("## Rules (CLAUDE.md Style)")
        lines.append("")
        lines.append("When implementing this pattern:")
        lines.append("")
        for i, rule in enumerate(rule_list, 1):
            lines.append(f"{i}. {rule}")
        lines.append("")

    # Add scaffold hint
    scaffold_key = normalized
    lines.append("## Scaffold")
    lines.append("")
    lines.append(
        f"Run `lore scaffold {scaffold_key}` to generate production-ready code for this pattern."
    )
    lines.append("")

    return "\n".join(lines)


def generate_mcp_config() -> dict[str, Any]:
    """Return the MCP config snippet for adding Lore to Claude Code.

    Returns:
        Dict with the mcpServers configuration block.
    """
    return {
        "mcpServers": {
            "lore": {
                "command": "python3",
                "args": ["-m", "lore.server"],
            }
        }
    }


def install_rules(
    output_dir: str,
    patterns: list[str] | None = None,
) -> dict[str, Any]:
    """Install Lore rules, hooks, and skills into a project directory.

    Writes:
    - {output_dir}/CLAUDE.md (appended if exists)
    - {output_dir}/.claude/hooks/lore_{pattern}.py for each pattern
    - {output_dir}/.claude/skills/{pattern}.md for each pattern

    Args:
        output_dir: Target project directory.
        patterns: Pattern IDs to install, or None for all hookable patterns.

    Returns:
        Summary dict of what was written.
    """
    root = Path(output_dir)
    hooks_dir = root / ".claude" / "hooks"
    skills_dir = root / ".claude" / "skills"

    hooks_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Determine which patterns to install
    if patterns is None:
        rule_patterns = list(_PATTERN_RULES.keys())
    else:
        rule_patterns = [p.replace("-", "_") for p in patterns]

    # 1. CLAUDE.md rules
    rules_content = generate_claude_md_rules(rule_patterns)
    claude_md_path = root / "CLAUDE.md"
    if claude_md_path.exists():
        existing = claude_md_path.read_text(encoding="utf-8")
        marker = "<!-- lore-rules-start -->"
        if marker not in existing:
            updated = existing.rstrip() + f"\n\n{marker}\n\n" + rules_content
        else:
            # Already installed — replace between markers
            end_marker = "<!-- lore-rules-end -->"
            before = existing.split(marker)[0]
            updated = before + f"{marker}\n\n" + rules_content + f"\n{end_marker}"
        claude_md_path.write_text(updated, encoding="utf-8")
    else:
        claude_md_path.write_text(
            f"<!-- lore-rules-start -->\n\n{rules_content}\n<!-- lore-rules-end -->",
            encoding="utf-8",
        )

    written_hooks: list[str] = []
    written_skills: list[str] = []
    skipped_hooks: list[str] = []

    # 2. Hook scripts
    for pattern in rule_patterns:
        hook_result = generate_hook_script(pattern)
        if "error" in hook_result:
            skipped_hooks.append(pattern)
            continue
        hook_path = hooks_dir / f"lore_{pattern}.py"
        hook_path.write_text(hook_result["script"], encoding="utf-8")
        hook_path.chmod(0o755)
        written_hooks.append(str(hook_path))

    # 3. Skill files
    for pattern in rule_patterns:
        skill_content = generate_skill_file(pattern)
        arch_id = _PATTERN_ALIASES.get(pattern, pattern.replace("_", "-"))
        skill_path = skills_dir / f"{arch_id}.md"
        skill_path.write_text(skill_content, encoding="utf-8")
        written_skills.append(str(skill_path))

    return {
        "claude_md": str(claude_md_path),
        "hooks_written": written_hooks,
        "skills_written": written_skills,
        "hooks_skipped": skipped_hooks,
        "patterns_installed": rule_patterns,
        "summary": (
            f"Installed {len(rule_patterns)} pattern(s): "
            f"CLAUDE.md rules + {len(written_hooks)} hooks + {len(written_skills)} skills"
        ),
    }


# ── Internal helpers ──────────────────────────────────────────────────────────


def _rules_from_archetype(arch: dict) -> list[str]:
    """Derive basic imperative rules from archetype data when no curated set exists."""
    name = arch.get("name", "This pattern")
    power = arch.get("power", "")
    weakness = arch.get("weakness", "")
    rules = []
    if power:
        rules.append(f"ALWAYS leverage {name}'s strength: {power}")
    if weakness:
        rules.append(f"NEVER ignore {name}'s known weakness: {weakness} — mitigate it explicitly")
    rules.append(f"MUST document why {name} was chosen in the system design")
    return rules


# ── Hook script templates ─────────────────────────────────────────────────────

_HOOK_SCRIPTS: dict[str, str] = {
    "circuit_breaker": textwrap.dedent('''\
        #!/usr/bin/env python3
        """
        LORE Hook: Circuit Breaker Enforcer (circuit_breaker)

        Warns when external API/LLM calls are written without a circuit breaker.
        Reads Claude Code hook JSON from stdin. Exit 0 = proceed, 1 = warn.

        Install in ~/.claude/settings.json:
        {
          "hooks": {
            "PreToolUse": [{
              "matcher": "Bash|Write|Edit",
              "hooks": [{"type": "command", "command": "python3 .claude/hooks/lore_circuit_breaker.py"}]
            }]
          }
        }
        """

        import json
        import re
        import sys

        NEEDS_CIRCUIT_BREAKER = [
            r"requests\\.get|requests\\.post|httpx\\.get|httpx\\.post|httpx\\.AsyncClient",
            r"aiohttp\\.ClientSession",
            r"openai\\..*\\.create|anthropic\\..*\\.create",
            r"while True.*retry|for.*retry.*range",
            r"urllib\\.request\\.urlopen",
        ]

        HAS_CIRCUIT_BREAKER = [
            r"CircuitBreaker|circuit_breaker",
            r"failure_threshold",
            r"max_retries\\s*=\\s*[1-9]",
            r"CLOSED.*OPEN|OPEN.*HALF_OPEN",
        ]

        INFINITE_LOOP_RISK = [
            r"while True",
            r"while not done",
            r"while.*running\\b",
        ]


        def check(code: str) -> list[str]:
            warnings = []
            has_breaker = any(re.search(p, code, re.IGNORECASE) for p in HAS_CIRCUIT_BREAKER)
            needs_breaker = any(re.search(p, code, re.IGNORECASE) for p in NEEDS_CIRCUIT_BREAKER)
            has_infinite = any(re.search(p, code, re.IGNORECASE) for p in INFINITE_LOOP_RISK)

            if needs_breaker and not has_breaker:
                warnings.append(
                    "LORE [The Breaker]: External API/LLM calls detected without a circuit breaker. "
                    "Systems without The Breaker experience 76%% failure rates in production. "
                    "ALWAYS wrap calls with CircuitBreaker(max_retries=3). "
                    "Fix: lore scaffold circuit_breaker"
                )
            if has_infinite and not has_breaker:
                warnings.append(
                    "LORE [The Breaker]: Infinite loop without failure threshold. "
                    "Add max_retries or CircuitBreaker to prevent runaway token spend. "
                    "Fix: lore scaffold circuit_breaker"
                )
            return warnings


        def main() -> None:
            try:
                data = json.load(sys.stdin)
            except Exception:
                sys.exit(0)

            tool_name = data.get("tool_name", "")
            tool_input = data.get("tool_input", {})

            if tool_name not in ("Bash", "Write", "Edit"):
                sys.exit(0)

            code = ""
            if tool_name == "Bash":
                code = tool_input.get("command", "")
            elif tool_name in ("Write", "Edit"):
                code = tool_input.get("content", "") + tool_input.get("new_string", "")
                # Only check Python files
                file_path = tool_input.get("file_path", "")
                if file_path and not file_path.endswith(".py"):
                    sys.exit(0)

            if not code or len(code) < 80:
                sys.exit(0)

            warnings = check(code)
            if warnings:
                print("\\n".join(warnings), file=sys.stderr)
                sys.exit(1)
            sys.exit(0)


        if __name__ == "__main__":
            main()
        '''),

    "dead_letter_queue": textwrap.dedent('''\
        #!/usr/bin/env python3
        """
        LORE Hook: Dead Letter Queue Enforcer (dead_letter_queue)

        Warns when batch task processing is written without a dead letter queue.
        Reads Claude Code hook JSON from stdin. Exit 0 = proceed, 1 = warn.

        Install in ~/.claude/settings.json:
        {
          "hooks": {
            "PreToolUse": [{
              "matcher": "Bash|Write|Edit",
              "hooks": [{"type": "command", "command": "python3 .claude/hooks/lore_dead_letter_queue.py"}]
            }]
          }
        }
        """

        import json
        import re
        import sys

        NEEDS_DLQ = [
            r"for.*task.*in.*tasks",
            r"asyncio\\.gather.*tasks",
            r"ThreadPoolExecutor|ProcessPoolExecutor",
            r"map\\(.*lambda",
        ]

        HAS_DLQ = [
            r"dead_letter|dlq|DeadLetter",
            r"ErrorEnvelope|error_envelope",
            r"failed_tasks|failures\\.append",
            r"max_retries.*[3-9]",
        ]


        def check(code: str) -> list[str]:
            warnings = []
            has_dlq = any(re.search(p, code, re.IGNORECASE) for p in HAS_DLQ)
            needs_dlq = any(re.search(p, code, re.IGNORECASE) for p in NEEDS_DLQ)

            if needs_dlq and not has_dlq:
                warnings.append(
                    "LORE [The Archivist]: Batch task processing without a dead letter queue. "
                    "Failed tasks will be silently dropped without DLQ. "
                    "ALWAYS capture failures in a dead letter queue with error context. "
                    "Fix: lore scaffold dead_letter_queue"
                )
            return warnings


        def main() -> None:
            try:
                data = json.load(sys.stdin)
            except Exception:
                sys.exit(0)

            tool_name = data.get("tool_name", "")
            tool_input = data.get("tool_input", {})

            if tool_name not in ("Bash", "Write", "Edit"):
                sys.exit(0)

            code = ""
            if tool_name == "Bash":
                code = tool_input.get("command", "")
            elif tool_name in ("Write", "Edit"):
                code = tool_input.get("content", "") + tool_input.get("new_string", "")
                file_path = tool_input.get("file_path", "")
                if file_path and not file_path.endswith(".py"):
                    sys.exit(0)

            if not code or len(code) < 80:
                sys.exit(0)

            warnings = check(code)
            if warnings:
                print("\\n".join(warnings), file=sys.stderr)
                sys.exit(1)
            sys.exit(0)


        if __name__ == "__main__":
            main()
        '''),

    "sentinel_observability": textwrap.dedent('''\
        #!/usr/bin/env python3
        """
        LORE Hook: Sentinel Observability Enforcer (sentinel_observability)

        Warns when agent code is written without observability instrumentation.
        Reads Claude Code hook JSON from stdin. Exit 0 = proceed, 1 = warn.

        Install in ~/.claude/settings.json:
        {
          "hooks": {
            "PreToolUse": [{
              "matcher": "Bash|Write|Edit",
              "hooks": [{"type": "command", "command": "python3 .claude/hooks/lore_sentinel_observability.py"}]
            }]
          }
        }
        """

        import json
        import re
        import sys

        # Patterns that indicate agent behavior needing observability
        NEEDS_OBSERVABILITY = [
            r"def.*agent|class.*Agent",
            r"dispatch|execute_task|run_task",
            r"llm\\.complete|client\\.chat|openai\\..*create",
        ]

        HAS_OBSERVABILITY = [
            r"logging\\.|logger\\.",
            r"langfuse|agentops|helicone|langsmith|arize",
            r"token_count|tokens_used|usage\\[",
            r"error_rate|latency|span\\.set",
        ]


        def check(code: str) -> list[str]:
            warnings = []
            has_obs = any(re.search(p, code, re.IGNORECASE) for p in HAS_OBSERVABILITY)
            needs_obs = any(re.search(p, code, re.IGNORECASE) for p in NEEDS_OBSERVABILITY)

            if needs_obs and not has_obs:
                warnings.append(
                    "LORE [The Sentinel]: Agent code detected without observability instrumentation. "
                    "Systems without The Sentinel experience 76%% failure rates in production. "
                    "ALWAYS instrument with logging + token tracking + error rates. "
                    "Fix: lore scaffold sentinel_observability"
                )
            return warnings


        def main() -> None:
            try:
                data = json.load(sys.stdin)
            except Exception:
                sys.exit(0)

            tool_name = data.get("tool_name", "")
            tool_input = data.get("tool_input", {})

            if tool_name not in ("Bash", "Write", "Edit"):
                sys.exit(0)

            code = ""
            if tool_name == "Bash":
                code = tool_input.get("command", "")
            elif tool_name in ("Write", "Edit"):
                code = tool_input.get("content", "") + tool_input.get("new_string", "")
                file_path = tool_input.get("file_path", "")
                if file_path and not file_path.endswith(".py"):
                    sys.exit(0)

            if not code or len(code) < 80:
                sys.exit(0)

            warnings = check(code)
            if warnings:
                print("\\n".join(warnings), file=sys.stderr)
                sys.exit(1)
            sys.exit(0)


        if __name__ == "__main__":
            main()
        '''),

    "reviewer_loop": textwrap.dedent('''\
        #!/usr/bin/env python3
        """
        LORE Hook: Reviewer Loop Enforcer (reviewer_loop)

        Warns when LLM output generation is written without a review/quality gate.
        Reads Claude Code hook JSON from stdin. Exit 0 = proceed, 1 = warn.

        Install in ~/.claude/settings.json:
        {
          "hooks": {
            "PreToolUse": [{
              "matcher": "Bash|Write|Edit",
              "hooks": [{"type": "command", "command": "python3 .claude/hooks/lore_reviewer_loop.py"}]
            }]
          }
        }
        """

        import json
        import re
        import sys

        NEEDS_REVIEWER = [
            r"generate|draft|write.*content|produce.*output",
            r"llm\\.complete|client\\.chat|openai\\..*create",
            r"return.*response|return.*output|return.*result",
        ]

        HAS_REVIEWER = [
            r"review|evaluate|score|quality",
            r"threshold|min_score|quality_gate",
            r"critic|judge|validator",
            r"max_iterations|max_rounds",
        ]


        def check(code: str) -> list[str]:
            warnings = []
            has_reviewer = any(re.search(p, code, re.IGNORECASE) for p in HAS_REVIEWER)
            needs_reviewer = any(re.search(p, code, re.IGNORECASE) for p in NEEDS_REVIEWER)

            if needs_reviewer and not has_reviewer:
                warnings.append(
                    "LORE [The Council]: LLM output generation without a reviewer loop. "
                    "ALWAYS add a quality gate: score output, regenerate if below threshold. "
                    "NEVER ship the first draft without review. "
                    "Fix: lore scaffold reviewer_loop"
                )
            return warnings


        def main() -> None:
            try:
                data = json.load(sys.stdin)
            except Exception:
                sys.exit(0)

            tool_name = data.get("tool_name", "")
            tool_input = data.get("tool_input", {})

            if tool_name not in ("Bash", "Write", "Edit"):
                sys.exit(0)

            code = ""
            if tool_name == "Bash":
                code = tool_input.get("command", "")
            elif tool_name in ("Write", "Edit"):
                code = tool_input.get("content", "") + tool_input.get("new_string", "")
                file_path = tool_input.get("file_path", "")
                if file_path and not file_path.endswith(".py"):
                    sys.exit(0)

            if not code or len(code) < 80:
                sys.exit(0)

            warnings = check(code)
            if warnings:
                print("\\n".join(warnings), file=sys.stderr)
                sys.exit(1)
            sys.exit(0)


        if __name__ == "__main__":
            main()
        '''),
}
