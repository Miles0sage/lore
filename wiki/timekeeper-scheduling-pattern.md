---
backlinks: []
concepts:
- scheduling
- cron
- background-jobs
- kairos-loop
- discovery-loops
- keepalive-jobs
- dead-job-detection
- cost-aware-scheduling
- scout-discovery-pattern
- morning-briefs
confidence: high
created: '2026-04-05'
domain: ai-agents
id: timekeeper-scheduling-pattern
sources:
- raw/2026-04-05-timekeeper-scheduling-proposal.md
status: published
title: 'The Timekeeper: Scheduling Patterns for Proactive AI Agents'
updated: '2026-04-06'
---

# The Timekeeper: Scheduling Patterns for Proactive AI Agents

## Overview

The Timekeeper is the scheduling pattern that makes an agent system **proactive instead of purely reactive**. It governs when work should happen without a human trigger: nightly research, keepalive jobs, morning briefs, maintenance loops, and queue cleanup.

Without scheduling, an agent system is a calculator — it only acts when prompted. With a Timekeeper, it becomes a living workflow that improves itself over time.

## Why Reactive-Only Agents Fail

Reactive systems put maintenance burden on operators:

- Research never becomes a routine
- Stale canon stays stale until someone notices
- Integrations break silently and stay broken
- Recurring cleanup (dead letters, old proposals) accumulates debt
- Operators carry the cognitive load of remembering every recurring task

The Timekeeper is what converts one-off automation into a living system.

## The KAIROS Loop

The core scheduling primitive for long-running daemons. Named after the Greek concept of **opportune time** — the right moment to act.

```
KAIROS = Check → Act → Rest
```

```python
import asyncio
import time

class KairosLoop:
    """
    Check: is there work to do right now?
    Act:   do it (bounded, observable)
    Rest:  sleep until next interval
    """
    def __init__(self, interval_seconds: int, max_cost_usd: float = 1.0):
        self.interval = interval_seconds
        self.max_cost = max_cost_usd
        self._running = False

    async def run(self):
        self._running = True
        while self._running:
            cycle_start = time.monotonic()
            try:
                cost = await self.check_and_act()
                if cost > self.max_cost:
                    await self._alert(f"Cycle cost ${cost:.4f} exceeds limit ${self.max_cost}")
            except Exception as exc:
                await self._record_failure(exc)
            elapsed = time.monotonic() - cycle_start
            sleep = max(0, self.interval - elapsed)
            await asyncio.sleep(sleep)

    async def check_and_act(self) -> float:
        """Override: return cost incurred this cycle."""
        raise NotImplementedError

    async def _alert(self, msg: str):
        # emit to observability layer
        pass

    async def _record_failure(self, exc: Exception):
        # emit to postmortem pipeline
        pass

    def stop(self):
        self._running = False
```

**Critical properties of the KAIROS loop:**
- **Bounded**: each cycle has a cost ceiling and a time ceiling
- **Observable**: failures are recorded, not swallowed
- **Idempotent**: safe to restart after a crash
- **Sleeping**: never busy-waits (no `while True: pass`)

## Job Taxonomy

Not all scheduled jobs are equal. Classify before designing:

| Type | Cadence | Failure mode | Example |
|---|---|---|---|
| **Discovery** | 30–60 min | Stale knowledge | Research daemon, trend scanner |
| **Maintenance** | Daily/weekly | Accumulated debt | Prune stale proposals, re-index wiki |
| **Synthesis** | Daily | Missed briefs | Morning brief, weekly canon report |
| **Keepalive** | 15–30 min | Silent integration death | Session refresh, health ping |
| **Cost control** | Hourly | Budget overrun | Spend report, circuit reset |
| **Publication** | On approval | Delayed canon update | Batch publish approved proposals |

## Cron vs Daemon

Two patterns for running scheduled jobs. Choose based on job duration and statefulness.

### Cron (stateless, short-lived)

Best for jobs that complete in under 5 minutes and carry no state between runs:

```bash
# /etc/cron.d/lore
# Morning brief at 7am UTC
0 7 * * * root cd /root/lore && python3 -m lore.jobs.morning_brief >> /var/log/lore/brief.log 2>&1

# Keepalive every 30 minutes
*/30 * * * * root python3 /root/lore/scripts/keepalive.py >> /var/log/lore/keepalive.log 2>&1

# Weekly canon maintenance on Sunday at 2am
0 2 * * 0 root cd /root/lore && python3 -m lore.jobs.maintenance >> /var/log/lore/maintenance.log 2>&1
```

### Daemon (stateful, long-running)

Best for jobs that maintain state across cycles — connection pools, running totals, backoff state:

```python
# daemon_ctl.py pattern (already in lore/scripts/)
import subprocess
import sys
from pathlib import Path

PID_FILE = Path("/tmp/lore-daemon.pid")

def start():
    proc = subprocess.Popen(
        [sys.executable, "scripts/lore_research_daemon.py"],
        stdout=open("/var/log/lore/daemon.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,   # detach from parent
    )
    PID_FILE.write_text(str(proc.pid))
    print(f"Daemon started: PID {proc.pid}")

def stop():
    if not PID_FILE.exists():
        print("No PID file — daemon not running")
        return
    pid = int(PID_FILE.read_text())
    os.kill(pid, signal.SIGTERM)
    PID_FILE.unlink()
    print(f"Sent SIGTERM to PID {pid}")
```

## Dead-Job Detection

The most dangerous scheduling failure: the job appears to be running but is not doing anything useful.

Symptoms:
- PID file exists, process running, but no log output in >2× interval
- Job completes instantly every cycle (always finding "nothing to do")
- Cost counter not incrementing for a job that should be spending

Detection:

```python
class DeadJobDetector:
    def __init__(self, job_id: str, expected_interval: int, tolerance: float = 2.5):
        self.job_id = job_id
        self.max_silence = expected_interval * tolerance
        self._last_activity: float = time.monotonic()

    def record_activity(self):
        self._last_activity = time.monotonic()

    def is_dead(self) -> bool:
        return (time.monotonic() - self._last_activity) > self.max_silence

    def check(self):
        if self.is_dead():
            raise RuntimeError(
                f"Job {self.job_id} has been silent for "
                f"{time.monotonic() - self._last_activity:.0f}s "
                f"(max allowed: {self.max_silence:.0f}s)"
            )
```

Call `record_activity()` at the end of every productive cycle. Check `is_dead()` from an external health monitor or watchdog.

## Cost-Aware Scheduling

Scheduled jobs must respect budget boundaries. Without cost guards, a research daemon can burn $20 overnight.

```python
class BudgetGuard:
    def __init__(self, daily_budget_usd: float):
        self.daily_budget = daily_budget_usd
        self._spent_today: float = 0.0
        self._day = date.today()

    def reset_if_new_day(self):
        today = date.today()
        if today != self._day:
            self._spent_today = 0.0
            self._day = today

    def can_run(self, estimated_cost: float) -> bool:
        self.reset_if_new_day()
        return (self._spent_today + estimated_cost) <= self.daily_budget

    def record_spend(self, actual_cost: float):
        self._spent_today += actual_cost

    def remaining(self) -> float:
        self.reset_if_new_day()
        return max(0.0, self.daily_budget - self._spent_today)
```

Default budget tiers for LORE patterns:
- Discovery daemon: $0.50/day (DeepSeek quality gate)
- Morning brief: $0.05/day
- Weekly report: $0.20/week
- Keepalive: $0.00 (should be zero-cost pings)

## Graceful Shutdown

Long-running daemons must handle SIGTERM cleanly:

```python
import signal

class GracefulDaemon:
    def __init__(self):
        self._shutdown = False
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        print("Shutdown signal received — finishing current cycle...")
        self._shutdown = True

    async def run(self):
        while not self._shutdown:
            await self.cycle()
            if not self._shutdown:
                await asyncio.sleep(self.interval)
        await self.cleanup()
        print("Daemon stopped cleanly.")

    async def cleanup(self):
        # flush buffers, close connections, write final state
        pass
```

## Scheduling Anti-Patterns

| Anti-pattern | What goes wrong | Fix |
|---|---|---|
| `while True: work()` | Busy-waits, no sleep, burns CPU | Use KAIROS: check → act → sleep |
| Coupling schedule to UI | Job only runs if someone opens the app | Separate cron/daemon from interactive tooling |
| Silent failures | Cron job dies, nobody notices for a week | Log start/end, alert on silence >2× interval |
| Over-scheduling | Low-value jobs create noise and cost | Audit cadence quarterly, kill jobs that rarely produce output |
| Shared mutable state | Two daemons write to the same file | Use a queue or distributed lock |
| No idempotency | Duplicate runs create duplicate records | Add dedup key on all job outputs |

## Recovery Patterns

**Missed-run recovery**: if the daemon was down for a window, should it catch up?

```python
def should_catchup(last_run: datetime, interval: timedelta) -> bool:
    """Catch up only if we missed fewer than 3 cycles."""
    missed = (datetime.utcnow() - last_run) // interval
    return 1 <= missed <= 3

def get_catchup_runs(last_run: datetime, interval: timedelta) -> list[datetime]:
    if not should_catchup(last_run, interval):
        return []
    runs = []
    t = last_run + interval
    while t <= datetime.utcnow():
        runs.append(t)
        t += interval
    return runs
```

More than 3 missed cycles → skip catchup, emit an alert, let the next scheduled run proceed normally.

## In LORE

The Timekeeper is central to Lore's evolutionary claim. It is what makes the system **alive**:

- `lore_research_daemon.py` — 30-min KAIROS loop, parallel scouts
- `daemon_ctl.py` — start/stop/status with PID tracking
- Morning brief generation (daily)
- Weekly canon report (Sunday)
- `batch_review.py` — publish approved proposals on schedule

If those actions happen only when someone remembers, the system is not truly self-improving.

## Key Concepts

[[scheduling]]
[[cron]]
[[kairos-loop]]
[[background-jobs]]
[[discovery-loops]]
[[keepalive-jobs]]
[[dead-job-detection]]
[[cost-aware-scheduling]]
[[scout-discovery-pattern]]
[[archetype-the-timekeeper]]

## Sources

- `2026-04-05-timekeeper-scheduling-proposal.md`
- LORE daemon implementation (`scripts/lore_research_daemon.py`, `scripts/daemon_ctl.py`)
