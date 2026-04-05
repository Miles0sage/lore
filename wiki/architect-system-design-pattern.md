---
backlinks: []
concepts:
- system-design
- adrs
- prds
- procedural-memory
- phase-planning
- supervisor-worker-pattern
- three-layer-memory-stack
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: architect-system-design-pattern
sources:
- raw/2026-04-05-architect-system-design-proposal.md
status: published
title: Architect System Design Pattern
updated: '2026-04-05'
---

# Architect System Design Pattern

## Overview
The Architect is the planning and coherence pattern for agent systems. It exists to prevent local optimizations from breaking the whole. Where workers execute and routers dispatch, The Architect defines the shape of the system: phases, operating rules, boundaries, artifacts, and decision records.

## Core Artifacts
The Architect should produce and maintain:
- PRDs that define product intent
- ADRs that capture major system decisions
- phase plans that sequence implementation
- operating rules that later agents inherit
- boundary definitions between private and public functionality

In practice, this is how planning becomes procedural memory.

## Why It Matters
Agent systems accumulate complexity quickly. Without an architectural layer:
- multiple workflows encode conflicting assumptions
- reliability patterns are added inconsistently
- operators lose track of what is canonical
- every new session re-litigates decisions that should already be settled

The Architect turns temporary reasoning into stable direction.

## Relationship To Other Patterns
- [[three-layer-memory-stack]] stores the long-lived outcomes of architectural decisions.
- [[supervisor-worker-pattern]] benefits from explicit decomposition plans and worker boundaries.
- [[timekeeper-scheduling-pattern]] enforces architectural maintenance loops once they are defined.
- [[reviewer-loop-pattern]] ensures that architectural outputs are challenged before they become policy.

## Good Architectural Practice
The Architect should:
- prefer explicit trade-offs over vague aspiration
- keep decisions close to implementation reality
- distinguish private operator tooling from public release surface
- define what "done" means for each phase

The pattern is not about producing diagrams for their own sake. It is about preserving coherence as the system evolves.

## Failure Modes
The Architect fails when:
- planning becomes detached from the actual runtime
- every idea becomes a grand roadmap item
- no artifact survives beyond the current session
- implementation teams cannot tell which decisions are still canonical

An Architect without operational feedback becomes decoration. An Architect with clear ADRs becomes leverage.

## Key Concepts
[[system-design]]
[[adrs]]
[[prds]]
[[procedural-memory]]
[[phase-planning]]
[[supervisor-worker-pattern]]
[[three-layer-memory-stack]]

## Sources
- `2026-04-05-architect-system-design-proposal.md`
