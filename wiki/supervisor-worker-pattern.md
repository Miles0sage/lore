---
backlinks: []
concepts:
- langgraph
- model routing
- reviewer loop
- handoff pattern
- circuit breaker
- dead letter queue
- tool health monitoring
confidence: high
created: '2026-04-04'
domain: ai-agents
id: supervisor-worker-pattern
sources:
- raw/2026-04-04-ai-agent-frameworks-2026.md
status: published
title: Supervisor-Worker Pattern
updated: '2026-04-06'
---

# Supervisor-Worker Pattern

## Definition

One supervising agent decomposes work, selects which worker should act next, and aggregates results. Workers are narrow specialists — they do one thing well and know nothing about the broader task.

This is the **default orchestration pattern** for production multi-agent systems because it is easier to debug than peer-to-peer swarms and cheaper than routing every step through an expensive model.

## Why It Works

The supervisor acts as the control plane. It holds context, makes routing decisions, and handles failure. Workers are execution units — stateless, replaceable, and auditable in isolation.

This separation gives you:
- **Debuggability** — routing decisions live in one place, not scattered across agents
- **Cost control** — expensive reasoning only happens in the supervisor; workers use cheap specialist models
- **Fault isolation** — a broken worker doesn't corrupt the supervisor's state
- **Reusability** — a well-scoped worker can serve multiple supervisors

## Typical Workflow

```
                ┌─────────────────────┐
  task ────────►│      SUPERVISOR     │◄──── retries / escalation
                │  (control plane)    │
                └──────┬──────────────┘
                       │ dispatch
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      worker-A      worker-B     worker-C
     (research)    (codegen)    (review)
          │            │            │
          └────────────┴────────────┘
                       │ results
                ┌──────▼──────────────┐
                │  SUPERVISOR merges  │
                │  validates, retries │
                └─────────────────────┘
```

1. Supervisor receives task and evaluates scope
2. Selects worker(s) — parallel fan-out is common
3. Workers execute bounded subtasks and return results
4. Supervisor validates, merges, retries, or escalates
5. Loop through a [[Reviewer Loop]] if quality gates are required

## Minimal Python Skeleton

```python
class Supervisor:
    def __init__(self, workers: dict[str, WorkerAgent]):
        self.workers = workers

    def run(self, task: str) -> str:
        # 1. Decompose
        steps = self._plan(task)

        results = []
        for step in steps:
            worker = self._route(step)
            try:
                result = worker.run(step)
                results.append(result)
            except WorkerError as e:
                if e.is_retryable:
                    result = worker.run(step)  # one retry
                    results.append(result)
                else:
                    self.dlq.push(step, error=e)

        return self._aggregate(results)

    def _route(self, step: str) -> WorkerAgent:
        # Model routing: cheap worker for simple steps, strong for complex
        if "code" in step:
            return self.workers["codegen"]
        return self.workers["default"]
```

## Production Advice

**Give the supervisor a strict budget.** Without a cap on retries and total steps, a confused supervisor will spin forever. Set `max_retries=2` per worker call and `max_steps=20` per task.

**Use model routing for cost control.** The supervisor needs to reason about task decomposition — use Sonnet or Opus there. Workers executing bounded subtasks can run on Haiku or a fine-tuned specialist. This alone can cut costs 3–5x.

**Keep workers truly stateless.** If a worker needs memory of previous calls, you have a design smell. The supervisor should pass all necessary context in each dispatch. Stateless workers can be replaced, scaled, and tested in isolation.

**Implement health checks per worker.** Before dispatching to a worker, check if it has been failing recently. Combine with [[Circuit Breaker]] logic so a broken worker gets bypassed rather than retried indefinitely.

**Emit a dispatch log.** Record every `(task_id, worker_name, attempt, result_status)` event. This log is your primary debugging tool when the system produces wrong results — you can replay the exact routing decisions.

## Common Mistakes

- **Making the supervisor too smart.** If the supervisor is doing the actual work, you've just moved complexity upward. The supervisor should *route and validate*, not *execute*.
- **Workers that call other workers directly.** This creates hidden peer-to-peer dependencies that are impossible to observe. All routing must flow through the supervisor.
- **No timeout on worker calls.** A hanging worker will freeze the supervisor. Always wrap worker calls in a timeout and treat a timeout as a retryable failure.
- **Returning raw worker output without validation.** Workers hallucinate and make schema errors. The supervisor must validate output before aggregating it.

## When to Use

Use when:
- Work can be decomposed into role-typed subtasks (research, write, review)
- You need auditability — who did what and in what order
- Tasks involve parallel execution with merging logic
- You want cost control through model routing

Do NOT use when:
- The task is inherently sequential with no branching — use a simple pipeline instead
- All agents need equal awareness of system state — use a shared blackboard or swarm
- Latency is the primary constraint and supervisor overhead is unacceptable

## Reliability Requirements

This pattern is only as robust as its failure handling:

- Wrap all worker calls in [[Circuit Breaker]] logic
- Route exhausted tasks to a [[Dead Letter Queue]]
- Monitor worker quality with [[Tool Health Monitoring]]
- Cap retries and total iterations unconditionally

Without those controls, a confused supervisor amplifies failures into higher cost and deeper retry loops.

## Working Example

```bash
python3 examples/multi_agent_pipeline/main.py
```

## Key Concepts
[[LangGraph]] [[Model Routing]] [[Reviewer Loop]] [[Handoff Pattern]] [[Circuit Breaker]] [[Dead Letter Queue]] [[Tool Health Monitoring]] [[AI Agent Frameworks & Patterns 2026]]

## Sources
- raw/2026-04-04-ai-agent-frameworks-2026.md
