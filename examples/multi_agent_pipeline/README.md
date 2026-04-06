# Multi-Agent Pipeline — Supervisor + Workers + DLQ

Demonstrates the **Supervisor-Worker** pattern combined with a **Dead Letter Queue**,
using pure Python stdlib.

## What it shows

| Phase | Description |
|-------|-------------|
| 1 | Supervisor dispatches 10 tasks to a round-robin worker pool |
| 2 | Workers fail stochastically; supervisor retries with backoff |
| 3 | Exhausted tasks are routed to the Dead Letter Queue with error context |
| 4 | DLQ consumer classifies failures (transient / permanent / ambiguous) |
| 5 | Transient failures are replayed; permanent failures flagged for human review |

## Run

```bash
python3 examples/multi_agent_pipeline/main.py
```

## Key classes

- `Supervisor` — control plane: dispatches, retries, routes to DLQ
- `WorkerAgent` — narrow specialist with configurable failure rate
- `DeadLetterQueue` — captures exhausted tasks with full error context
- `replay_dlq` — out-of-band consumer that classifies and replays

## Related patterns

- `wiki/supervisor-worker-pattern.md`
- `wiki/dead-letter-queue-pattern-for-ai-agents.md`
