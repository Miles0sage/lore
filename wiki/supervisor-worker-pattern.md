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
confidence: medium
created: '2026-04-04'
domain: ai-agents
id: supervisor-worker-pattern
sources:
- raw/2026-04-04-ai-agent-frameworks-2026.md
status: published
title: Supervisor-Worker Pattern
updated: '2026-04-04'
---

# Supervisor-Worker Pattern

*Sources: 1 primary synthesis | Date: 2026-04-04*

---

## Definition

The supervisor-worker pattern is a multi-agent architecture where one supervising agent decomposes work, decides which worker should act next, and aggregates the results from narrower specialist workers.

It is the dominant orchestration pattern in this wiki because it is easier to debug than free-form swarms and cheaper than using a high-end model for every step.

---

## Why It Works

- Centralized control keeps routing decisions explicit
- Workers stay narrow, reusable, and replaceable
- Failure isolation is better than in peer-to-peer swarms
- Cost drops because the supervisor can be expensive while workers stay cheap

In practice, the supervisor becomes the control plane, while workers are execution units.

---

## Typical Workflow

1. The supervisor receives the task and evaluates scope.
2. It chooses a worker or set of workers.
3. Workers execute bounded subtasks.
4. The supervisor validates, merges, retries, or escalates.
5. The system exits or loops through a [[Reviewer Loop]].

This pattern often combines with [[Model Routing]] so that the supervisor uses a stronger reasoning model and workers use faster or cheaper specialists.

---

## Best-Fit Use Cases

- research pipelines
- code generation plus review
- customer support escalation trees with specialist agents
- compliance workflows that need explicit control and auditability
- retrieval-plus-synthesis pipelines with parallel workers

The pattern is especially strong when tasks can be clearly split into roles but still require centralized decisions.

---

## Framework Fit

[[LangGraph]] is the canonical implementation in this wiki because it supports explicit routing, parallel fan-out, checkpoints, and human interrupts. Other frameworks can mimic the pattern, but LangGraph is the one most directly associated with it in the source material.

The main alternative is the [[Handoff Pattern]], where agents explicitly transfer control to each other. Handoffs reduce routing overhead but give up the single control plane that makes supervisor-worker systems easier to observe.

---

## Reliability Requirements

This pattern is robust only if the supervisor is opinionated about failure:

- use [[Circuit Breaker]] logic around tools
- send persistent failures to a [[Dead Letter Queue]]
- monitor worker quality with [[Tool Health Monitoring]]
- cap retries and iterations

Without those controls, the supervisor can amplify bad routing into higher cost and more retries.

---

## Verdict

If you need multi-agent orchestration and want the most production-friendly default, start with supervisor-worker. It is not the only pattern, but it is the easiest one to reason about when systems become expensive, stateful, or high stakes.

## Key Concepts
[[LangGraph]] [[Model Routing]] [[Reviewer Loop]] [[Handoff Pattern]] [[Circuit Breaker]] [[Dead Letter Queue]] [[Tool Health Monitoring]] [[AI Agent Frameworks & Patterns 2026]]

## Sources
- raw/2026-04-04-ai-agent-frameworks-2026.md
