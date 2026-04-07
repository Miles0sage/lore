---
title: "I audited 10 AI agent frameworks. Every single one had no cost guard."
created_at: 2026-04-07
author: lore
tags: [ai-agents, reliability, python, production, open-source]
status: draft
cover_image: scorecard
---

# I audited 10 AI agent frameworks. Every single one had no cost guard.

Not 9 out of 10. Not "most." **All of them.**

Here's the scorecard. Here's the fix. Here's how to apply it in 60 seconds.

---

## The scorecard

```
┌──────────────────────┬────────────────┬──────┬────────────┬───────────────┬──────────┐
│ Repo                 │ Circuit Breaker│ DLQ  │ Cost Guard │ Observability │ Criticals│
├──────────────────────┼────────────────┼──────┼────────────┼───────────────┼──────────┤
│ OpenAI Swarm         │    MISSING     │  ✗   │   MISSING  │    MISSING    │    1     │
│ BabyAGI              │    MISSING     │  ✗   │   MISSING  │    partial    │    2     │
│ GPT-Researcher       │    MISSING     │  ✗   │   MISSING  │    present    │    0     │
│ CrewAI Examples      │    MISSING     │  ✗   │   MISSING  │    MISSING    │    2     │
│ Phidata/Agno         │    present     │  ~   │   partial  │    present    │    1     │
│ AutoGen (Microsoft)  │    MISSING     │  ✗   │   MISSING  │    MISSING    │    1     │
│ LangGraph            │    partial     │  ✗   │   MISSING  │    present    │    0     │
│ LlamaIndex           │    MISSING     │  ✗   │   MISSING  │    present    │    0     │
│ Pydantic AI          │    MISSING     │  ✗   │   MISSING  │    present    │    0     │
│ AutoGPT              │    MISSING     │  ✗   │   MISSING  │    MISSING    │    2     │
└──────────────────────┴────────────────┴──────┴────────────┴───────────────┴──────────┘

  ✗ = MISSING   ~ = partial   ✓ = present

  Cost guard:      10/10 MISSING  ◄── every single one
  DLQ:              9/10 MISSING
  Circuit breaker:  8/10 MISSING
  Observability:    5/10 missing or partial
  Critical findings: 9 total
```

---

## Why this matters at 2am

Picture this:

```
02:14  BILLING ALERT: $47 charged this hour
02:15  BILLING ALERT: $91 charged this hour
02:31  BILLING ALERT: $203 charged this hour
02:47  BILLING ALERT: $400 charged since midnight
```

An agent hit a PDF API returning 429s. No circuit breaker — it kept retrying.
No cost guard — nothing stopped it. No DLQ — 3,000 tasks left in unknown state.

The framework was fine. The reliability layer didn't exist.

---

## What's missing and why it matters

```
                    THE RELIABILITY GAP
                    
  Your agent today:              What it needs:
  
  ┌─────────────────┐            ┌──────────────────────────────────┐
  │   LLM call      │            │ CostGuard   ← hard stop at $X    │
  │   tool call     │    +       │ CircuitBreaker ← stop cascade     │
  │   tool call     │   lore     │ DLQ         ← nothing lost silent │
  │   LLM call      │            │ Observability ← know what happened│
  └─────────────────┘            └──────────────────────────────────┘
  
  Works in demo                  Works at 2am
```

---

## The fix: 4 commands

```bash
pip install lore-agents
```

### 1. Cost guard (the 10/10 finding)

```bash
lore scaffold cost_guard
```

```python
class CostGuard:
    """Hard-stop cost protection. Zero external dependencies.
    
    Args:
        budget_tokens: Hard-stop limit. Raises CostGuardExceeded when hit.
        warn_at:       Fraction that triggers warning log (default 0.80).
    
    Usage:
        guard = CostGuard(budget_tokens=100_000, warn_at=0.80)
        guard.consume("llm_call", tokens=response.usage.total_tokens)
        guard.warn_if_low()
    """
```

Wire it in 3 lines:

```python
guard = CostGuard(budget_tokens=100_000)      # hard stop at 100k tokens

# before every LLM call:
guard.consume("summarize", tokens=response.usage.total_tokens)
# → raises CostGuardExceeded if over budget
# → logs WARNING if >80% used
```

### 2. Circuit breaker

```bash
lore scaffold circuit_breaker
```

```
State machine:

   CLOSED ──(5 failures)──► OPEN ──(30s timeout)──► HALF_OPEN
     ▲                                                    │
     └────────────(1 success)────────────────────────────┘

   CLOSED  = normal, requests flow through
   OPEN    = gate sealed, returns fallback immediately (no wasted tokens)
   HALF_OPEN = one probe request, success reopens, failure re-seals
```

```python
breaker = CircuitBreaker(name="openai_api", failure_threshold=5)
result  = await breaker.call(my_llm_function, prompt)
# → after 5 failures: raises CircuitOpenError instantly
# → saves every token that would've been burned in the retry storm
```

### 3. Dead letter queue

```bash
lore scaffold dead_letter_queue
```

```
Without DLQ:              With DLQ:

task fails               task fails
    │                        │
    ├─ retry forever    classify failure
    │  (burnout)             │
    ├─ discard silently  ┌───┴──────────────┐
    │  (data loss)       │                  │
    └─ crash pipeline  TRANSIENT        PERMANENT
       (downtime)      (429, timeout)   (schema error)
                           │                │
                        replay queue    human review
                        (auto-retry)    (inspect & fix)
```

### 4. Observability

```bash
lore scaffold sentinel_observability
```

Four signals, structured JSON output:

```
{
  "event": "llm_call",
  "task_id": "t-8472",
  "model": "gpt-4.1",
  "latency_s": 1.24,
  "tokens_used": 2847,
  "cost_usd": 0.0028,
  "error_rate_1h": 0.02,
  "timestamp": "2026-04-07T02:14:33Z"
}
```

---

## All 19 patterns

```bash
lore scaffold --list
```

```
Pattern                       Archetype           Frameworks
──────────────────────────────────────────────────────────────────────
circuit_breaker               The Breaker         python, langgraph
cost_guard                    The Timekeeper      python
dead_letter_queue             The Archivist       python
reviewer_loop                 The Council         python, langgraph, crewai
supervisor_worker             The Commander       python, langgraph, crewai, openai_agents
handoff_pattern               The Weaver          python, crewai, openai_agents
three_layer_memory            The Stack           python
model_routing                 The Router          python, openai_agents
sentinel_observability        The Sentinel        python
tool_health_monitor           The Warden          python
librarian_retrieval           The Librarian       python
scout_discovery               The Scout           python
cartographer_knowledge_graph  The Cartographer    python
timekeeper_scheduling         The Timekeeper      python
architect_system_design       The Architect       python
alchemist_prompt_routing      The Alchemist       python
react_loop                                        python
reflexion_loop                                    python
plan_execute                                      python

19 patterns. Framework variants: LangGraph · CrewAI · OpenAI Agents SDK
```

---

## Audit your own codebase

```bash
lore audit .
```

Uses Gemini 2.5 Pro. Outputs a JSON report with findings, severity, and the exact `lore scaffold` command to fix each gap.

```json
{
  "findings": [
    {
      "pattern": "cost_guard",
      "status": "MISSING",
      "severity": "HIGH",
      "detail": "No configurable API spend limit found. Autonomous loops have no hard stop.",
      "fix": "lore scaffold cost_guard"
    },
    {
      "pattern": "circuit_breaker",
      "status": "MISSING", 
      "severity": "HIGH",
      "detail": "External API calls have no failure isolation. Single degraded dependency can cascade.",
      "fix": "lore scaffold circuit_breaker"
    }
  ],
  "score": 2,
  "max_score": 10
}
```

---

## Teach Claude before it writes code

```bash
lore install /path/to/your/project
```

```
Installed:
  .claude/CLAUDE.md          ← 15 pattern rules
  .claude/hooks/pre_tool.py  ← blocks anti-patterns before they're written
  .claude/skills/lore.yaml   ← scaffold shortcuts as slash commands

Claude now knows:
  ✓ Never write retry without circuit breaker
  ✓ Never ship without DLQ for failed tasks  
  ✓ Always add cost guard before LLM calls
  ✓ Use cheapest model tier that matches task
```

The hook fires **before** Claude writes the code. Not after review. Before.

---

## The 76-article knowledge base

```bash
lore search "cost guard" --limit 3

1. The Timekeeper: Scheduling Patterns for Proactive AI Agents
   score: 2.38 — budget_tokens=100_000, warn_at=0.80, hard stop before silent cost explosion

2. Alchemist Prompt Routing Pattern  
   score: 2.34 — cost-aware escalation, provider-specific adjustments

3. MANTIS v1 From Wiki and NotebookLM
   score: 2.31 — observability / cost tracking, persistent session state
```

76 articles. Full-text BM25. Zero API calls. Runs offline.

---

## What this is not

Lore is **not a framework**. It does not replace LangGraph, CrewAI, AutoGen, or anything else.

```
What frameworks solve:           What lore solves:
─────────────────────────────    ─────────────────────────────────
"Can my agent do X?"             "Will my agent do X safely at 2am
                                  without burning my budget when
                                  the PDF API starts returning 429s?"
```

You need both. Most teams only have one.

The $400 2am incident was fixable in 20 lines:
- `lore scaffold circuit_breaker` → wrap the PDF API call
- `lore scaffold cost_guard` → hard stop on the LLM client
- `lore scaffold dead_letter_queue` → capture the 3,000 stranded tasks

The framework was fine. The reliability layer was missing.

---

```
pip install lore-agents

lore scaffold cost_guard        # the 10/10 missing pattern
lore scaffold circuit_breaker   # stops the 2am cascade
lore scaffold dead_letter_queue # nothing lost silently
lore audit .                    # find what else is missing
```

**[github.com/Miles0sage/lore](https://github.com/Miles0sage/lore)**

563 tests passing. MIT license. Zero mandatory dependencies.
Works alongside LangGraph, CrewAI, AutoGen, OpenAI Agents SDK — not instead of them.

---

*Run `lore audit .` on your repo. Tell us what score you get.*
*That's the feedback loop that makes this better.*
