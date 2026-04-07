"""
lore run — inject reliability contracts into any agent process.

lore.yaml schema:
    budget_tokens: 500000          # hard stop
    warn_at: 0.80                  # warn at 80%
    circuit_breaker:
      enabled: true
      threshold: 5                 # failures before open
      window_seconds: 60
    dlq:
      enabled: true
      on_permanent: log            # log | notify_slack
      on_transient: retry          # retry | dlq
    observability:
      enabled: true
      log_level: INFO
    checkpoint:
      enabled: false
      path: .lore/checkpoints/
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Budget parsing
# ---------------------------------------------------------------------------

_LORE_YAML_DEFAULTS: dict[str, Any] = {
    "budget_tokens": None,
    "warn_at": 0.80,
    "circuit_breaker": {
        "enabled": False,
        "threshold": 5,
        "window_seconds": 60,
    },
    "dlq": {
        "enabled": False,
        "on_permanent": "log",
        "on_transient": "retry",
    },
    "observability": {
        "enabled": True,
        "log_level": "INFO",
    },
    "checkpoint": {
        "enabled": False,
        "path": ".lore/checkpoints/",
    },
}


def _parse_budget_value(value: Any) -> int | None:
    """Parse budget tokens from yaml value (str like '100k', '1M', or int)."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower().endswith("k"):
        return int(float(s[:-1]) * 1_000)
    if s.lower().endswith("m"):
        return int(float(s[:-1]) * 1_000_000)
    return int(s)


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge *override* into a copy of *base*, recursing into nested dicts."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


# ---------------------------------------------------------------------------
# load_lore_yaml
# ---------------------------------------------------------------------------


def load_lore_yaml(path: str | Path = "lore.yaml") -> dict[str, Any]:
    """Parse *path* as YAML, merge with defaults, return config dict.

    Missing file or missing keys fall back to sensible defaults.
    budget_tokens may be expressed as '100k', '1M', or a plain integer.

    Args:
        path: Path to lore.yaml (default: 'lore.yaml').

    Returns:
        Config dict with all keys present (defaults filled in).
    """
    config: dict[str, Any] = _deep_merge(_LORE_YAML_DEFAULTS, {})

    yaml_path = Path(path)
    if not yaml_path.exists():
        return config

    try:
        import yaml  # type: ignore[import]
        with yaml_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    except ImportError:
        # Fallback: minimal key=value parser for simple flat YAML
        raw = _parse_simple_yaml(yaml_path)
    except Exception:
        return config

    if not isinstance(raw, dict):
        return config

    config = _deep_merge(config, raw)

    # Normalise budget_tokens to int or None
    config["budget_tokens"] = _parse_budget_value(config.get("budget_tokens"))

    return config


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Minimal YAML parser for flat key: value files (no PyYAML required)."""
    result: dict[str, Any] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    except OSError:
        pass
    return result


# ---------------------------------------------------------------------------
# build_env
# ---------------------------------------------------------------------------


def build_env(config: dict[str, Any]) -> dict[str, str]:
    """Build a dict of LORE_* env vars from *config*.

    These vars are read by lore/preamble.py inside the child process.

    Args:
        config: Parsed config dict (from load_lore_yaml).

    Returns:
        Dict of environment variable name -> string value.
    """
    env: dict[str, str] = {}

    budget = config.get("budget_tokens")
    if budget is not None:
        env["LORE_BUDGET_TOKENS"] = str(budget)
        env["LORE_WARN_AT"] = str(config.get("warn_at", 0.80))

    cb = config.get("circuit_breaker", {})
    if cb.get("enabled"):
        env["LORE_CIRCUIT_BREAKER"] = "true"
        env["LORE_CIRCUIT_BREAKER_THRESHOLD"] = str(cb.get("threshold", 5))
        env["LORE_CIRCUIT_BREAKER_WINDOW_SECONDS"] = str(cb.get("window_seconds", 60))

    obs = config.get("observability", {})
    if obs.get("enabled", True):
        env["LORE_OBSERVABILITY"] = "true"
        env["LORE_LOG_LEVEL"] = str(obs.get("log_level", "INFO"))

    dlq = config.get("dlq", {})
    if dlq.get("enabled"):
        env["LORE_DLQ"] = "true"
        env["LORE_DLQ_ON_PERMANENT"] = str(dlq.get("on_permanent", "log"))
        env["LORE_DLQ_ON_TRANSIENT"] = str(dlq.get("on_transient", "retry"))

    ck = config.get("checkpoint", {})
    if ck.get("enabled"):
        env["LORE_CHECKPOINT"] = "true"
        env["LORE_CHECKPOINT_PATH"] = str(ck.get("path", ".lore/checkpoints/"))

    return env


# ---------------------------------------------------------------------------
# generate_preamble
# ---------------------------------------------------------------------------


def generate_preamble(config: dict[str, Any]) -> str:
    """Generate the Python preamble code that patches LLM clients.

    The returned string is valid Python that can be written to a temp file
    and set as PYTHONSTARTUP, or exec'd directly.

    Args:
        config: Parsed config dict (from load_lore_yaml).

    Returns:
        Python source code string.
    """
    preamble_module = Path(__file__).parent / "preamble.py"
    lines = [
        "import sys as _lore_sys",
        f"_lore_sys.path.insert(0, {str(Path(__file__).parents[1])!r})",
        "try:",
        "    from lore.preamble import activate as _lore_activate",
        "    _lore_activate()",
        "except Exception as _lore_exc:",
        "    import logging",
        "    logging.getLogger('lore').warning('lore preamble failed: %s', _lore_exc)",
        "del _lore_sys",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# run_with_runtime
# ---------------------------------------------------------------------------


def run_with_runtime(
    script_path: str | Path,
    config: dict[str, Any],
    extra_args: list[str] | None = None,
) -> int:
    """Execute *script_path* with Lore reliability contracts injected.

    Sets LORE_* env vars and PYTHONSTARTUP to the generated preamble,
    then execs the script in a subprocess.

    Args:
        script_path: Path to the Python script to run.
        config:      Parsed config dict (from load_lore_yaml).
        extra_args:  Additional CLI args to pass to the script.

    Returns:
        Exit code from the child process.
    """
    import tempfile

    script = Path(script_path).resolve()
    if not script.exists():
        print(f"lore run: error: script not found: {script}", file=sys.stderr)
        return 1

    # Write preamble to a temp file and use PYTHONSTARTUP
    preamble_code = generate_preamble(config)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        prefix="lore_preamble_",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(preamble_code)
        tmp_path = tmp.name

    try:
        child_env = {**os.environ}
        child_env.update(build_env(config))
        child_env["PYTHONSTARTUP"] = tmp_path

        cmd = [sys.executable, str(script)] + (extra_args or [])
        result = subprocess.run(cmd, env=child_env)
        return result.returncode
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# init_lore_yaml  (used by lore init command)
# ---------------------------------------------------------------------------

_DEFAULT_LORE_YAML = """\
# lore.yaml — Lore runtime configuration
# Run your agent with: lore run my_agent.py --budget 100k

budget_tokens: 500000       # hard stop (tokens). Use 100k, 1M, or plain int.
warn_at: 0.80               # warn when 80% of budget consumed

circuit_breaker:
  enabled: true
  threshold: 5              # consecutive failures before opening
  window_seconds: 60        # recovery wait before probing (half-open)

dlq:
  enabled: false
  on_permanent: log         # log | notify_slack
  on_transient: retry       # retry | dlq

observability:
  enabled: true
  log_level: INFO           # DEBUG | INFO | WARNING | ERROR

checkpoint:
  enabled: false
  path: .lore/checkpoints/
"""


def init_lore_yaml(directory: str | Path = ".") -> Path:
    """Write a starter lore.yaml into *directory*.

    Args:
        directory: Target directory (default: current working directory).

    Returns:
        Path to the written file.

    Raises:
        FileExistsError: If lore.yaml already exists in *directory*.
    """
    target = Path(directory) / "lore.yaml"
    if target.exists():
        raise FileExistsError(f"lore.yaml already exists: {target}")
    target.write_text(_DEFAULT_LORE_YAML, encoding="utf-8")
    return target
