"""Tests for lore.monitor dashboard functions."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from lore.monitor import (
    get_circuit_states,
    get_dlq_stats,
    get_token_usage,
    render_dashboard,
    run_monitor,
)


# ---------------------------------------------------------------------------
# get_circuit_states
# ---------------------------------------------------------------------------


def test_get_circuit_states_empty(tmp_path: Path) -> None:
    """Returns [] when db file does not exist."""
    missing = tmp_path / "no_such_file.db"
    result = get_circuit_states(missing)
    assert result == []


def test_get_circuit_states_with_data(tmp_path: Path) -> None:
    """Returns rows when db has circuit_state entries."""
    db = tmp_path / "circuit_breaker.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE circuit_state (tool TEXT PRIMARY KEY, state TEXT NOT NULL DEFAULT 'closed', failures INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute("INSERT INTO circuit_state VALUES ('search', 'closed', 0)")
    conn.execute("INSERT INTO circuit_state VALUES ('llm', 'open', 3)")
    conn.commit()
    conn.close()

    result = get_circuit_states(db)
    assert len(result) == 2
    tools = {r["tool"] for r in result}
    assert tools == {"search", "llm"}
    open_row = next(r for r in result if r["tool"] == "llm")
    assert open_row["state"] == "open"
    assert open_row["failures"] == 3


# ---------------------------------------------------------------------------
# get_dlq_stats
# ---------------------------------------------------------------------------


def test_get_dlq_stats_empty(tmp_path: Path) -> None:
    """Returns zeros when db file does not exist."""
    missing = tmp_path / "no_such_dlq.db"
    result = get_dlq_stats(missing)
    assert result == {"depth": 0, "permanent": 0, "transient": 0, "ambiguous": 0}


def test_get_dlq_stats_with_data(tmp_path: Path) -> None:
    """Counts entries correctly by failure_class."""
    db = tmp_path / "dlq.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """CREATE TABLE dlq_entries (
            entry_id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            prompt_hash TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            failure_class TEXT NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 1,
            last_error TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            resolved_at REAL
        )"""
    )
    future = time.time() + 86400
    now = time.time()
    conn.execute(
        "INSERT INTO dlq_entries VALUES ('id1','t','h','{}','transient',1,'',?,?,NULL)",
        (now, future),
    )
    conn.execute(
        "INSERT INTO dlq_entries VALUES ('id2','t','h','{}','permanent',1,'',?,?,NULL)",
        (now, future),
    )
    conn.execute(
        "INSERT INTO dlq_entries VALUES ('id3','t','h','{}','transient',1,'',?,?,NULL)",
        (now, future),
    )
    conn.commit()
    conn.close()

    result = get_dlq_stats(db)
    assert result["depth"] == 3
    assert result["transient"] == 2
    assert result["permanent"] == 1
    assert result["ambiguous"] == 0


# ---------------------------------------------------------------------------
# get_token_usage
# ---------------------------------------------------------------------------


def test_get_token_usage_empty(tmp_path: Path) -> None:
    """Returns empty dict when file does not exist."""
    missing = tmp_path / "no_metrics.jsonl"
    result = get_token_usage(missing)
    assert result == {}


def test_get_token_usage_with_data(tmp_path: Path) -> None:
    """Parses the most recent record with 'consumed' key."""
    metrics = tmp_path / "circuit_metrics.jsonl"
    records = [
        {"ts": 1.0, "tool": "search", "from_state": "closed", "to_state": "open", "failures": 3},
        {"ts": 2.0, "consumed": 42331, "total": 500000, "pct_used": 0.085},
    ]
    metrics.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    result = get_token_usage(metrics)
    assert result.get("consumed") == 42331
    assert result.get("total") == 500000


# ---------------------------------------------------------------------------
# render_dashboard
# ---------------------------------------------------------------------------


def test_render_dashboard_no_crash() -> None:
    """render_dashboard with empty data dict does not raise."""
    # Pass None as console to exercise the plain-text fallback path
    render_dashboard(None, {})


def test_render_dashboard_with_rich() -> None:
    """render_dashboard with a real Rich console does not raise."""
    try:
        from rich.console import Console
        from io import StringIO

        buf = StringIO()
        console = Console(file=buf, no_color=True)
        data = {
            "circuits": [{"tool": "llm", "state": "open", "failures": 3}],
            "dlq": {"depth": 2, "permanent": 1, "transient": 1, "ambiguous": 0},
            "token": {"consumed": 42000, "total": 500000},
            "findings": [
                {"event": "error", "timestamp": time.time(), "error_type": "TimeoutError", "task_id": "t1"}
            ],
        }
        render_dashboard(console, data)
        output = buf.getvalue()
        assert "Circuit Breakers" in output or "llm" in output
    except ImportError:
        pytest.skip("rich not installed")


# ---------------------------------------------------------------------------
# run_monitor
# ---------------------------------------------------------------------------


def test_run_monitor_once() -> None:
    """run_monitor(once=True) completes without error."""
    run_monitor(once=True)
