---
backlinks: []
concepts:
- aws lambda
- tool health monitoring
- state machine
- langgraph
- circuit breaker pattern
- ai factory
- exponential backoff
- dynamodb
- dead letter queue
confidence: high
created: '2026-04-05'
domain: ai-agents
id: circuit-breaker-pattern-for-ai-agents
sources:
- raw/2026-04-05-circuit-breaker-pattern-for-ai-agents.md
- raw/2026-04-05-circuit-breaker-pattern-github.md
status: published
title: Circuit Breaker Pattern for AI Agents
updated: '2026-04-06'
---

# Circuit Breaker Pattern for AI Agents

## Overview

The Circuit Breaker is a fault-tolerance pattern that stops requests from reaching a failing component and returns a fast fallback instead. In AI agent systems it is not optional — without it, a single slow tool can exhaust your entire token budget while worker threads pile up waiting on timeouts.

The pattern is named after an electrical breaker: when current (traffic) exceeds a safe threshold, the breaker trips (opens), protecting the rest of the circuit.

## State Machine

```
         failures >= threshold
CLOSED ─────────────────────────► OPEN
  ▲                                  │
  │  probe succeeds                  │ recovery_timeout elapses
  │                                  ▼
  └──────────────────────── HALF_OPEN
         probe fails → OPEN
```

| State | Behaviour |
|-------|-----------|
| **CLOSED** | All calls pass through. Failure counter increments on each error; resets on success. |
| **OPEN** | All calls are rejected immediately with a `CircuitOpenError`. No downstream contact. |
| **HALF_OPEN** | One probe call is allowed. Success → CLOSED. Failure → OPEN again. |

## Minimal Python Implementation

```python
import time
from enum import Enum

class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, name, failure_threshold=3, recovery_timeout=30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = State.CLOSED
        self._failures = 0
        self._opened_at = None

    @property
    def state(self):
        if self._state == State.OPEN:
            if time.time() - self._opened_at >= self.recovery_timeout:
                self._state = State.HALF_OPEN
        return self._state

    def call(self, fn, *args, **kwargs):
        if self.state == State.OPEN:
            raise CircuitOpenError(f"{self.name} is OPEN")
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        self._failures = 0
        self._state = State.CLOSED

    def _on_failure(self):
        self._failures += 1
        if self._failures >= self.failure_threshold or self._state == State.HALF_OPEN:
            self._state = State.OPEN
            self._opened_at = time.time()

class CircuitOpenError(Exception):
    pass
```

## Production Advice

**Tune thresholds per tool, not globally.** An LLM API tolerates 5 failures before opening; a database connection should open after 2. One global setting leaves you either too sensitive or too permissive.

**Persist state across restarts.** An in-memory breaker resets to CLOSED when your process restarts — potentially sending a wave of traffic to a still-broken service. Use Redis, DynamoDB, or a Postgres row to store `(state, opened_at, failure_count)`.

**Emit metrics on every transition.** The breaker state is one of the most useful signals in your system. Log `breaker_opened`, `breaker_closed`, `breaker_probe_sent` events. Alert when a circuit stays open for more than 2x the recovery timeout.

**Pair with exponential backoff on the caller side.** The breaker prevents *new* calls from hitting a dead service; backoff prevents the retry storm when the breaker re-closes.

**Return a useful fallback, not just an error.** When OPEN, return cached data, a degraded response, or queue the task for later. Throwing an exception to the end user is often worse than a stale answer.

## Common Mistakes

- **Sharing one breaker across all tools.** A slow vector DB should not trip the breaker for your LLM calls. One breaker instance per external dependency.
- **Setting `recovery_timeout` too short.** 5 seconds is almost always too fast. Services under load need 30–120 seconds to drain their queues. Start at 60s and tune down.
- **Not resetting the failure counter on success.** If you only increment failures and never reset them, intermittent errors will eventually open the circuit even on a healthy service.
- **Wrapping the breaker in a try/except that swallows `CircuitOpenError`.** Your calling code must distinguish between "downstream failed" (retry later) and "circuit open" (don't retry yet).

## When to Use

Use when:
- Calling any external API or tool that can be slow or unavailable
- Managing a worker pool where one bad worker shouldn't stall the queue
- Protecting LLM API calls from quota exhaustion cascades

Do NOT use when:
- The operation is idempotent and cheap to retry with no downstream risk
- Latency is dominated by your own computation, not network calls
- You need to propagate errors immediately for correctness (e.g., payment validation)

## Complementary Patterns

- **[[Dead Letter Queue]]** — captures tasks blocked by the open circuit for later replay
- **[[Tool Health Monitoring]]** — feeds real-time success rate data back to breaker thresholds
- **[[Exponential Backoff]]** — governs retry timing after the circuit re-closes
- **[[Supervisor-Worker Pattern]]** — the supervisor checks breaker state before dispatching

## Working Example

```bash
python3 examples/resilient_api_client/main.py
```

## Key Concepts
[[Circuit Breaker Pattern]] [[State Machine]] [[Dead Letter Queue]] [[Tool Health Monitoring]] [[Exponential Backoff]] [[LangGraph]] [[AI Factory]] [[AWS Lambda]] [[DynamoDB]]

## Sources
- `2026-04-05-circuit-breaker-pattern-for-ai-agents.md`
- `2026-04-05-circuit-breaker-pattern-github.md`
