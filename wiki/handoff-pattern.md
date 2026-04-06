---
backlinks: []
concepts:
- peer-to-peer-architecture
- referential-drift
- openai-agents-sdk
- linear-pipeline
- data-gap
- agentask
- context-transfer
- langgraph
- error-propagation
- capability-gap
- supervisor-worker-pattern
- signal-corruption
- handoff-pattern
- multi-agent-coordination
confidence: high
created: '2026-04-05'
domain: ai-agents
id: handoff-pattern
sources:
- raw/2026-04-05-handoff-pattern-in-multi-agent-systems.md
- raw/2026-04-05-agent-handoffs-arxiv.md
status: published
title: Handoff Pattern
updated: '2026-04-06'
---

# Handoff Pattern

## Overview

The Handoff Pattern transfers execution control and context from one agent to the next. Unlike the [[Supervisor-Worker Pattern]], there is no central controller — each agent decides when it has finished its scope and explicitly passes the baton to a designated successor.

Think of it as a relay race: each runner (agent) carries the baton (context) for their leg and hands it cleanly to the next.

## Core Components

A robust handoff requires four elements:

| Component | Description |
|-----------|-------------|
| **Handoff trigger** | The condition that ends the current agent's scope. Can be completion-based ("I've written the code") or exception-based ("I can't handle this — escalate"). |
| **Context package** | A structured object containing task state, artifacts produced, decisions made, and instructions for the receiver. |
| **Target selection** | Logic that maps trigger conditions to the correct next agent. Usually a routing table or capability registry. |
| **Acknowledgment** | The receiving agent confirms it has received and can act on the context before the sender agent terminates. |

## Context Package Schema

The context package is where most handoff failures originate. Be explicit:

```python
@dataclass
class HandoffContext:
    task_id:        str          # Unique identifier for the overall task
    task_goal:      str          # The original goal — never mutate this
    artifacts:      dict         # Outputs produced so far (code, summaries, etc.)
    decisions:      list[str]    # Key choices made and why
    constraints:    list[str]    # Hard constraints the receiver must respect
    next_action:    str          # Specific instruction for the receiving agent
    handoff_reason: str          # Why this handoff is happening
    sender_id:      str
    timestamp:      float
```

## Sequence

```
  Agent A                    Agent B
     │                          │
     │── completes scope ───────│
     │── builds context pkg ────│
     │── selects target (B) ────│
     │── sends context ─────────►│
     │                          │── acknowledges ────────►│
     │◄── ACK received ─────────│                         │
     │── terminates ────────────│                         │
                                │── begins execution ─────┘
```

## Framework Implementations

**OpenAI Agents SDK** provides first-class handoff primitives. An agent returns a `Handoff` object with the target agent name and a populated context. The SDK handles routing and ACK automatically.

**LangGraph** models handoffs as directed graph edges. A node that completes returns the name of the next node; LangGraph routes state through the graph edge. Built-in state transfer handles context packaging.

```python
# LangGraph example
def agent_a(state: GraphState) -> GraphState:
    # ... do work ...
    return {**state, "next": "agent_b", "artifact": result}

graph.add_conditional_edges(
    "agent_a",
    lambda s: s["next"],
    {"agent_b": "agent_b", "agent_c": "agent_c"},
)
```

## Production Advice

**Validate the context package before handing off.** The receiving agent will fail in unpredictable ways if `task_goal` is missing or `artifacts` is malformed. Add a schema validation step before every handoff — it takes 5ms and prevents hours of debugging.

**Never mutate `task_goal`.** The original goal must survive every handoff intact. Each agent may add context and artifacts, but the goal is immutable. Referential drift — where the task goal drifts between agents — is one of the most common failure modes in handoff chains.

**Log the full context package at every handoff boundary.** This is your audit trail. When the final agent produces a wrong result, you need to replay the exact context that each agent received.

**Implement capability checks before accepting a handoff.** The receiving agent should verify it has the tools, permissions, and context it needs before confirming the ACK. Failing fast at the handoff boundary is far cheaper than failing 200 LLM tokens into the task.

**Cap chain length.** A handoff chain with no maximum length can cycle. Set a hard limit (e.g., 10 hops) and route to a human review queue if exceeded.

## Common Failure Modes

Research on inter-agent handoffs identifies four dominant error classes (per `2026-04-05-agent-handoffs-arxiv.md`):

| Failure | Description | Mitigation |
|---------|-------------|-----------|
| **Data Gap** | Receiver is missing information it needs | Explicit schema for context package; validation before handoff |
| **Signal Corruption** | Instructions distorted during transfer | Use structured objects, not freeform strings, for context |
| **Referential Drift** | Task goal shifts across handoffs | Pass original goal as immutable field in every context package |
| **Capability Gap** | Receiver lacks required tools or permissions | Capability registry checked at routing time |

**AgentAsk** — lightweight clarification modules that sit at the handoff edge — can reduce cascading errors by up to 4.69% while adding less than 10% overhead. Worth adding for high-stakes pipelines.

## Common Mistakes

- **Using freeform strings as the context package.** Unstructured text loses information on every hop. Use a typed dataclass or JSON schema.
- **No acknowledgment protocol.** If the sender terminates before the receiver confirms, a network hiccup drops the task with no recovery path.
- **Handoffs inside a loop without a termination condition.** Two agents that each hand off to the other will run forever. Always define an exit condition.
- **Conflating handoff with function call.** A handoff transfers *ownership* of the task. A function call returns to the caller. If you expect a return value, you want a supervisor dispatching to a worker, not a handoff.

## When to Use

Use when:
- Work is naturally sequential with clear stage boundaries
- Different stages require genuinely different capabilities or permissions
- Overhead of a central supervisor is unacceptable for latency
- Pipeline stages are long-running (each agent may take minutes)

Do NOT use when:
- You need centralized observability and routing control — use [[Supervisor-Worker Pattern]] instead
- Stages need to run in parallel and merge — supervisor fan-out handles this better
- You need to retry individual stages — a supervisor with a [[Dead Letter Queue]] is easier to manage

## Comparison with Supervisor-Worker

| Dimension | Handoff | Supervisor-Worker |
|-----------|---------|-------------------|
| Control plane | Distributed (each agent routes itself) | Centralized (one supervisor) |
| Observability | Harder — state spreads across agents | Easier — one place to observe routing |
| Latency | Lower — no supervisor round-trip | Higher — every step goes through supervisor |
| Failure recovery | Each agent must handle errors | Supervisor centralizes retry and DLQ logic |
| Best for | Linear pipelines, known stage sequence | Dynamic routing, parallel fan-out, complex retry |

## Key Concepts
[[handoff-pattern]] [[multi-agent-coordination]] [[peer-to-peer-architecture]] [[context-transfer]] [[supervisor-worker-pattern]] [[openai-agents-sdk]] [[langgraph]] [[linear-pipeline]] [[error-propagation]] [[data-gap]] [[signal-corruption]] [[referential-drift]] [[capability-gap]] [[agentask]]

## Sources
- `2026-04-05-handoff-pattern-in-multi-agent-systems.md`
- `2026-04-05-agent-handoffs-arxiv.md`
