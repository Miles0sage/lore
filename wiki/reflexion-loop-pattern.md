---
id: reflexion-loop-pattern
title: Reflexion Loop Pattern for AI Agents
tags:
  - reflexion
  - self-critique
  - quality
  - iteration
  - production
---

# Reflexion Loop Pattern for AI Agents

## What It Is

Reflexion extends the basic ReAct loop with self-critique. After each attempt, the agent evaluates its own output, identifies what went wrong, and stores that evaluation as a memory that informs the next attempt.

```
Attempt 1 → Evaluate → Reflect ("I forgot to check X")
    │
    ▼
Attempt 2 (with reflection in context) → Evaluate → Reflect
    │
    ▼
Attempt 3 → Success (or max attempts reached)
```

The key insight: the agent's own critique is more useful than just retrying. The reflection is a structured note — what failed, why, what to do differently — not just a retry.

## Implementation

```bash
lore scaffold reflexion_loop
```

```python
agent = ReflexionAgent(
    tools=[search_tool, code_tool],
    max_attempts=3,
    evaluator="self"  # or pass a separate evaluator model
)

result = await agent.run("Write a Python function to parse ISO 8601 dates")
# Attempt 1: produces function with no timezone handling
# Reflection: "Failed edge case: timezone-aware datetimes. Add pytz handling."
# Attempt 2: adds timezone handling, passes evaluator
# → Returns improved output
```

## Production Considerations

**Max attempts**: Always set a hard limit. Without it, a reflexion loop on a hard problem will iterate until budget exhaustion.

**Cost per attempt**: Each attempt costs tokens. With a `CostGuard` and `max_attempts=3`, the worst case is 3x a single attempt. Plan for this.

**Evaluation quality**: Self-evaluation is good enough for code correctness (run the tests) and factual tasks (check against sources). For subjective quality, use a separate evaluator model or human-in-the-loop.

**Memory persistence**: Reflexion is most powerful when reflections persist across sessions. Wire to `three_layer_memory` to store reflections in episodic memory.

## When to Use It

- Code generation where you can run tests to evaluate correctness
- Tasks with a clear success criterion (passes tests, answers a factual question correctly)
- Anywhere a single attempt fails consistently but a second attempt with the failure note would succeed

For multi-model quality gates, see `reviewer_loop`. For simpler retry logic, see `circuit_breaker`.
