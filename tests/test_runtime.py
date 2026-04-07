"""Tests for lore.runtime — load_lore_yaml, build_env, generate_preamble, run_cmd dry-run."""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import pytest

from lore.runtime import (
    _parse_budget_value,
    build_env,
    generate_preamble,
    init_lore_yaml,
    load_lore_yaml,
)


# ---------------------------------------------------------------------------
# _parse_budget_value
# ---------------------------------------------------------------------------


def test_parse_budget_value_plain_int():
    assert _parse_budget_value(500000) == 500000


def test_parse_budget_value_k():
    assert _parse_budget_value("100k") == 100_000


def test_parse_budget_value_K_upper():
    assert _parse_budget_value("100K") == 100_000


def test_parse_budget_value_m():
    assert _parse_budget_value("1M") == 1_000_000


def test_parse_budget_value_m_lower():
    assert _parse_budget_value("1m") == 1_000_000


def test_parse_budget_value_none():
    assert _parse_budget_value(None) is None


def test_parse_budget_value_float_k():
    assert _parse_budget_value("1.5k") == 1_500


# ---------------------------------------------------------------------------
# load_lore_yaml — defaults when file is missing
# ---------------------------------------------------------------------------


def test_load_lore_yaml_defaults_missing_file(tmp_path):
    config = load_lore_yaml(tmp_path / "nonexistent.yaml")
    assert config["budget_tokens"] is None
    assert config["warn_at"] == pytest.approx(0.80)
    assert config["circuit_breaker"]["enabled"] is False
    assert config["circuit_breaker"]["threshold"] == 5
    assert config["dlq"]["enabled"] is False
    assert config["observability"]["enabled"] is True


def test_load_lore_yaml_defaults_empty_file(tmp_path):
    yaml_file = tmp_path / "lore.yaml"
    yaml_file.write_text("", encoding="utf-8")
    config = load_lore_yaml(yaml_file)
    assert config["budget_tokens"] is None
    assert config["warn_at"] == pytest.approx(0.80)


# ---------------------------------------------------------------------------
# load_lore_yaml — parses budget
# ---------------------------------------------------------------------------


def test_load_lore_yaml_parses_budget_100k(tmp_path):
    yaml_file = tmp_path / "lore.yaml"
    yaml_file.write_text("budget_tokens: 100k\n", encoding="utf-8")
    config = load_lore_yaml(yaml_file)
    assert config["budget_tokens"] == 100_000


def test_load_lore_yaml_parses_budget_1M(tmp_path):
    yaml_file = tmp_path / "lore.yaml"
    yaml_file.write_text("budget_tokens: 1M\n", encoding="utf-8")
    config = load_lore_yaml(yaml_file)
    assert config["budget_tokens"] == 1_000_000


def test_load_lore_yaml_parses_budget_plain_int(tmp_path):
    yaml_file = tmp_path / "lore.yaml"
    yaml_file.write_text("budget_tokens: 500000\n", encoding="utf-8")
    config = load_lore_yaml(yaml_file)
    assert config["budget_tokens"] == 500_000


# ---------------------------------------------------------------------------
# build_env — correct LORE_* env vars
# ---------------------------------------------------------------------------


def test_build_env_no_budget_no_cb():
    config = {
        "budget_tokens": None,
        "warn_at": 0.80,
        "circuit_breaker": {"enabled": False, "threshold": 5, "window_seconds": 60},
        "dlq": {"enabled": False, "on_permanent": "log", "on_transient": "retry"},
        "observability": {"enabled": True, "log_level": "INFO"},
        "checkpoint": {"enabled": False, "path": ".lore/checkpoints/"},
    }
    env = build_env(config)
    assert "LORE_BUDGET_TOKENS" not in env
    assert "LORE_CIRCUIT_BREAKER" not in env


def test_build_env_sets_budget_vars():
    config = {
        "budget_tokens": 100_000,
        "warn_at": 0.75,
        "circuit_breaker": {"enabled": False, "threshold": 5, "window_seconds": 60},
        "dlq": {"enabled": False, "on_permanent": "log", "on_transient": "retry"},
        "observability": {"enabled": True, "log_level": "INFO"},
        "checkpoint": {"enabled": False, "path": ".lore/checkpoints/"},
    }
    env = build_env(config)
    assert env["LORE_BUDGET_TOKENS"] == "100000"
    assert env["LORE_WARN_AT"] == "0.75"


def test_build_env_sets_circuit_breaker_vars():
    config = {
        "budget_tokens": None,
        "warn_at": 0.80,
        "circuit_breaker": {"enabled": True, "threshold": 3, "window_seconds": 120},
        "dlq": {"enabled": False, "on_permanent": "log", "on_transient": "retry"},
        "observability": {"enabled": True, "log_level": "INFO"},
        "checkpoint": {"enabled": False, "path": ".lore/checkpoints/"},
    }
    env = build_env(config)
    assert env["LORE_CIRCUIT_BREAKER"] == "true"
    assert env["LORE_CIRCUIT_BREAKER_THRESHOLD"] == "3"
    assert env["LORE_CIRCUIT_BREAKER_WINDOW_SECONDS"] == "120"


def test_build_env_sets_all_vars():
    config = {
        "budget_tokens": 500_000,
        "warn_at": 0.80,
        "circuit_breaker": {"enabled": True, "threshold": 5, "window_seconds": 60},
        "dlq": {"enabled": True, "on_permanent": "log", "on_transient": "retry"},
        "observability": {"enabled": True, "log_level": "DEBUG"},
        "checkpoint": {"enabled": True, "path": ".lore/checkpoints/"},
    }
    env = build_env(config)
    assert env["LORE_BUDGET_TOKENS"] == "500000"
    assert env["LORE_CIRCUIT_BREAKER"] == "true"
    assert env["LORE_DLQ"] == "true"
    assert env["LORE_OBSERVABILITY"] == "true"
    assert env["LORE_LOG_LEVEL"] == "DEBUG"
    assert env["LORE_CHECKPOINT"] == "true"


# ---------------------------------------------------------------------------
# generate_preamble — returns valid Python string
# ---------------------------------------------------------------------------


def test_generate_preamble_returns_string():
    config = load_lore_yaml("nonexistent_for_test.yaml")
    preamble = generate_preamble(config)
    assert isinstance(preamble, str)
    assert len(preamble) > 0


def test_generate_preamble_is_valid_python():
    config = load_lore_yaml("nonexistent_for_test.yaml")
    preamble = generate_preamble(config)
    # Should compile without error
    compile(preamble, "<preamble>", "exec")


def test_generate_preamble_contains_activate():
    config = load_lore_yaml("nonexistent_for_test.yaml")
    preamble = generate_preamble(config)
    assert "activate" in preamble


# ---------------------------------------------------------------------------
# _run_cmd dry-run via CLI
# ---------------------------------------------------------------------------


def test_run_cmd_dry_run(tmp_path, capsys):
    from lore.cli import main

    script = tmp_path / "agent.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    yaml_file = tmp_path / "lore.yaml"
    yaml_file.write_text("budget_tokens: 100k\n", encoding="utf-8")

    rc = main(["run", str(script), "--budget", "100k", "--config", str(yaml_file), "--dry-run"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "dry-run" in captured.out
    assert "LORE_BUDGET_TOKENS" in captured.out


def test_run_cmd_dry_run_no_budget(tmp_path, capsys):
    from lore.cli import main

    script = tmp_path / "agent.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("", encoding="utf-8")

    rc = main(["run", str(script), "--config", str(yaml_file), "--dry-run"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "dry-run" in captured.out
    # No budget or circuit_breaker configured — those vars must be absent
    assert "LORE_BUDGET_TOKENS" not in captured.out
    assert "LORE_CIRCUIT_BREAKER" not in captured.out


# ---------------------------------------------------------------------------
# init_lore_yaml
# ---------------------------------------------------------------------------


def test_init_lore_yaml_creates_file(tmp_path):
    path = init_lore_yaml(tmp_path)
    assert path.exists()
    assert path.name == "lore.yaml"
    content = path.read_text()
    assert "budget_tokens" in content
    assert "circuit_breaker" in content


def test_init_lore_yaml_raises_if_exists(tmp_path):
    (tmp_path / "lore.yaml").write_text("exists\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        init_lore_yaml(tmp_path)


# ---------------------------------------------------------------------------
# Integration: run_with_runtime executes a real script
# ---------------------------------------------------------------------------


def test_run_with_runtime_simple_script(tmp_path):
    from lore.runtime import run_with_runtime

    script = tmp_path / "hello.py"
    script.write_text("print('lore runtime ok')\n", encoding="utf-8")
    config = load_lore_yaml(tmp_path / "no.yaml")

    rc = run_with_runtime(script, config)
    assert rc == 0


def test_run_with_runtime_missing_script(tmp_path, capsys):
    from lore.runtime import run_with_runtime

    config = load_lore_yaml(tmp_path / "no.yaml")
    rc = run_with_runtime(tmp_path / "missing.py", config)
    assert rc == 1
    captured = capsys.readouterr()
    assert "not found" in captured.err
