---
title: "We Audited CrewAI's Source Code. Here's What We Found."
date: 2026-04-07
tags: [crewai, audit, reliability, circuit-breaker, cost-guard, production]
summary: A real code-level audit of CrewAI's reliability patterns. Token tracking exists. Cost guards don't. Here's the diff that matters.
---

# We Audited CrewAI's Source Code. Here's What We Found.

CrewAI is one of the most popular multi-agent frameworks in production today. 25,000+ GitHub stars. Used in real pipelines at real companies.

We cloned the repo and ran `lore audit` on it. Here's the machine output, then we'll show you what it means in practice.

```bash
$ git clone https://github.com/crewAIInc/crewAI /tmp/crewai
$ lore audit /tmp/crewai
```

---

## The Audit Output

```
Framework: CrewAI (github.com/crewAIInc/crewAI)
Commit:    main, April 2026
Files:     50 scanned, 180k chars

CRITICAL  Loss of Observability: Webhook URLs are not persisted on HITL Resume
HIGH      Missing Tool-Level Failure Isolation
MEDIUM    In-Code Telemetry Configuration is Not Supported

Suggested fixes:
  lore scaffold circuit_breaker
  lore scaffold dead_letter_queue
  lore scaffold sentinel_observability
  lore install --patterns circuit_breaker,dead_letter_queue,sentinel_observability

Saved: .lore/audits/20260407-crewai-audit.json
```

Then we read the source to understand each finding.

---

## The Scorecard

```
Framework: CrewAI (github.com/crewAIInc/crewAI)
Commit:    main, April 2026
Audited:   lib/crewai/src/crewai/

Pattern               Status    File
─────────────────────────────────────────────────────────
Circuit Breaker       MISSING   —
Cost Guard            MISSING   —
Dead Letter Queue     MISSING   —
HITL Webhook Persist  MISSING   — (CRITICAL)
RPM Rate Limiter      PRESENT   utilities/rpm_controller.py
Token Counter         PRESENT   utilities/token_counter_callback.py
Telemetry             PARTIAL   telemetry/telemetry.py
Retry Logic           PARTIAL   tools/tool_usage.py
─────────────────────────────────────────────────────────
Lore Score:  3 / 8 patterns present
```

---

## The Critical Finding: HITL Webhook Loss

The most dangerous gap is one you'd never find reading the docs.

CrewAI supports Human-in-the-Loop (HITL) — a crew can pause mid-execution, send a webhook to your system, and wait for a human to approve before continuing.

The problem: **when the crew resumes, the webhook URL is gone.**

```python
# The flow: crew pauses → sends webhook → human approves → crew resumes
# What's lost on resume: the original webhook URL for the next pause
# Result: the second human approval never fires. The agent proceeds unilaterally.
```

In a production pipeline where HITL is your safety gate — approving purchases, confirming deletions, validating outputs — this is a silent failure. Your safety gate stops working after the first resume. You don't know until something goes wrong.

**The fix with Lore:**

```python
from lore import ObservabilityHub

hub = ObservabilityHub()

class PersistentHITLCrew(Crew):
    def before_kickoff(self, inputs):
        hub.checkpoint("hitl_webhook", {
            "url": self.config.webhook_url,
            "crew_id": self.id
        })
        return super().before_kickoff(inputs)

    def on_resume(self):
        config = hub.restore("hitl_webhook")
        self.config.webhook_url = config["url"]  # restored
        super().on_resume()
```

---

## What's There

### RPM Controller ✓

CrewAI has a solid rate limiter. It tracks requests per minute, blocks when the limit is hit, and resets cleanly.

```python
# lib/crewai/src/crewai/utilities/rpm_controller.py
class RPMController(BaseModel):
    max_rpm: int | None = Field(default=None)
    _current_rpm: int = PrivateAttr(default=0)
    _lock: "threading.Lock | None" = PrivateAttr(default=None)

    def check_or_wait(self) -> bool:
        # blocks until next minute if at limit
        ...
```

This is the right instinct. It prevents your agent from hammering the API when downstream is slow.

### Token Counter ✓

Token usage is tracked via a callback handler wired into the LLM call chain:

```python
# lib/crewai/src/crewai/utilities/token_counter_callback.py
class TokenCalcHandler(BaseCallbackHandler):
    def on_llm_end(self, response, **kwargs):
        usage = response_obj["usage"]
        self.token_cost_process.sum_prompt_tokens(usage.prompt_tokens)
        self.token_cost_process.sum_completion_tokens(usage.completion_tokens)
```

It counts. Every token. Accurately.

---

## What's Missing

### Circuit Breaker ✗

Zero hits for `CircuitBreaker`, `circuit_break`, or `OPEN`/`HALF_OPEN` state anywhere in the codebase.

```bash
$ grep -r "CircuitBreaker\|circuit_break" lib/crewai/src --include="*.py"
(no output)
```

What this means in practice: if your tool starts returning 500s, the agent keeps calling it. Every step. Until `max_retries` is exhausted — and then it returns an error string, not an exception. The loop continues.

```python
# lib/crewai/src/crewai/tools/tool_usage.py
try:
    return self._use(tool_string=tool_string, tool=tool, calling=calling)
except Exception as e:
    error = getattr(e, "message", str(e))
    if self.task:
        self.task.increment_tools_errors()
    return error  # ← returns error as a string, loop keeps going
```

The error counter increments. The loop doesn't stop. The API bill grows.

### Cost Guard ✗

Here's the gap: token counting exists, but there's no hard stop.

```python
# What exists:
self.token_cost_process.sum_prompt_tokens(usage.prompt_tokens)

# What's missing:
if total_tokens > budget:
    raise CostGuardExceeded("budget exhausted at step N")
```

The token counter is observational. It tells you what happened. It doesn't prevent runaway spend.

In a 10-agent crew running overnight, this is the difference between a $50 bill and a $2,000 bill.

### Dead Letter Queue ✗

When a task fails permanently in CrewAI, it fails inline. There's no mechanism to:
- Capture the failed task with its context
- Classify the failure (transient vs. permanent)
- Queue it for human review or replay

```bash
$ grep -r "dead_letter\|dlq\|failed_task" lib/crewai/src --include="*.py"
(no output)
```

A long-running research crew that hits one bad task will either retry forever or silently drop the result. There's no middle path.

---

## Adding the Missing Patterns

You can wire Lore's reliability harness onto CrewAI without modifying its source.

```bash
pip install lore-agents
```

### Circuit Breaker on Tool Calls

```python
from lore import CircuitBreaker

breaker = CircuitBreaker("crewai-tools")

class ProtectedTool(BaseTool):
    def _run(self, query: str) -> str:
        with breaker:
            return self.underlying_tool.run(query)
```

If the tool fails 5 times in 60 seconds, the circuit opens. Subsequent calls fail fast with `CircuitOpenError` instead of hammering the broken endpoint.

### Cost Guard on the Crew

```python
from lore import CostGuard

guard = CostGuard(budget_tokens=500_000, warn_at=0.80)

class GuardedCrew(Crew):
    def _run_agent_step(self, agent, task):
        result = super()._run_agent_step(agent, task)
        guard.consume(f"agent:{agent.role}", tokens=result.token_usage.total)
        return result
```

At 80% budget: logs a WARNING. At 100%: raises `CostGuardExceeded`. The crew stops before the damage is done.

### Dead Letter Queue for Failed Tasks

```python
from lore import DeadLetterQueue, FailureClass

dlq = DeadLetterQueue()

class ResilientCrew(Crew):
    def _handle_task_failure(self, task, error):
        failure_class = classify_error(error)  # TRANSIENT / PERMANENT / AMBIGUOUS
        dlq.enqueue(
            task_id=task.id,
            payload={"task": task.description, "error": str(error)},
            failure_class=failure_class
        )
        # human reviews via: lore dlq list
```

Failed tasks are captured, classified, and queued for review — not silently dropped.

---

## The Full Scaffold

```bash
lore scaffold react_loop     # single-agent loop with all guards
lore scaffold plan_execute   # planner + executor pattern
lore scaffold cost_guard     # standalone budget enforcement
lore scaffold circuit_breaker # standalone failure isolation
```

Each scaffold generates production-ready Python. Not pseudocode — runnable code with the patterns wired in.

---

## Why CrewAI Doesn't Have These

This isn't a criticism. It's a pattern.

Agent frameworks are built by researchers and developers who care deeply about **capability**: can the agent use tools? Can it plan? Can it delegate? Can it remember?

**Reliability** is an operational concern. It surfaces when you're running agents in production, getting paged at 2am, and tracing a $3,000 API bill back to a retry loop that ran for 6 hours.

CrewAI is excellent at what it's designed for. It needs a harness for what it's not.

That's Lore.

---

## Reproduce This Audit

```bash
pip install lore-agents
git clone https://github.com/crewAIInc/crewAI /tmp/crewai
lore audit /tmp/crewai
```

The audit runs locally. No data leaves your machine.

---

*Lore is an open-source reliability harness for AI agents. Patterns: circuit breaker, cost guard, dead letter queue, observability, three-layer memory.*

*[GitHub](https://github.com/agentsmodelssystems/lore-agents) · [PyPI](https://pypi.org/project/lore-agents/) · [Docs](https://agentsmodelssystems.github.io/lore-agents/)*
