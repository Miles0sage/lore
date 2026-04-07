---
id: plan-execute-pattern
title: Plan-Execute Pattern for AI Agents
tags:
  - planning
  - execution
  - multi-step
  - agent-architecture
  - production
---

# Plan-Execute Pattern for AI Agents

## What It Is

Plan-Execute separates the agent's planning phase from its execution phase. A planner LLM produces a structured task list. An executor (which may be a different, cheaper model) works through the tasks step by step.

```
User Goal
    │
    ▼
[Planner LLM]
    │ produces
    ▼
Task 1 → Task 2 → Task 3 → ... → Task N
    │
    ▼
[Executor LLM + Tools]
    │ executes each task
    ▼
Results → Final Answer
```

## Why Separate Planning from Execution

**Cost**: Planning requires high-capability models (GPT-5, Claude Opus). Execution of individual steps often doesn't. Route planning to a capable model, execution to a cheaper one.

**Reliability**: A plan is inspectable. You can validate it before execution begins. You can re-plan if a step fails without restarting the entire pipeline.

**Parallelism**: Independent tasks in the plan can run concurrently.

## Implementation

```bash
lore scaffold plan_execute
```

```python
planner = PlanExecuteAgent(
    planner_model="gpt-4.1",      # capable model for planning
    executor_model="gpt-4.1-mini", # cheaper model for steps
    tools=[search, calculate, write_file]
)

result = await planner.run("Write a research report on quantum computing trends")
# → Planner produces 6-step plan
# → Executor runs each step, collecting results
# → Final synthesis combines step outputs
```

## Production Considerations

**Re-planning on failure**: If a step fails, the agent should re-plan from the current state, not restart from scratch. Implement a `replan_on_failure` flag.

**Plan validation**: Before execution, validate the plan. Check that all required tools exist, that steps are logically ordered, that the plan is not circular.

**Cost guard**: Wire a `CostGuard` across the full plan-execute cycle. Both phases burn tokens.

**DLQ for failed steps**: Steps that fail permanently (not transient errors) go to the dead letter queue for human review rather than blocking the whole plan.

## When to Use It

- Long-horizon tasks requiring multiple distinct steps
- Tasks where planning and execution have different model requirements
- Workflows where you want to inspect or modify the plan before running
- Pipelines where steps can run in parallel

For simpler single-loop tasks, see `react_loop`. For multi-agent fan-out, see `supervisor_worker`.
