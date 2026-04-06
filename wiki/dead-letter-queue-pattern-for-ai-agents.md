---
backlinks: []
concepts:
- exponential-backoff
- replay-idempotency
- observability
- error-isolation
- circuit-breaker-pattern
- dead-letter-queue
- failure-classification
- retry-threshold
confidence: high
created: '2026-04-05'
domain: ai-agents
id: dead-letter-queue-pattern-for-ai-agents
sources:
- raw/2026-04-05-dead-letter-queue.md
status: published
title: Dead Letter Queue Pattern for AI Agents
updated: '2026-04-06'
---

# Dead Letter Queue Pattern for AI Agents

## Overview

A Dead Letter Queue (DLQ) is an error-isolation pattern: tasks that fail beyond a configurable retry threshold are moved to a separate queue for asynchronous inspection, replay, or discard. The main processing pipeline never stalls waiting on a poisoned task.

In AI agent systems the DLQ is especially important because failure modes are unlike traditional software. A task can fail due to non-deterministic LLM output, context window overflow, rate-limit exhaustion, or malformed JSON — none of which benefit from an immediate retry in the same way a network blip would.

## Core Components

```
  main queue ──► worker ──► retry (N times) ──► DLQ ──► consumer
                                                           │
                               ┌───────────────────────────┤
                               ▼           ▼               ▼
                           replay      human review     discard
                         (transient)   (permanent)   (ambiguous)
```

| Component | Responsibility |
|-----------|----------------|
| **Retry counter** | Tracks attempt count per task. Configurable threshold (default: 3). |
| **Error envelope** | Metadata snapshot at failure time: task ID, error type, stack trace, timestamp, worker ID, attempt count. |
| **DLQ storage** | Dedicated queue or table: Redis list, Postgres table with `status` column, SQS DLQ. |
| **DLQ consumer** | Out-of-band process that classifies failures and routes to replay / review / discard. |

## Failure Classification

Classification is the critical step that makes DLQ replay safe:

| Class | Examples | Action |
|-------|----------|--------|
| **Transient** | Network timeout, HTTP 429, DB connection refused | Replay after backoff window |
| **Permanent** | Malformed input, schema mismatch, context overflow | Route to human review; do not replay |
| **Ambiguous** | LLM hallucination, unexpected tool output format | Replay once with modified prompt or different model; escalate on second failure |

Misclassifying a permanent failure as transient is the most common DLQ mistake — you end up replaying bad input forever.

## Implementation Pattern

```python
import time, asyncio

async def process_task(task, dlq, retry_count=0, max_retries=3):
    try:
        result = await agent.run(task)
        return result
    except Exception as e:
        if retry_count >= max_retries:
            # Exhausted — move to DLQ with full context
            await dlq.push({
                "task":       task,
                "error":      str(e),
                "error_type": classify_error(e),   # "transient" | "permanent" | "ambiguous"
                "attempts":   retry_count + 1,
                "timestamp":  time.time(),
                "worker_id":  worker.id,
            })
            return None
        # Exponential backoff before retry
        await asyncio.sleep(2 ** retry_count)
        return await process_task(task, dlq, retry_count + 1, max_retries)


async def consume_dlq(dlq):
    """Out-of-band consumer — runs as a separate process or cron."""
    entries = await dlq.drain()
    for entry in entries:
        if entry["error_type"] == "transient":
            await replay(entry["task"])
        elif entry["error_type"] == "permanent":
            await notify_human(entry)
        else:
            await replay_with_modified_prompt(entry["task"])
```

## Production Advice

**Make tasks idempotent before you need the DLQ.** Replay is only safe if running a task twice produces the same outcome. Add a `task_id` to every task and check for it at the start of execution: `if already_processed(task_id): return cached_result`.

**Set a DLQ TTL.** Items should expire after 7–30 days. Without a TTL your DLQ grows unboundedly. Archive expired items instead of deleting them — you may need them for post-mortems.

**Alert on DLQ depth, not just errors.** Individual errors are noise. A DLQ depth above 50 items indicates systemic failure and should page someone. Track `dlq_depth` as a first-class metric in your dashboard.

**Don't replay during a live incident.** If 500 tasks are in the DLQ because your LLM provider is down, replaying them the moment it comes back creates a thundering herd. Replay gradually — 10 tasks/minute — and watch error rates before increasing.

**Separate DLQs per task type.** A malformed tool-call task and a rate-limited LLM task should not share a queue. They have different retry windows, different consumer logic, and different escalation paths.

## Common Mistakes

- **Retrying inside the hot path instead of using a DLQ.** Synchronous retries block the worker thread. Move anything beyond 1–2 retries out of band.
- **Not capturing the full error envelope.** If you only log the error message, you lose the stack trace, the task payload, and the worker context you need to debug the failure.
- **Replaying without re-classification.** A task that was "transient" at 2am may be "permanent" at 2pm if input data changed. Re-classify at replay time.
- **Letting the DLQ consumer crash silently.** The consumer is a background process. If it dies and nobody notices, your DLQ fills up and items expire unprocessed. Monitor consumer liveness.

## When to Use

Use when:
- Tasks can fail for reasons outside your control (external APIs, LLM non-determinism)
- Worker queue depth matters and you cannot afford to block on retries
- You need an audit trail of every failure for debugging or compliance

Do NOT use when:
- Tasks are pure in-process computation with no external calls — just let exceptions propagate
- Failures must be handled synchronously for correctness (e.g., a payment that either commits or rolls back)
- Your task volume is so low that a simple try/except with logging is sufficient

## Integration with Circuit Breaker

The two patterns are complementary, not redundant:

- **Circuit Breaker** halts traffic at the *system* level when a tool is unhealthy
- **DLQ** captures *individual* task failures for later replay

Workflow: circuit opens → new tasks are blocked → when circuit closes → DLQ consumer replays accumulated failures gradually.

## Framework Implementations

- **AI Factory** — Postgres table with `status` column (`pending` / `dlq` / `replayed`)
- **Celery** — `task_reject_on_worker_lost` + custom error handlers
- **AWS SQS** — native DLQ with configurable `maxReceiveCount`
- **LangGraph** — no native support; add a conditional edge routing to an `error_state` node

## Working Example

```bash
python3 examples/multi_agent_pipeline/main.py
```

## Key Concepts
[[dead-letter-queue]] [[error-isolation]] [[retry-threshold]] [[failure-classification]] [[circuit-breaker-pattern]] [[replay-idempotency]] [[observability]] [[exponential-backoff]]

## Sources
- 2026-04-05-dead-letter-queue.md
