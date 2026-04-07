---
title: "Your AI agent has no cost guard. Here's how to add one in 60 seconds."
created_at: 2026-04-07
author: lore
tags: [ai-agents, reliability, python, production, open-source]
status: draft
---

# Your AI agent has no cost guard. Here's how to add one in 60 seconds.

We audited 10 of the most widely-used open-source agent frameworks. Circuit breakers: 8/10 missing. Dead letter queues: 9/10 missing. Cost guards: **10 out of 10 missing.**

Not partial. Not undocumented. Zero. None of them ship with a mechanism to say: *if this agent spends more than $X or makes more than N API calls, stop.*

This post is the fix. Five minutes, four commands, zero new dependencies.

---

## Install

```bash
pip install lore-agents
```

That's it. Pure Python. Zero mandatory dependencies. Works as a CLI or as an MCP server for Claude Code, Cursor, or any assistant.

---

## The 10/10 finding: cost guards

The `lore audit` finding on AutoGPT was the starkest:

> *"The `--continuous` flag enables fully autonomous operation but there are no documented, mandatory safeguards like API spend limits, action counters, or automatic shutdown on repeated errors. This creates a dangerous execution path that can lead to runaway API costs."*

A cost guard is not complicated. It's a counter with a threshold check before each API call. But it needs to be first-class — part of the execution model, not a wrapper bolted on from outside.

Here's the one Lore generates:

```bash
lore scaffold cost_guard
```

Output:

```python
"""
LORE SCAFFOLD: cost_guard — Hard-Stop Cost Protection for Production AI Agents

The Timekeeper's budget enforcer. Tracks token consumption per step, warns at
configurable thresholds, and raises CostGuardExceeded before an agent can
silently burn through its entire budget.

Cost guards missing in 10/10 production agent repos audited. This is the fix.
"""

class CostGuardExceeded(Exception):
    """Raised when the agent's token budget is exhausted."""

    def __init__(self, used: int, budget: int, step: str = "") -> None:
        self.used = used
        self.budget = budget
        self.step = step
        pct = 100.0 * used / budget if budget else 0.0
        where = f" at step '{step}'" if step else ""
        super().__init__(
            f"CostGuard: budget exhausted{where} — used {used:,} / {budget:,} tokens ({pct:.1f}%)"
        )


class CostGuard:
    """Hard-stop cost protection for production AI agents.

    Tracks token consumption step-by-step, emits a warning when the warn
    threshold is crossed, and raises CostGuardExceeded when the hard budget
    is hit. Zero external dependencies — drop into any Python agent project.

    Args:
        budget_tokens: Hard-stop limit. Raises CostGuardExceeded when exceeded.
        warn_at: Fraction of budget that triggers a warning log (default 0.80).
        name: Optional label for this guard, used in log messages.
    """
```

Drop this into your agent. Wire `guard.consume("step_name", tokens=response.usage.total_tokens)` before every LLM call. Done.

---

## The cascade problem: circuit breakers

Cost guards stop runaway spending. Circuit breakers stop cascade failures — when one dependency is degraded, don't let it drag everything else down.

```bash
lore scaffold circuit_breaker
```

Output:

```python
"""
Circuit Breaker Pattern — The Breaker, Guardian of the Gate

Prevents cascading failures by monitoring request success rates and
interrupting traffic to failing components. Three states: CLOSED (normal),
OPEN (gate sealed), HALF_OPEN (single probe to test recovery).

Systems without circuit breakers experience 76% failure rates in production.
"""

class CircuitState(Enum):
    CLOSED = "CLOSED"       # Normal operation, requests flow freely
    OPEN = "OPEN"           # Gate sealed, returns fallback immediately
    HALF_OPEN = "HALF_OPEN" # Single probe allowed to test recovery


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5           # Failures before opening
    recovery_wait_seconds: float = 30.0  # Wait before HALF_OPEN probe
    success_threshold: int = 1           # Successes in HALF_OPEN to close
```

Usage:

```python
breaker = CircuitBreaker(name="openai_api")
result = await breaker.call(my_llm_call, prompt)
```

When `openai_api` hits 5 consecutive failures, the breaker opens. For the next 30 seconds, every call returns the fallback immediately — no wasted tokens, no cascade. After 30 seconds, one probe goes through. If it succeeds, the gate reopens.

---

## The silent failure problem: dead letter queues

Without a DLQ, failed tasks have three bad outcomes: retry forever (resource exhaustion), discard silently (data loss), or crash the pipeline (operational disruption).

```bash
lore scaffold dead_letter_queue
```

```python
"""
Dead Letter Queue Pattern — The Archivist, Keeper of Lost Messages

Error-isolation pattern where tasks that fail beyond retry threshold
are routed to a separate queue for inspection, replay, or discard.
Nothing is destroyed. Everything waits to be understood.
"""

class FailureClass(Enum):
    TRANSIENT = "transient"   # Safe to replay (network timeout, 429)
    PERMANENT = "permanent"   # Cannot succeed without modification
    AMBIGUOUS = "ambiguous"   # Replay once with modified prompt
```

The Archivist classifies every failure. TRANSIENT errors (rate limits, timeouts) go to replay queue. PERMANENT errors (schema violations, malformed input) go to human review. AMBIGUOUS errors get one more shot with a modified prompt. Nothing disappears silently.

---

## All 19 patterns

```bash
lore scaffold --list
```

```
Pattern                             Archetype            Frameworks
--------------------------------------------------------------------------------
alchemist_prompt_routing            The Alchemist        python
architect_system_design             The Architect        python
cartographer_knowledge_graph        The Cartographer     python
circuit_breaker                     The Breaker          python, langgraph
cost_guard                          The Timekeeper       python
dead_letter_queue                   The Archivist        python
handoff_pattern                     The Weaver           python, crewai, openai_agents
librarian_retrieval                 The Librarian        python
model_routing                       The Router           python, openai_agents
plan_execute                                             python
react_loop                                               python
reflexion_loop                                           python
reviewer_loop                       The Council          python, langgraph, crewai
scout_discovery                     The Scout            python
sentinel_observability              The Sentinel         python
supervisor_worker                   The Commander        python, langgraph, crewai, openai_agents
three_layer_memory                  The Stack            python
timekeeper_scheduling               The Timekeeper       python
tool_health_monitor                 The Warden           python

19 patterns available.
```

Framework-specific variants:

```bash
lore scaffold supervisor_worker --framework langgraph
lore scaffold reviewer_loop     --framework crewai
lore scaffold handoff_pattern   --framework openai_agents
```

Write directly to a file:

```bash
lore scaffold circuit_breaker -o src/resilience.py
```

---

## Searchable knowledge base

76 production articles. Full-text BM25 search. Zero API calls.

```bash
lore search "cost guard" --limit 3
```

```
1. The Timekeeper: Scheduling Patterns for Proactive AI Agents
   (id: timekeeper-scheduling-pattern, score: 2.382)
   ...budget_tokens=100_000, warn_at=0.80 — hard stop before silent cost explosion...

2. Alchemist Prompt Routing Pattern
   (id: alchemist-prompt-routing-pattern, score: 2.339)
   ...cost-aware escalation, provider-specific adjustments...

3. MANTIS v1 From Wiki and NotebookLM
   (id: mantis-v1-from-wiki-and-notebooklm, score: 2.311)
   ...observability / cost tracking — persistent session state...

3 result(s). Use 'lore read <id>' to read full article.
```

```bash
lore read timekeeper-scheduling-pattern
lore search "retry failure handling"
lore search "RAG chunking reranking"
```

---

## Teach your AI assistant before it writes code

The part that changes how you work day-to-day:

```bash
lore install /path/to/your/project
```

This injects into your project:

```
your-project/
├── .claude/
│   └── CLAUDE.md          ← 15 pattern rules: never write retry without circuit breaker, etc.
├── .claude/hooks/
│   └── pre_tool_use.py    ← blocks anti-patterns before they're written
└── .claude/skills/
    └── lore_patterns.yaml ← scaffold shortcuts wired to slash commands
```

After `lore install`, Claude knows:
- Never write a retry loop without a circuit breaker
- Never ship without a dead-letter queue for failed tasks
- Always add cost guards before making LLM calls
- Use the cheapest model tier that matches the task complexity

The hook fires before Claude writes any code. Not after. Before.

---

## Audit your own codebase

Run the same analysis we ran on the 10 frameworks:

```bash
lore audit .
```

Lore uses Gemini 2.5 Pro to check four dimensions: circuit breaker, DLQ, cost guard, observability. Output is a JSON report with findings, severity scores, and direct scaffold commands to fix each gap.

If you've been in production more than a month, you'll find something.

---

## What this is and isn't

Lore is not a framework. It does not replace LangGraph, CrewAI, AutoGen, or anything else. It's the reliability layer that sits alongside them.

The frameworks solve the hard problem: getting an LLM to plan and execute multi-step tasks across arbitrary tool APIs. That's genuinely impressive engineering. Lore solves the adjacent hard problem: making sure that agent doesn't burn $400 at 2am when the PDF extraction API starts returning 429s.

You need both. Right now, most teams only have one.

---

```bash
pip install lore-agents
lore scaffold cost_guard
lore scaffold circuit_breaker
lore scaffold dead_letter_queue
lore audit .
```

*`lore` is open-source. Star it, fork it, build your own codex from it.*
*[github.com/Miles0sage/lore](https://github.com/Miles0sage/lore)*
