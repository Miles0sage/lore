"""lore monitor — real-time agent health dashboard."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from lore.config import get_telemetry_dir


def get_circuit_states(db_path: Path) -> list[dict[str, Any]]:
    """Read all circuit names and states from SQLite.

    Returns [] when the db file does not exist or has no rows.
    """
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT tool, state, failures FROM circuit_state ORDER BY tool"
        ).fetchall()
        conn.close()
        return [{"tool": r["tool"], "state": r["state"], "failures": r["failures"]} for r in rows]
    except Exception:
        return []


def get_dlq_stats(db_path: Path) -> dict[str, int]:
    """Count DLQ entries by failure class.

    Returns {"depth": 0, "permanent": 0, "transient": 0, "ambiguous": 0}
    when the db file does not exist or is empty.
    """
    zero: dict[str, int] = {"depth": 0, "permanent": 0, "transient": 0, "ambiguous": 0}
    if not db_path.exists():
        return zero
    try:
        now = time.time()
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT failure_class, COUNT(*) as cnt FROM dlq_entries"
            " WHERE resolved_at IS NULL AND expires_at >= ? GROUP BY failure_class",
            (now,),
        ).fetchall()
        conn.close()
        stats = dict(zero)
        for row in rows:
            fc = row["failure_class"]
            count = row["cnt"]
            stats["depth"] += count
            if fc in stats:
                stats[fc] = count
        return stats
    except Exception:
        return zero


def get_token_usage(metrics_path: Path) -> dict[str, Any]:
    """Parse the most recent token budget entry from circuit_metrics.jsonl.

    Returns {} when the file does not exist or has no usable data.
    """
    if not metrics_path.exists():
        return {}
    try:
        import json

        lines = metrics_path.read_text(encoding="utf-8").splitlines()
        # Scan from the end for a record with token budget info
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if "consumed" in record or "tokens_used" in record:
                    return record
            except Exception:
                continue
        return {}
    except Exception:
        return {}


def get_recent_findings(observability_path: Path, n: int = 5) -> list[dict[str, Any]]:
    """Return the last *n* events from observability.jsonl as finding dicts."""
    if not observability_path.exists():
        return []
    try:
        import json

        lines = observability_path.read_text(encoding="utf-8").splitlines()
        findings = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                findings.append(record)
                if len(findings) >= n:
                    break
            except Exception:
                continue
        return list(reversed(findings))
    except Exception:
        return []


def _render_plain(data: dict[str, Any]) -> None:
    """Fallback plain-text render when rich is not installed."""
    circuits = data.get("circuits", [])
    dlq = data.get("dlq", {})
    findings = data.get("findings", [])

    print("=== Lore Monitor ===")
    print("\n-- Circuit Breakers --")
    if circuits:
        for c in circuits:
            state = c["state"].upper()
            mark = "x" if state == "OPEN" else "OK"
            print(f"  {c['tool']:<20} {state} [{mark}] (failures: {c['failures']})")
    else:
        print("  (no circuits recorded)")

    print("\n-- DLQ --")
    print(f"  depth: {dlq.get('depth', 0)}")
    print(f"  permanent: {dlq.get('permanent', 0)}")
    print(f"  transient: {dlq.get('transient', 0)}")
    print(f"  ambiguous: {dlq.get('ambiguous', 0)}")

    print("\n-- Recent Findings --")
    if findings:
        for f in findings:
            ts = f.get("timestamp", 0)
            event = f.get("event", "unknown")
            task_id = f.get("task_id", "")
            error_type = f.get("error_type", "")
            detail = error_type or task_id
            print(f"  [{event.upper()}] {detail}")
    else:
        print("  (no recent events)")
    print()


def render_dashboard(console: Any, data: dict[str, Any]) -> None:
    """Render one frame of the dashboard using Rich.

    Falls back to plain text if console is None.
    """
    if console is None:
        _render_plain(data)
        return

    try:
        from rich.columns import Columns
        from rich.panel import Panel
        from rich.progress import BarColumn, Progress, TextColumn
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        _render_plain(data)
        return

    circuits = data.get("circuits", [])
    dlq = data.get("dlq", {})
    token = data.get("token", {})
    findings = data.get("findings", [])

    # -- Cost / Token panel --
    consumed = token.get("consumed", token.get("tokens_used", 0))
    total = token.get("total", 500_000)
    pct = (consumed / total) if total > 0 else 0.0
    bar_filled = int(pct * 10)
    bar = "[green]" + "█" * bar_filled + "[dim]" + "░" * (10 - bar_filled) + "[/]"
    cost_text = Text()
    cost_text.append(f"{consumed:,} / {total:,}\n", style="bold")
    cost_text.append(bar + f"  {pct * 100:.1f}%")
    cost_panel = Panel(cost_text, title="Cost Burn", expand=True)

    # -- Circuit Breakers panel --
    cb_table = Table.grid(padding=(0, 1))
    if circuits:
        for c in circuits:
            state = c["state"]
            if state == "open":
                status = Text(f"OPEN [red]✗[/] ({c['failures']} fail)", style="red")
            elif state == "half_open":
                status = Text("HALF-OPEN [yellow]~[/]", style="yellow")
            else:
                status = Text("CLOSED [green]✓[/]", style="green")
            cb_table.add_row(f"{c['tool']}:", status)
    else:
        cb_table.add_row(Text("(no data)", style="dim"))
    cb_panel = Panel(cb_table, title="Circuit Breakers", expand=True)

    # -- DLQ panel --
    dlq_text = Text()
    dlq_text.append(f"depth: {dlq.get('depth', 0)}\n")
    dlq_text.append(f"permanent: {dlq.get('permanent', 0)}\n", style="red" if dlq.get("permanent", 0) else "")
    dlq_text.append(f"transient: {dlq.get('transient', 0)}\n")
    dlq_text.append(f"ambiguous: {dlq.get('ambiguous', 0)}")
    dlq_panel = Panel(dlq_text, title="DLQ", expand=True)

    console.print(Columns([cost_panel, cb_panel, dlq_panel], equal=True))

    # -- Recent findings --
    if findings:
        finding_table = Table(show_header=False, box=None, padding=(0, 1))
        finding_table.add_column("sev", style="bold", width=10)
        finding_table.add_column("ts", width=6)
        finding_table.add_column("detail")
        for f in findings[-5:]:
            event = f.get("event", "info").upper()
            ts_raw = f.get("timestamp", 0)
            try:
                import datetime
                ts_str = datetime.datetime.fromtimestamp(ts_raw).strftime("%H:%M")
            except Exception:
                ts_str = "--:--"
            detail = f.get("error_type") or f.get("task_id") or f.get("model") or ""
            sev_style = "red" if event == "ERROR" else "yellow" if event == "WARNING" else "dim"
            finding_table.add_row(
                Text(f"[{event}]", style=sev_style), ts_str, detail
            )
        console.print(Panel(finding_table, title="Recent Findings"))


def _collect_data() -> dict[str, Any]:
    """Gather all dashboard data from disk."""
    tel = get_telemetry_dir()
    cb_db = tel / "circuit_breaker.db"
    dlq_db = tel / "dlq.db"
    metrics = tel / "circuit_metrics.jsonl"
    obs = tel / "observability.jsonl"

    return {
        "circuits": get_circuit_states(cb_db),
        "dlq": get_dlq_stats(dlq_db),
        "token": get_token_usage(metrics),
        "findings": get_recent_findings(obs),
    }


def run_monitor(refresh_seconds: float = 2.0, once: bool = False) -> None:
    """Run the dashboard loop.

    Args:
        refresh_seconds: How often to refresh (ignored when once=True).
        once:            Print one snapshot and exit (for tests / CI).
    """
    try:
        from rich.console import Console

        console: Any = Console()
    except ImportError:
        console = None

    def _render_once() -> None:
        data = _collect_data()
        if console is not None:
            console.clear()
        render_dashboard(console, data)

    if once:
        _render_once()
        return

    try:
        while True:
            _render_once()
            time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        pass
