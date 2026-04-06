# Resilient API Client — Circuit Breaker Example

Demonstrates the **Circuit Breaker** pattern using pure Python stdlib.

## What it shows

| Phase | Description |
|-------|-------------|
| 1 | Healthy traffic — breaker stays CLOSED |
| 2 | Service degrades — breaker trips to OPEN after 3 consecutive failures |
| 3 | Recovery timeout elapses — breaker moves to HALF_OPEN |
| 4 | Single probe succeeds — breaker closes, traffic resumes |

## Run

```bash
python3 examples/resilient_api_client/main.py
```

## Key classes

- `CircuitBreaker` — three-state machine (CLOSED / OPEN / HALF_OPEN)
- `CircuitOpenError` — raised when a call is blocked by an open circuit
- `fake_http_get` — simulated HTTP endpoint with configurable failure rate

## Related pattern

See `wiki/circuit-breaker-pattern-for-ai-agents.md` for production guidance.
