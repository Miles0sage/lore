"""Tests for the cost_guard scaffold — CostGuard class and CLI integration."""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

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


def _load_cost_guard_module() -> types.ModuleType:
    """Load cost_guard.py template as a module for black-box testing."""
    from lore.scaffold import TEMPLATES

    src = TEMPLATES["cost_guard"]
    mod = types.ModuleType("cost_guard")
    exec(compile(src, "<cost_guard>", "exec"), mod.__dict__)  # noqa: S102
    return mod


# ── Template registration ─────────────────────────────────────────────────────


def test_cost_guard_template_exists():
    from lore.scaffold import TEMPLATES

    assert "cost_guard" in TEMPLATES
    assert len(TEMPLATES["cost_guard"]) > 0


def test_cost_guard_in_list_patterns():
    from lore.scaffold import list_patterns

    names = {p["pattern"] for p in list_patterns()}
    assert "cost_guard" in names


def test_cost_guard_archetype_is_timekeeper():
    from lore.scaffold import list_patterns

    pattern = next(p for p in list_patterns() if p["pattern"] == "cost_guard")
    assert pattern["archetype"] == "The Timekeeper"


def test_cost_guard_template_has_lore_scaffold_header():
    from lore.scaffold import TEMPLATES

    assert "LORE SCAFFOLD:" in TEMPLATES["cost_guard"]


def test_cost_guard_template_compiles():
    from lore.scaffold import TEMPLATES

    compile(TEMPLATES["cost_guard"], "<cost_guard>", "exec")


# ── CLI scaffold cost_guard ───────────────────────────────────────────────────


def test_cli_scaffold_cost_guard_stdout():
    result = _run("scaffold", "cost_guard")
    assert result.returncode == 0
    assert "CostGuard" in result.stdout
    assert "CostGuardExceeded" in result.stdout


def test_cli_scaffold_cost_guard_to_file(tmp_path):
    result = _run("scaffold", "cost_guard", "-o", str(tmp_path))
    assert result.returncode == 0
    assert "Wrote" in result.stdout
    written = (tmp_path / "cost_guard.py").read_text()
    assert "class CostGuard" in written
    assert "class CostGuardExceeded" in written


def test_cli_scaffold_list_includes_cost_guard():
    result = _run("scaffold", "--list")
    assert result.returncode == 0
    assert "cost_guard" in result.stdout
    assert "19 patterns available" in result.stdout


# ── CostGuardExceeded exception ───────────────────────────────────────────────


def test_cost_guard_exceeded_is_exception():
    mod = _load_cost_guard_module()
    exc = mod.CostGuardExceeded(used=100, budget=50, step="llm_call")
    assert isinstance(exc, Exception)
    assert exc.used == 100
    assert exc.budget == 50
    assert exc.step == "llm_call"
    assert "100" in str(exc)
    assert "50" in str(exc)


def test_cost_guard_exceeded_no_step():
    mod = _load_cost_guard_module()
    exc = mod.CostGuardExceeded(used=200, budget=100)
    assert exc.step == ""
    assert "200" in str(exc)


# ── CostGuard construction ────────────────────────────────────────────────────


def test_cost_guard_default_construction():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard()
    assert guard.budget == 100_000
    assert guard.warn_at == 0.80
    assert guard.used == 0
    assert guard.remaining == 100_000


def test_cost_guard_custom_budget():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=50_000, warn_at=0.75)
    assert guard.budget == 50_000
    assert guard.warn_at == 0.75


def test_cost_guard_invalid_budget_raises():
    mod = _load_cost_guard_module()
    with pytest.raises(ValueError, match="budget_tokens"):
        mod.CostGuard(budget_tokens=0)

    with pytest.raises(ValueError, match="budget_tokens"):
        mod.CostGuard(budget_tokens=-1)


def test_cost_guard_invalid_warn_at_raises():
    mod = _load_cost_guard_module()
    with pytest.raises(ValueError, match="warn_at"):
        mod.CostGuard(warn_at=0.0)

    with pytest.raises(ValueError, match="warn_at"):
        mod.CostGuard(warn_at=1.0)

    with pytest.raises(ValueError, match="warn_at"):
        mod.CostGuard(warn_at=1.5)


# ── consume ───────────────────────────────────────────────────────────────────


def test_consume_increments_used():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000)
    guard.consume("step1", 1_000)
    assert guard.used == 1_000
    guard.consume("step2", 500)
    assert guard.used == 1_500


def test_consume_records_step_log():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000)
    guard.consume("llm_call", 2_400)
    guard.consume("tool_use", 300)
    s = guard.summary()
    assert s["steps"] == 2
    assert s["step_log"][0]["step"] == "llm_call"
    assert s["step_log"][0]["tokens"] == 2_400
    assert s["step_log"][1]["step"] == "tool_use"
    assert s["step_log"][1]["tokens"] == 300


def test_consume_raises_when_budget_exceeded():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=1_000)
    with pytest.raises(mod.CostGuardExceeded) as exc_info:
        guard.consume("expensive_step", 1_001)
    assert exc_info.value.used == 1_001
    assert exc_info.value.budget == 1_000
    assert exc_info.value.step == "expensive_step"


def test_consume_raises_exactly_at_budget():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=500)
    with pytest.raises(mod.CostGuardExceeded):
        guard.consume("step", 500)


def test_consume_negative_tokens_raises():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000)
    with pytest.raises(ValueError, match="non-negative"):
        guard.consume("step", -1)


# ── check ─────────────────────────────────────────────────────────────────────


def test_check_within_budget_does_not_raise():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000)
    guard.consume("step", 5_000)
    guard.check()  # should not raise


def test_check_raises_when_over_budget():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=100)
    # Bypass consume to force _used over budget without triggering consume's check
    guard._used = 101
    with pytest.raises(mod.CostGuardExceeded):
        guard.check()


def test_check_with_step_label():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=100)
    guard._used = 150
    with pytest.raises(mod.CostGuardExceeded) as exc_info:
        guard.check(step="my_step")
    assert exc_info.value.step == "my_step"


# ── warn_if_low ───────────────────────────────────────────────────────────────


def test_warn_if_low_returns_false_when_below_threshold():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000, warn_at=0.80)
    guard._used = 7_000  # 70%, below threshold
    assert guard.warn_if_low() is False


def test_warn_if_low_returns_true_when_above_threshold():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000, warn_at=0.80)
    guard._used = 8_500  # 85%, above threshold
    assert guard.warn_if_low() is True


def test_warn_if_low_fires_only_once():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000, warn_at=0.80)
    guard._used = 9_000
    assert guard.warn_if_low() is True
    assert guard.warn_if_low() is False  # second call is no-op
    assert guard.warn_if_low() is False  # third call is no-op


def test_warn_if_low_at_exact_threshold():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000, warn_at=0.80)
    guard._used = 8_000  # exactly 80%
    assert guard.warn_if_low() is True


# ── summary ───────────────────────────────────────────────────────────────────


def test_summary_keys():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=5_000, name="test_guard")
    guard.consume("step1", 1_000)
    s = guard.summary()

    for key in ("name", "budget", "used", "remaining", "pct_used", "warn_at_pct", "warned", "steps", "step_log", "elapsed_seconds"):
        assert key in s, f"missing key: {key}"


def test_summary_values():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000, warn_at=0.80, name="my_agent")
    guard.consume("call", 3_000)
    s = guard.summary()
    assert s["name"] == "my_agent"
    assert s["budget"] == 10_000
    assert s["used"] == 3_000
    assert s["remaining"] == 7_000
    assert s["pct_used"] == 30.0
    assert s["warn_at_pct"] == 80.0
    assert s["warned"] is False
    assert s["steps"] == 1
    assert s["elapsed_seconds"] >= 0


def test_summary_remaining_never_negative():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=100)
    guard._used = 200  # force over-budget without raising
    s = guard.summary()
    assert s["remaining"] == 0


# ── reset ─────────────────────────────────────────────────────────────────────


def test_reset_clears_state():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000)
    guard.consume("step", 5_000)
    guard._used = 8_500
    guard.warn_if_low()
    guard.reset()
    assert guard.used == 0
    assert guard.remaining == 10_000
    assert guard._warned is False
    assert guard._step_log == []


# ── repr ──────────────────────────────────────────────────────────────────────


def test_repr_contains_key_info():
    mod = _load_cost_guard_module()
    guard = mod.CostGuard(budget_tokens=10_000, name="agent_x")
    guard.consume("step", 2_500)
    r = repr(guard)
    assert "agent_x" in r
    assert "2500" in r
    assert "10000" in r


# ── audit detection ───────────────────────────────────────────────────────────


def test_audit_suggest_cost_guard_on_cost_keyword():
    from lore.audit import suggest_lore_actions

    parsed = {
        "summary": "No cost tracking or budget limits in the agent loop.",
        "top_findings": [],
        "missing_capabilities": ["cost visibility", "token budget enforcement"],
    }
    actions = suggest_lore_actions(parsed)
    patterns = [a["pattern"] for a in actions]
    assert "cost_guard" in patterns


def test_audit_suggest_cost_guard_on_budget_keyword():
    from lore.audit import suggest_lore_actions

    parsed = {
        "summary": "Budget limits are missing; agents can overspend.",
        "top_findings": [],
        "missing_capabilities": [],
    }
    actions = suggest_lore_actions(parsed)
    patterns = [a["pattern"] for a in actions]
    assert "cost_guard" in patterns


def test_audit_suggest_cost_guard_command_format():
    from lore.audit import suggest_lore_actions

    parsed = {
        "summary": "Token spend is unmonitored.",
        "top_findings": [],
        "missing_capabilities": [],
    }
    actions = suggest_lore_actions(parsed)
    cost_action = next((a for a in actions if a["pattern"] == "cost_guard"), None)
    assert cost_action is not None
    assert cost_action["command"] == "lore scaffold cost_guard"
    assert cost_action["type"] == "scaffold"


def test_audit_no_false_positive_when_no_cost_keywords():
    from lore.audit import suggest_lore_actions

    parsed = {
        "summary": "Circuit breaker missing. Dead letter queue needed.",
        "top_findings": [],
        "missing_capabilities": [],
    }
    actions = suggest_lore_actions(parsed)
    patterns = [a["pattern"] for a in actions]
    assert "cost_guard" not in patterns
