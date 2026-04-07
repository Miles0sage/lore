---
backlinks: []
concepts:
- background-jobs
- dead-job-detection
- keepalive-jobs
- morning-briefs
- cost-aware-scheduling
- kairos-loop
- scout-discovery-pattern
- discovery-loops
- cron
- scheduling
confidence: high
created: '2026-04-05'
domain: ai-agents
id: timekeeper-scheduling-pattern
sources:
- raw/2026-04-05-timekeeper-scheduling-proposal.md
- raw/2026-04-05-timekeeper-scheduling-proposal.md
status: published
title: 'The Timekeeper: Scheduling Patterns for Proactive AI Agents'
updated: '2026-04-06'
---

# The Timekeeper: Scheduling Patterns for Proactive AI Agents

## Overview

The Timekeeper is the scheduling pattern that makes an agent system **proactive instead of purely reactive**. It governs when work should happen without a human trigger: nightly research, keepalive jobs, morning briefs, maintenance loops, and queue cleanup.

Without scheduling, an agent system is a calculator — it only acts when prompted. With a Timekeeper, it becomes a living workflow that improves itself over time. This is the core role of scheduling in making Lore actually evolutionary: by continuously gathering data, maintaining state, and synthesizing insights on a fixed cadence, the system compounds knowledge and adapts autonomously.

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
- **Failure alerting for missed schedules**: The loop must explicitly track heartbeat timestamps. If a cycle fails to complete or misses its scheduled window, an alert is routed to the operator dashboard or incident channel, preventing silent degradation.

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

*Note: Overnight research cycles* typically fall under the **Discovery** and **Synthesis** categories, running during low-traffic windows to ingest new data, cross-reference it with existing canon, and prepare morning briefs without competing for daytime compute or API quotas.

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

Cron-driven agent loops excel at deterministic, fire-and-forget tasks. They are easy to audit, restart automatically on system boot, and integrate cleanly with standard Unix observability tools.

### Daemon (stateful, long-running)

Best for jobs that require persistent connections, in-memory caches, or complex state machines (e.g., the KAIROS loop). Daemons maintain context across cycles, reducing cold-start overhead but requiring explicit health checks, graceful shutdown handlers, and process supervision (systemd, supervisord, or container orchestrators).

## Key Concepts

- **Evolutionary Scheduling**: Using fixed cadences to compound agent knowledge, enabling the system to self-improve and adapt without manual intervention.
- **Cron-Driven Agent Loops**: Stateless, time-triggered executions ideal for discrete, short-duration tasks that don't require persistent memory.
- **Overnight Research Cycles**: Low-priority, high-throughput discovery jobs scheduled during off-peak hours to maximize data ingestion and synthesis efficiency.
- **Failure Alerting for Missed Schedules**: A mandatory observability layer that detects skipped or stalled cycles and routes notifications before silent failures degrade system reliability.
- **Keepalive Jobs**: Frequent, lightweight health checks that maintain active sessions, renew authentication tokens, and verify external integration uptime.

## Sources

- `2026-04-05-timekeeper-scheduling-proposal.md`
