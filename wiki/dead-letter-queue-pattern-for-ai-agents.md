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
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: dead-letter-queue-pattern-for-ai-agents
sources:
- raw/2026-04-05-dead-letter-queue.md
status: published
title: Dead Letter Queue Pattern for AI Agents
updated: '2026-04-05'
---

# Dead Letter Queue Pattern for AI Agents

## Overview
A Dead Letter Queue (DLQ) is an error-isolation pattern where tasks that fail beyond a configurable retry threshold are routed to a separate queue for asynchronous inspection, replay, or discard. In AI agent systems, DLQs prevent individual task failures from blocking the main processing pipeline.

## Why AI Agents Need DLQs
AI agents encounter failure modes absent in traditional software, including non-deterministic LLM outputs, context window overflows, tool timeouts, and malformed JSON from model responses. Without a DLQ, a single poisoned task can stall an entire worker queue. The DLQ functions as a pressure valve, ensuring failed tasks exit the hot path immediately and are processed out-of-band.

## Core Components
- **Retry counter**: Tracks the attempt count per task. Features a configurable threshold, typically set to 3-5.
- **DLQ storage**: A dedicated queue or table (e.g., Redis list, Postgres table, SQS DLQ) that stores failed tasks alongside full error context.
- **Error envelope**: Metadata attached at the time of failure, containing the original task, error type, stack trace, timestamp, attempt count, and worker ID.
- **DLQ consumer**: A separate process that inspects DLQ items, classifies failures, and routes them to replay, manual review, or discard.

## Failure Classification
DLQ consumers categorize failures into three distinct types:
- **Transient**: Includes network timeouts and rate limit 429 errors. Safe to replay after a backoff window.
- **Permanent**: Includes malformed input, schema mismatches, and context overflows. Cannot succeed without task modification and must be routed to human review.
- **Ambiguous**: Includes LLM hallucinations and tools returning unexpected formats. Requires a single replay with a modified prompt or different model; escalation occurs if the second attempt fails.

## Implementation Pattern
```python
async def process_task(task, retry_count=0, max_retries=3):
    try:
        result = await agent.run(task)
        return result
    except Exception as e:
        if retry_count >= max_retries:
            await dlq.push({
                "task": task,
                "error": str(e),
                "error_type": classify_error(e),
                "attempts": retry_count + 1,
                "timestamp": time.time()
            })
            return None
        await asyncio.sleep(2 ** retry_count)  # exponential backoff
        return await process_task(task, retry_count + 1, max_retries)
```

## Integration with Circuit Breaker
The DLQ and Circuit Breaker patterns are complementary:
- The Circuit Breaker halts traffic to a failing tool at the system level.
- The DLQ captures individual task failures and preserves them for later replay.
- Once the circuit closes, the DLQ consumer can replay the accumulated failed tasks.

## Production Considerations
- **DLQ TTL**: Items should expire after 7-30 days to prevent unbounded storage growth.
- **Alerting**: Configure alerts for DLQ depth exceeding a defined threshold (e.g., > 100 items triggers a paging incident).
- **Replay idempotency**: Tasks must be safe for repeated execution. Implement task IDs and idempotency keys.
- **Observability**: DLQ depth serves as a leading indicator of system health and should be tracked in operational dashboards.

## Framework Implementations
- **AI Factory**: Implements DLQ as a Postgres table utilizing a status column (`pending`/`dlq`/`replayed`).
- **Celery**: Provides built-in dead letter support via `task_reject_on_worker_lost` and custom error handlers.
- **AWS SQS**: Offers native DLQ support with a configurable `maxReceiveCount`.
- **LangGraph**: Lacks native DLQ functionality; requires implementation via a conditional edge routing to an error state node.

## Key Concepts
[[dead-letter-queue]]
[[error-isolation]]
[[retry-threshold]]
[[failure-classification]]
[[circuit-breaker-pattern]]
[[replay-idempotency]]
[[observability]]
[[exponential-backoff]]

## Sources
- 2026-04-05-dead-letter-queue.md
