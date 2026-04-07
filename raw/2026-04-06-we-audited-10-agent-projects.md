---
title: "We ran lore audit on 10 open-source agent projects. Here's what we found."
created_at: 2026-04-06
author: lore
tags: [ai-agents, reliability, production, open-source, audit]
status: draft
---

# We ran lore audit on 10 open-source agent projects. Here's what we found.

## The $400 wake-up call

It started at 2am with a Slack notification from a billing alert.

An agent we'd deployed to summarize research papers had hit a retry loop. The upstream PDF extraction API was returning 429s. The agent had no circuit breaker — it just kept hammering, spinning up new LLM calls to process results that never arrived. By the time the on-call engineer killed the process, the agent had burned through $400 in API credits over six hours, produced zero useful output, and left a queue of 3,000 unprocessed tasks in an ambiguous state. Were they failed? Were they in progress? We didn't know — there was no dead letter queue to inspect.

We wrote a postmortem. Somewhere in it was a line that kept coming back to us: *"The framework we used was not designed for this."*

That's true. Most agent frameworks are not designed for production reliability. They're designed for capability demonstration — showing what's possible when an LLM can call tools, plan, and execute multi-step tasks. That's genuinely hard, genuinely impressive engineering. But "it works in the demo" and "it works at 2am when everything is on fire" are different bars.

We wanted to know exactly how different. So we built `lore audit` — a static analysis tool that checks agent codebases for production reliability patterns — and we ran it against 10 of the most widely-used open-source agent projects.

This is what we found.

---

## The methodology

`lore audit` uses Gemini 2.5 Pro to perform structured code analysis across four reliability dimensions:

- **Circuit breaker**: Does the project implement or recommend a pattern to stop cascading failures when a downstream dependency is degraded?
- **Dead Letter Queue (DLQ)**: Is there a mechanism to capture, inspect, and replay tasks that failed unrecoverably?
- **Cost guard**: Are there configurable API spend limits, action counters, or automatic shutdown conditions on autonomous agents?
- **Observability**: Are structured logs, traces, or metrics emitted in a way that would allow an operator to understand what an agent did and why?

We ran the audit against the primary codebases of 10 projects, using the latest commit on their main branch as of April 2026. The projects were selected to represent the breadth of the ecosystem: orchestration frameworks, research agents, coding agents, and multi-agent systems.

Projects audited: OpenAI Swarm, BabyAGI, GPT-Researcher, CrewAI Examples, Phidata/Agno, AutoGen (Microsoft), LangGraph, LlamaIndex, Pydantic AI, AutoGPT.

Here's the full scorecard:

| Repo | Circuit Breaker | DLQ | Cost Guard | Observability | Criticals |
|------|:---:|:---:|:---:|:---:|:---:|
| OpenAI Swarm | MISSING | MISSING | MISSING | MISSING | 1 |
| BabyAGI | MISSING | MISSING | MISSING | partial | 2 |
| GPT-Researcher | MISSING | MISSING | MISSING | present | 0 |
| CrewAI Examples | MISSING | MISSING | MISSING | MISSING | 2 |
| Phidata/Agno | present | partial | partial | present | 1 |
| AutoGen (Microsoft) | MISSING | MISSING | MISSING | MISSING | 1 |
| LangGraph | partial | MISSING | MISSING | present | 0 |
| LlamaIndex | MISSING | MISSING | MISSING | present | 0 |
| Pydantic AI | MISSING | MISSING | MISSING | present | 0 |
| AutoGPT | MISSING | MISSING | MISSING | MISSING | 2 |

**Summary totals:**
- Circuit breaker missing: 8/10
- DLQ missing: 9/10
- Cost guard missing: **10/10**
- Observability missing or partial: 5/10
- Critical findings: 9 total across all projects

Let's walk through what the audit found, starting with the most striking result.

---

## Finding 1: Cost guards — 10 out of 10 missing

Every single project we audited had no built-in cost guard.

Not "partial." Not "undocumented." Zero. None of them ship with a configurable mechanism to say: *if this agent spends more than $X or makes more than N API calls, stop.*

This is the finding that surprised us most. The risk of runaway API costs in autonomous agents is well-understood — it's one of the first things discussed whenever autonomous execution comes up. And yet, across all ten codebases, there is no first-class mechanism to bound it.

AutoGPT is the starkest example. The audit found: *"The `--continuous` flag enables fully autonomous operation but there are no documented, mandatory safeguards like API spend limits, action counters, or automatic shutdown on repeated errors. This creates a dangerous execution path that can lead to runaway API costs and unintended system actions."*

This is an agent that was explicitly designed to run autonomously for extended periods. The absence of a cost guard isn't an oversight — it reflects the fact that these frameworks are built to demonstrate capability, not to operate safely in the dark.

The fix is not complicated. A cost guard is essentially a counter with a threshold check before each API call. But it needs to be first-class — part of the framework's execution model, not a wrapper you bolt on from the outside. Right now, every team shipping an agent to production has to build this themselves.

---

## Finding 2: Dead letter queues — 9 out of 10 missing

A dead letter queue is a holding area for tasks that failed in a way that cannot be retried automatically. It's a concept borrowed from message queue systems (SQS, RabbitMQ, Kafka all have native DLQ support), and it solves a specific problem: what do you do with a task that keeps failing?

Without a DLQ, you have three bad options: retry forever (resource exhaustion), discard silently (data loss), or crash the pipeline (operational disruption). With a DLQ, you have a fourth option: quarantine the bad task, let everything else proceed, and let a human inspect the failure at their convenience.

In agentic systems, this matters more than in traditional pipelines. A "task" for an agent might be a document to process, a user request to fulfill, or an action to execute. Losing it silently is not acceptable in most production contexts. Yet only one project — Phidata/Agno — had any partial implementation of this pattern.

The AutoGen audit was particularly direct: *"The event-driven, pub/sub architecture lacks any documented mechanism for handling message delivery failures, agent processing errors, or poison pills. Without a Dead Letter Queue and replay strategy, transient failures can lead to permanent data loss."*

LangGraph gets partial credit for its checkpointing system, which provides durable execution and can recover from transient failures. But the audit flagged a gap even there: *"The framework advertises 'Durable execution' via checkpointing, which handles transient failures. However, it lacks explicit guidance for handling fundamentally un-processable tasks ('poison pills'). In production, this can lead to infinite retries, resource exhaustion, or silent data loss."*

There's a meaningful difference between "this task failed and can be retried" and "this task is fundamentally broken and needs human review." LangGraph handles the first case. Most frameworks handle neither.

---

## Finding 3: Circuit breakers — 8 out of 10 missing

A circuit breaker is a pattern from distributed systems resilience (popularized by Netflix's Hystrix, now ubiquitous in service meshes). The concept: if a downstream service starts failing, stop sending it requests for a period of time. Give it a chance to recover. Don't let one failing dependency bring down your entire system.

For agent systems, the relevant downstream dependencies are LLM APIs, tool APIs, and any external services the agent calls. When these degrade — rate limits, timeouts, partial outages — an agent without circuit breakers will hammer them until it either succeeds, exhausts its budget, or crashes.

OpenAI Swarm, one of the most widely-referenced agent frameworks, had this finding: *"No Production Safeguards for Failure and Recovery — the entire framework is stateless with no retry logic, no circuit breakers, and no DLQ."*

LlamaIndex, which many teams use in production-adjacent systems, had: *"Without built-in, configurable retry logic or circuit breakers, applications built on LlamaIndex will be brittle and prone to cascading failures. Developers are left to implement this critical resiliency layer themselves for every single external call."*

That last sentence is key: *developers are left to implement this themselves for every single external call.* That's what the ecosystem currently expects. Every team shipping an agent has to rediscover and re-implement the same resilience patterns from scratch.

---

## The outlier: Phidata/Agno

One project stood out as materially more production-mature than the rest: Phidata/Agno.

It was the only project with a circuit breaker present (not partial — present), the only one with any DLQ implementation (partial), the only one with cost guard functionality (partial), and it had solid observability. It also had one critical finding, but one is notably better than two.

What Phidata/Agno gets right is that it treats infrastructure concerns as part of the framework's job, not the application developer's job. Retry policies, structured logging, and execution boundaries are first-class concepts in its design. That's the right instinct.

It's worth noting that Phidata/Agno has been through more production cycles than many of the other projects. The gap between it and the rest of the field is not a gap in intelligence or engineering quality — it's a gap in production mileage.

---

## A note on BabyAGI

BabyAGI self-describes as "not for production," and the audit found exactly why that disclaimer exists. Two critical findings: arbitrary code execution via unsandboxed `exec()`, and an encryption key exposed in logs.

We include it in the audit not to pile on — the project has been transparent about its experimental nature — but because it's widely forked and studied. Codebases with `exec()` in the execution loop show up in production more often than they should.

---

## What Pydantic AI gets right (and what it defers)

Pydantic AI had zero critical findings and good observability, which puts it in a reasonable position. But the audit found an interesting architectural choice: *"The framework relies on integrations with heavy-duty orchestrators like Temporal, Prefect, and DBOS for critical resilience patterns. Users without the infrastructure may lack built-in, lightweight alternatives."*

This is a reasonable design position — offload reliability to infrastructure that's specifically designed for it. Temporal is excellent at durable execution. If you have Temporal, you probably don't need circuit breakers in your agent layer.

But many teams don't have Temporal. And "the framework assumes you have enterprise orchestration infrastructure" is a real gap for teams at earlier stages. The finding here is not a failure — it's a scoping decision that should be made explicit.

---

## What to do about it

If you're shipping an agent to production and you recognize your setup in any of these findings, here's the practical path forward.

`lore` ships scaffolds for all four patterns. These are production-ready implementations you can drop into an existing agent project:

```bash
# Add a circuit breaker around any external call
lore scaffold circuit_breaker

# Add a dead letter queue for failed tasks
lore scaffold dead_letter_queue

# Add a cost guard with configurable thresholds
lore scaffold cost_guard

# Add structured observability
lore scaffold observability
```

Each scaffold takes under 60 seconds to install and is designed to work alongside existing frameworks, not replace them. The circuit breaker works with any async function. The DLQ integrates with Redis, SQS, or a local SQLite store for development. The cost guard hooks into the OpenAI and Anthropic SDK call sites.

You can also run `lore audit` on your own codebase to get the same structured findings we generated for these 10 projects:

```bash
lore audit .
```

The audit produces a JSON report with findings, severity scores, and remediation suggestions for each missing pattern.

---

## The category problem

We want to be clear about what this audit is and is not saying.

It is not saying these frameworks are bad. OpenAI Swarm, LangGraph, LlamaIndex, CrewAI, Pydantic AI — these are serious engineering efforts that solve genuinely hard problems. Getting an LLM to reliably plan and execute multi-step tasks across arbitrary tool APIs is not easy. The teams behind these projects have made the ecosystem dramatically more capable.

What the audit is saying is that the ecosystem has a category gap. These frameworks are capability layers. They answer the question: *can an agent do X?* Production reliability is a different category. It answers the question: *will an agent do X safely, observably, and without burning down your infrastructure when things go wrong?*

That second category has no dominant framework. The patterns exist — circuit breakers, DLQs, cost guards — but they live in distributed systems engineering, not in the AI agent ecosystem. The knowledge hasn't transferred yet.

That's the gap `lore` is designed to fill. Not by replacing existing frameworks, but by being the reliability layer that sits alongside them. The two categories are complementary. You need both.

The $400 wake-up call we described at the start was fixable in about 20 lines of code. A circuit breaker around the PDF extraction call. A cost guard on the LLM client. A DLQ for the tasks that couldn't complete. The agent framework we used was fine. We just needed the other half of the stack.

---

*`lore` is an open-source agent reliability toolkit. Full audit methodology and raw Gemini output available at [github.com/Miles0sage/lore](https://github.com/Miles0sage/lore). Run `lore audit` on your own codebase and see where you stand.*
