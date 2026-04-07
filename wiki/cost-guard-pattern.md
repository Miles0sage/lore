---
id: cost-guard-pattern
title: Cost Guard Pattern for AI Agents
tags:
  - cost-guard
  - budget
  - token-limits
  - production
  - The Timekeeper
---

# Cost Guard Pattern for AI Agents

## The 10/10 Finding

We audited 10 open-source agent frameworks. Cost guards were missing in every single one. Not partial — absent. This is the most universally skipped production control in the AI agent ecosystem.

The risk is well understood: autonomous agents making LLM calls in a loop can burn through API budgets rapidly when something goes wrong upstream. A single stuck retry loop hitting a degraded API can generate hundreds of dollars in charges overnight with zero useful output.

## What a Cost Guard Does

A cost guard tracks token consumption per step, warns when a configurable threshold is crossed, and raises a hard-stop exception before the budget is fully exhausted.

Three responsibilities:

1. **Track**: count tokens consumed at each named step
2. **Warn**: emit a log warning when consumption crosses `warn_at` fraction of budget (default 80%)
3. **Stop**: raise `CostGuardExceeded` when the hard budget is hit

## Implementation

```bash
lore scaffold cost_guard
```

Core interface:

```python
guard = CostGuard(budget_tokens=100_000, warn_at=0.80)

# Before or after each LLM call:
guard.consume("summarize_step", tokens=response.usage.total_tokens)

# Check remaining budget:
guard.warn_if_low()       # logs WARNING if >80% used
print(guard.summary())    # full per-step breakdown
```

The exception carries context:

```python
# CostGuardExceeded: budget exhausted at step 'summarize_step'
# — used 100,847 / 100,000 tokens (100.8%)
```

## When to Use It

- Any autonomous loop making LLM calls without a human in the path
- Research agents, document processing pipelines, multi-step planners
- Any agent with a `--continuous` or equivalent mode
- Production deployments where API cost is unbounded by default

## Integration Points

Wire `guard.consume()` at two points:

1. **After each LLM response** — use `response.usage.total_tokens` from the OpenAI/Anthropic SDK
2. **Before expensive tool calls** — estimate cost and pre-check with `guard.check(estimated_tokens)`

## Relationship to Other Patterns

Cost guard is complementary to the circuit breaker. The circuit breaker stops calls when a downstream dependency is failing. The cost guard stops calls when your own budget is exhausted. In a production agent you want both:

- Circuit breaker: stops the cascade when the API returns 429s
- Cost guard: stops the spend when retries keep burning tokens despite the cascade

## The Archetype: The Timekeeper

The Timekeeper enforces budgets before time and money run out. Not reactive — proactive. The Timekeeper doesn't wait for the bill. It watches every step and closes the gate before the damage is done.

See also: `circuit_breaker`, `dead_letter_queue`, `sentinel_observability`
