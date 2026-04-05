#!/usr/bin/env python3
"""Daemon control — check status, start, stop."""
import os
import subprocess
import sys
from pathlib import Path

PID_FILE = Path("/tmp/lore-daemon.pid")
LOG_FILE = Path("/var/log/lore-daemon.log")
DAEMON   = Path(__file__).parent / "lore_research_daemon.py"

def _running_pid():
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        return None

cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

if cmd == "status":
    pid = _running_pid()
    if pid:
        print(f"RUNNING pid={pid}")
    else:
        print("STOPPED")
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text().splitlines()
        print("Last log lines:")
        for l in lines[-8:]:
            print(" ", l)

elif cmd == "start":
    pid = _running_pid()
    if pid:
        print(f"Already running pid={pid}")
        sys.exit(0)
    env = {**os.environ, "LORE_WIKI_DIR": "/root/lore"}
    proc = subprocess.Popen(
        [sys.executable, str(DAEMON)],
        stdout=open(LOG_FILE, "a"),
        stderr=subprocess.STDOUT,
        env=env,
        cwd="/root/lore",
        start_new_session=True,
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"Started pid={proc.pid}")

elif cmd == "stop":
    import signal
    pid = _running_pid()
    if not pid:
        print("Not running")
        sys.exit(0)
    os.kill(pid, signal.SIGTERM)
    print(f"Sent SIGTERM to {pid}")
