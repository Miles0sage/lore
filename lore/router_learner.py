"""Self-rewriting router — takes eval reports and updates routing rules.

Uses GPT-5.4 (via dispatch) to analyze the eval report against current
routing rules, then rewrites .lore/routing_rules.json with updated
keyword lists. Safety-gated: max 3 keyword changes per rewrite cycle.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_telemetry_dir
from .eval_loop import build_eval_report
from .routing import _load_routing_rules, _default_routing_rules, log_router_event


_MAX_CHANGES_PER_CYCLE = 3


def _rules_path() -> Path:
    return get_telemetry_dir() / "routing_rules.json"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _backup_rules(path: Path) -> Path | None:
    """Copy current rules to a timestamped backup. Returns backup path or None."""
    if not path.exists():
        return None
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_suffix(f".backup-{ts}.json")
    shutil.copy2(path, backup)
    return backup


def _build_rewrite_prompt(current_rules: dict[str, Any], eval_report: dict[str, Any]) -> str:
    return f"""You are the Lore routing optimizer. Analyze the eval report and current routing rules,
then return ONLY a valid JSON object with updated keyword lists.

CURRENT ROUTING RULES:
{json.dumps(current_rules, indent=2)}

EVAL REPORT:
{json.dumps(eval_report, indent=2)}

CONSTRAINTS:
- You may add, remove, or move at most {_MAX_CHANGES_PER_CYCLE} keywords total.
- light_keywords route to DeepSeek (cheap bulk work).
- escalation_keywords route to GPT-5.4 (high-judgment).
- Everything else routes to GPT-4.1 (standard).
- If the eval shows a task_type failing on a cheap tier, move its keyword to escalation_keywords.
- If the eval shows a task_type succeeding perfectly on an expensive tier, move it down.
- Keep the same JSON schema. Include "changes" array describing what you changed.

Return ONLY valid JSON with this exact schema:
{{
  "light_keywords": ["..."],
  "escalation_keywords": ["..."],
  "task_overrides": {{}},
  "changes": [
    {{"action": "move", "keyword": "...", "from": "...", "to": "...", "reason": "..."}}
  ]
}}"""


def _parse_llm_response(content: str) -> dict[str, Any] | None:
    """Extract JSON from LLM response, tolerating markdown fences."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Strip opening and closing fences
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _apply_safety_gate(
    current_rules: dict[str, Any],
    proposed: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Enforce max changes per cycle. Returns (safe_rules, warnings)."""
    warnings: list[str] = []
    changes = proposed.get("changes", [])

    if len(changes) > _MAX_CHANGES_PER_CYCLE:
        warnings.append(
            f"LLM proposed {len(changes)} changes, capped at {_MAX_CHANGES_PER_CYCLE}"
        )
        changes = changes[:_MAX_CHANGES_PER_CYCLE]

    current_light = set(current_rules.get("light_keywords", []))
    current_escalation = set(current_rules.get("escalation_keywords", []))
    proposed_light = set(proposed.get("light_keywords", []))
    proposed_escalation = set(proposed.get("escalation_keywords", []))

    # Count actual keyword set differences
    light_diff = current_light.symmetric_difference(proposed_light)
    escalation_diff = current_escalation.symmetric_difference(proposed_escalation)
    total_diff = len(light_diff) + len(escalation_diff)

    if total_diff > _MAX_CHANGES_PER_CYCLE:
        warnings.append(
            f"Keyword set diff is {total_diff}, exceeds cap of {_MAX_CHANGES_PER_CYCLE}. "
            "Falling back to current rules with only declared changes applied."
        )
        # Apply only the declared changes to current rules
        safe_light = set(current_rules.get("light_keywords", []))
        safe_escalation = set(current_rules.get("escalation_keywords", []))

        for change in changes[:_MAX_CHANGES_PER_CYCLE]:
            kw = change.get("keyword", "")
            action = change.get("action", "")
            to_tier = change.get("to", "")
            if not kw:
                continue
            if action == "move" or action == "add":
                # Remove from all sets first
                safe_light.discard(kw)
                safe_escalation.discard(kw)
                # Add to target
                if to_tier == "light":
                    safe_light.add(kw)
                elif to_tier in ("high", "escalation"):
                    safe_escalation.add(kw)
            elif action == "remove":
                safe_light.discard(kw)
                safe_escalation.discard(kw)

        return {
            "light_keywords": sorted(safe_light),
            "escalation_keywords": sorted(safe_escalation),
            "task_overrides": proposed.get("task_overrides", {}),
            "changes": changes[:_MAX_CHANGES_PER_CYCLE],
        }, warnings

    return {
        "light_keywords": sorted(proposed_light),
        "escalation_keywords": sorted(proposed_escalation),
        "task_overrides": proposed.get("task_overrides", {}),
        "changes": changes[:_MAX_CHANGES_PER_CYCLE],
    }, warnings


def _save_rules(rules: dict[str, Any], updated_by: str = "router_learner") -> Path:
    """Write routing_rules.json with metadata."""
    path = _rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = {
        "version": rules.get("version", 1) + 1 if "version" in rules else 1,
        "updated_at": _utc_now(),
        "updated_by": updated_by,
        "light_keywords": rules.get("light_keywords", []),
        "escalation_keywords": rules.get("escalation_keywords", []),
        "task_overrides": rules.get("task_overrides", {}),
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def learn_from_telemetry(
    *,
    dispatch_fn: Any | None = None,
) -> dict[str, Any]:
    """Run one self-rewrite cycle.

    1. Build eval report from telemetry
    2. Load current routing rules
    3. Send both to GPT-5.4 via dispatch
    4. Apply safety gate
    5. Save updated rules (with backup)
    6. Log the rewrite event

    Args:
        dispatch_fn: Optional override for dispatch.dispatch_task (for testing).

    Returns:
        Result dict with eval_report, changes, warnings, and paths.
    """
    # 1. Build eval report
    eval_report = build_eval_report()

    if eval_report["event_count"] == 0:
        return {
            "status": "skipped",
            "reason": "No router events found — nothing to learn from.",
            "eval_report": eval_report,
        }

    # 2. Load current rules
    current_rules = _load_routing_rules()

    # 3. Call GPT-5.4 for analysis
    if dispatch_fn is None:
        from . import dispatch as _dispatch_mod
        dispatch_fn = _dispatch_mod.dispatch_task

    prompt = _build_rewrite_prompt(current_rules, eval_report)
    result = dispatch_fn(
        "canon_review",
        prompt,
        system="You are a routing optimization engine. Return only valid JSON.",
        description="Router self-rewrite: analyze eval and update keyword routing rules",
        max_tokens=1024,
    )

    if "error" in result:
        return {
            "status": "error",
            "reason": f"Dispatch failed: {result['error']}",
            "eval_report": eval_report,
            "dispatch_result": result,
        }

    content = result.get("content", "")
    proposed = _parse_llm_response(content)
    if proposed is None:
        return {
            "status": "error",
            "reason": "Failed to parse LLM response as JSON",
            "raw_response": content[:500],
            "eval_report": eval_report,
        }

    # 4. Apply safety gate
    safe_rules, warnings = _apply_safety_gate(current_rules, proposed)

    # 5. Backup + save
    backup_path = _backup_rules(_rules_path())
    saved_path = _save_rules(safe_rules)

    # 6. Log the rewrite event
    changes = safe_rules.get("changes", [])
    log_router_event(
        task_type="router_self_rewrite",
        model=result.get("model", "gpt-5.4"),
        status="ok",
        description=f"Rewrote routing rules: {len(changes)} changes",
        accepted=True,
    )

    return {
        "status": "ok",
        "changes": changes,
        "change_count": len(changes),
        "warnings": warnings,
        "rules_path": str(saved_path),
        "backup_path": str(backup_path) if backup_path else None,
        "eval_report_summary": {
            "event_count": eval_report["event_count"],
            "suggestion_count": eval_report["suggestion_count"],
        },
    }
