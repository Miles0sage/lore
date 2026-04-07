"""Autonomous evolution daemon — analyzes audit history and proposes new patterns."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

from .config import get_audit_dir, get_telemetry_dir
from .scaffold import TEMPLATES


def _load_audit_files(audit_dir: Path) -> list[dict]:
    """Load all JSON audit files from the audit directory."""
    if not audit_dir.exists():
        return []
    audits = []
    for path in sorted(audit_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            audits.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return audits


def _extract_gap_patterns(audits: list[dict]) -> Counter:
    """Extract pattern names from lore_actions across all audits."""
    counts: Counter = Counter()
    for audit in audits:
        for action in audit.get("lore_actions", []):
            if action.get("type") == "scaffold":
                pattern = action.get("pattern", "").strip()
                if pattern:
                    counts[pattern] += 1
    return counts


def _existing_template_names(template_dir: Path) -> set[str]:
    """Return the set of pattern names that already have templates."""
    names: set[str] = set(TEMPLATES.keys())
    if template_dir.exists():
        for path in template_dir.glob("*.py"):
            names.add(path.stem)
    return names


def _propose_stub(pattern: str, count: int) -> dict:
    """Build a proposed scaffold stub descriptor for a missing pattern."""
    label = pattern.replace("_", " ").title()
    return {
        "pattern": pattern,
        "frequency": count,
        "stub_filename": f"{pattern}.py",
        "description": f"Proposed scaffold stub for '{label}' (flagged {count}x in audits).",
        "stub_content": _minimal_stub(pattern),
    }


def _minimal_stub(pattern: str) -> str:
    """Generate a minimal scaffold stub for a new pattern."""
    label = pattern.replace("_", " ").title()
    return f'''"""
LORE Scaffold — {label}

Auto-proposed by `lore evolve` based on recurring audit gaps.
Replace this stub with a production-ready implementation.
"""

from __future__ import annotations


def build_{pattern}(config: dict | None = None) -> dict:
    """Entry point for the {label} pattern.

    Args:
        config: Optional configuration dict.

    Returns:
        A dict describing the initialized pattern state.
    """
    cfg = config or {{}}
    return {{"pattern": "{pattern}", "config": cfg, "status": "stub"}}
'''


def _write_evolution_report(result: dict, evolution_dir: Path) -> Path:
    """Write the markdown evolution report and return its path."""
    evolution_dir.mkdir(parents=True, exist_ok=True)
    date_str = time.strftime("%Y-%m-%d")
    report_path = evolution_dir / f"{date_str}.md"

    lines = [
        f"# Lore Evolution Report — {date_str}",
        "",
        "## Summary",
        "",
        f"- Audits analyzed: **{result['audits_analyzed']}**",
        f"- Top gap patterns found: **{len(result['top_gaps'])}**",
        f"- New patterns proposed: **{len(result['proposed_patterns'])}**",
        "",
        "## Top Gaps (frequency across audits)",
        "",
    ]

    if result["top_gaps"]:
        for pattern, count in result["top_gaps"]:
            already = "(already has template)" if pattern in result.get("covered_patterns", set()) else "(no template)"
            lines.append(f"- `{pattern}` — {count}x {already}")
    else:
        lines.append("_No recurring gaps found._")

    lines += ["", "## Proposed New Scaffolds", ""]

    if result["proposed_patterns"]:
        for stub in result["proposed_patterns"]:
            lines.append(f"### `{stub['pattern']}` (flagged {stub['frequency']}x)")
            lines.append("")
            lines.append(stub["description"])
            lines.append("")
            lines.append("```python")
            lines.append(stub["stub_content"].strip())
            lines.append("```")
            lines.append("")
    else:
        lines.append("_No new patterns proposed (all recurring gaps already have templates)._")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_evolution(
    audit_dir: Path | None = None,
    template_dir: Path | None = None,
    *,
    min_frequency: int = 2,
) -> dict:
    """Analyze audit history and propose new scaffold patterns.

    Args:
        audit_dir: Directory containing JSON audit files. Defaults to .lore/audits.
        template_dir: Directory containing existing scaffold templates. Defaults to lore/templates.
        min_frequency: Minimum times a pattern must appear to be proposed. Default: 2.

    Returns:
        Dict with keys: audits_analyzed, top_gaps, proposed_patterns, report_path.
    """
    resolved_audit_dir = audit_dir or get_audit_dir()
    from .scaffold import TEMPLATES_DIR
    resolved_template_dir = template_dir or TEMPLATES_DIR

    audits = _load_audit_files(resolved_audit_dir)
    gap_counts = _extract_gap_patterns(audits)
    existing = _existing_template_names(resolved_template_dir)

    top_gaps = gap_counts.most_common()
    proposed = [
        _propose_stub(pattern, count)
        for pattern, count in top_gaps
        if count >= min_frequency and pattern not in existing
    ]

    evolution_dir = get_telemetry_dir() / "evolution"
    report_path = _write_evolution_report(
        {
            "audits_analyzed": len(audits),
            "top_gaps": top_gaps,
            "proposed_patterns": proposed,
            "covered_patterns": existing,
        },
        evolution_dir,
    )

    return {
        "audits_analyzed": len(audits),
        "top_gaps": top_gaps,
        "proposed_patterns": proposed,
        "report_path": str(report_path),
    }
