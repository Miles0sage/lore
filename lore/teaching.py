"""
LORE Teaching — Compile Codex knowledge into injectable context packages.

Transforms archetypes, wiki articles, and scaffold templates into formats
that other agents can consume directly: CLAUDE.md rules, system prompts,
skill files, and MCP tool descriptions.
"""

from __future__ import annotations

from . import archetypes, search, scaffold


def compile_lesson(pattern: str, format: str = "claude_md") -> dict:
    """Compile a pattern into an injectable context package.

    Args:
        pattern: Pattern name or ID (e.g. "circuit-breaker", "reviewer-loop").
        format: One of "claude_md", "system_prompt", "skill", "mcp_description".

    Returns:
        Dict with pattern, format, content, archetype name, scaffold flag, word count.
    """
    valid_formats = {"claude_md", "system_prompt", "skill", "mcp_description"}
    if format not in valid_formats:
        return {
            "error": f"Unknown format: {format}. Valid: {', '.join(sorted(valid_formats))}",
            "pattern": pattern,
            "format": format,
        }

    # Gather components
    arch = archetypes.get_archetype(pattern)
    article = _find_article(pattern)
    scaffold_code = _find_scaffold(pattern)

    if arch is None and article is None:
        return {
            "error": f"Pattern '{pattern}' not found. No archetype or article matches.",
            "pattern": pattern,
            "format": format,
            "content": "",
            "archetype": None,
            "has_scaffold": False,
            "word_count": 0,
        }

    archetype_name = arch["name"] if arch else None

    # Build content for the requested format
    if format == "claude_md":
        content = _build_claude_md(pattern, arch, article, scaffold_code)
    elif format == "system_prompt":
        content = _build_system_prompt(pattern, arch, article, scaffold_code)
    elif format == "skill":
        content = _build_skill(pattern, arch, article, scaffold_code)
    elif format == "mcp_description":
        content = _build_mcp_description(pattern, arch, article, scaffold_code)
    else:
        content = ""

    return {
        "pattern": pattern,
        "format": format,
        "content": content,
        "archetype": archetype_name,
        "has_scaffold": scaffold_code is not None,
        "word_count": len(content.split()),
    }


def compile_fleet_brief(changed_patterns: list[str] | None = None) -> dict:
    """Compile lessons for changed (or all teachable) patterns.

    Args:
        changed_patterns: Explicit list of pattern IDs, or None to auto-detect.

    Returns:
        Dict with lessons list, summary string, and agent count.
    """
    if changed_patterns is None:
        # Fall back to all teachable patterns
        teachable = list_teachable_patterns()
        changed_patterns = [t["pattern_id"] for t in teachable]

    lessons = []
    for pid in changed_patterns:
        lesson = compile_lesson(pid, format="claude_md")
        if "error" not in lesson:
            lessons.append(lesson)

    summary_parts = [f"{len(lessons)} pattern(s) compiled"]
    if lessons:
        names = [l["archetype"] or l["pattern"] for l in lessons]
        summary_parts.append(f"patterns: {', '.join(names)}")

    return {
        "lessons": lessons,
        "summary": ". ".join(summary_parts),
        "agent_count": len(lessons),
    }


def list_teachable_patterns() -> list[dict]:
    """Return all patterns with enough content to teach (archetype + article minimum)."""
    results = []

    all_archetypes = archetypes.list_archetypes()
    all_articles = search.list_articles()
    article_ids = {a["id"] for a in all_articles}
    scaffold_patterns = set(scaffold.list_patterns())

    for arch_entry in all_archetypes:
        pid = arch_entry["pattern_id"]

        # Check if there is a matching article (fuzzy: pid substring in article id or vice versa)
        has_article = _has_matching_article(pid, article_ids)

        # Normalize scaffold key (archetypes use hyphens, scaffolds use underscores)
        scaffold_key = pid.replace("-", "_")
        has_scaffold = scaffold_key in scaffold_patterns

        results.append({
            "pattern_id": pid,
            "name": arch_entry["name"],
            "has_archetype": True,
            "has_article": has_article,
            "has_scaffold": has_scaffold,
        })

    return results


# ── Internal helpers ──────────────────────────────────────────────────────────


def _find_article(pattern: str) -> dict | None:
    """Try to find a wiki article matching the pattern."""
    # Direct ID lookup
    article = search.read_article(pattern)
    if article:
        return article
    # Try underscore variant
    article = search.read_article(pattern.replace("-", "_"))
    if article:
        return article
    # Try hyphen variant
    article = search.read_article(pattern.replace("_", "-"))
    if article:
        return article
    # Search as last resort — but only accept high-confidence matches
    results = search.search(pattern, limit=1)
    if results and results[0].get("score", 0) > 5.0:
        return search.read_article(results[0]["id"])
    return None


def _find_scaffold(pattern: str) -> str | None:
    """Try to find a scaffold template matching the pattern."""
    key = pattern.replace("-", "_")
    code = scaffold.get_template(key)
    if code:
        return code
    # Try hyphen-to-underscore
    key = pattern.replace(" ", "_")
    return scaffold.get_template(key)


def _has_matching_article(pattern_id: str, article_ids: set[str]) -> bool:
    """Check if any article ID matches the pattern (fuzzy)."""
    if pattern_id in article_ids:
        return True
    normalized = pattern_id.replace("-", "_")
    if normalized in article_ids:
        return True
    # Substring match
    for aid in article_ids:
        if pattern_id in aid or aid in pattern_id:
            return True
        if normalized in aid or aid in normalized:
            return True
    return False


def _build_claude_md(pattern: str, arch: dict | None, article: dict | None, scaffold_code: str | None) -> str:
    """Build CLAUDE.md-style imperative rules block."""
    lines: list[str] = []
    title = arch["name"] if arch else pattern
    lines.append(f"# {title} Pattern — Rules")
    lines.append("")

    if arch:
        lines.append(f"You are implementing the **{arch['name']}** ({arch.get('title', '')}) pattern.")
        lines.append("")
        lines.append("## Mandatory Behaviors")
        lines.append("")
        # Extract directives from the lore
        lines.append(f"- **Power:** {arch.get('power', 'N/A')}")
        lines.append(f"- **Known Weakness:** {arch.get('weakness', 'N/A')}")
        lines.append("")

    if arch:
        lines.append("## Pattern Description")
        lines.append("")
        lines.append(arch.get("lore", ""))
        lines.append("")

    if article:
        # Extract key sections from the article content
        content = article.get("content", "")
        if content:
            lines.append("## Reference Knowledge")
            lines.append("")
            # Take first 800 chars of article content to keep injection size reasonable
            truncated = content[:800]
            if len(content) > 800:
                truncated += "\n\n_(Truncated. Use lore_read for full article.)_"
            lines.append(truncated)
            lines.append("")

    if scaffold_code:
        lines.append("## Scaffold Available")
        lines.append("")
        lines.append(f"Production-ready code template exists for `{pattern}`. Use `lore_scaffold {pattern.replace('-', '_')}` to generate.")
        lines.append("")

    if arch:
        allies = arch.get("allies", [])
        if allies:
            lines.append("## Related Patterns")
            lines.append("")
            for ally in allies:
                lines.append(f"- {ally}")
            lines.append("")

    return "\n".join(lines)


def _build_system_prompt(pattern: str, arch: dict | None, article: dict | None, scaffold_code: str | None) -> str:
    """Build a ready-to-inject system prompt paragraph."""
    parts: list[str] = []

    if arch:
        parts.append(
            f"You are operating with the {arch['name']} pattern ({arch.get('title', '')}). "
            f"{arch.get('lore', '')} "
            f"Your strength: {arch.get('power', 'N/A')}. "
            f"Your known weakness: {arch.get('weakness', 'N/A')}."
        )
    else:
        parts.append(f"You are implementing the {pattern} pattern.")

    if article:
        content = article.get("content", "")
        # Take a concise excerpt for system prompt injection — strip markdown
        excerpt = content[:400].replace("\n", " ").replace("#", "").strip()
        # Collapse multiple spaces from stripped markdown
        while "  " in excerpt:
            excerpt = excerpt.replace("  ", " ")
        if excerpt:
            parts.append(f"Key context: {excerpt}")

    if scaffold_code:
        parts.append(
            f"A production-ready code scaffold is available for this pattern. "
            f"Use lore_scaffold to generate it."
        )

    return " ".join(parts)


def _build_skill(pattern: str, arch: dict | None, article: dict | None, scaffold_code: str | None) -> str:
    """Build Claude Code skill file format (yaml frontmatter + instruction body)."""
    slug = pattern.replace(" ", "-").lower()
    name = arch["name"] if arch else pattern
    title = arch.get("title", pattern) if arch else pattern

    lines: list[str] = []
    lines.append("---")
    lines.append(f"name: {slug}")
    lines.append(f"description: \"{name} — {title}\"")
    lines.append(f"pattern: {pattern}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {name}")
    lines.append("")

    if arch:
        lines.append(f"**Role:** {arch.get('title', '')}")
        lines.append(f"**Power:** {arch.get('power', '')}")
        lines.append(f"**Weakness:** {arch.get('weakness', '')}")
        lines.append("")
        lines.append("## Lore")
        lines.append("")
        lines.append(arch.get("lore", ""))
        lines.append("")

    if article:
        content = article.get("content", "")
        if content:
            lines.append("## Knowledge Base Excerpt")
            lines.append("")
            truncated = content[:600]
            if len(content) > 600:
                truncated += "\n\n_(Use lore_read for full article.)_"
            lines.append(truncated)
            lines.append("")

    if scaffold_code:
        lines.append("## Scaffold")
        lines.append("")
        lines.append(f"Run `lore_scaffold {pattern.replace('-', '_')}` to generate production code.")
        lines.append("")

    return "\n".join(lines)


def _build_mcp_description(pattern: str, arch: dict | None, article: dict | None, scaffold_code: str | None) -> str:
    """Build MCP tool description text for tool-use agents."""
    parts: list[str] = []

    if arch:
        parts.append(f"{arch['name']} ({arch.get('title', '')})")
        parts.append(arch.get("lore", ""))
        parts.append(f"Strength: {arch.get('power', '')}. Weakness: {arch.get('weakness', '')}.")
    else:
        parts.append(f"Pattern: {pattern}.")

    if article:
        title = article.get("title", "")
        parts.append(f"See Codex article: \"{title}\" for full details.")

    if scaffold_code:
        parts.append(f"Code scaffold available via lore_scaffold {pattern.replace('-', '_')}.")

    return " ".join(parts)
