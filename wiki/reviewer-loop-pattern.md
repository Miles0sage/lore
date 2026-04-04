---
backlinks: []
concepts:
- reviewer-loop
- quality-gate
- langgraph
- human-escalation
- token-cost-optimization
- circuit-breaker
- model-routing
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: reviewer-loop-pattern
sources:
- raw/2026-04-05-reviewer-loop-pattern.md
status: published
title: Reviewer Loop Pattern
updated: '2026-04-05'
---

# Reviewer Loop Pattern

## Overview
The Reviewer Loop is a quality gate pattern in which a draft agent generates output and a separate reviewer agent evaluates it against explicit criteria before the output is accepted. This architecture introduces iterative validation to improve reliability and reduce hallucination or logical errors.

## Execution Flow
The pattern operates through a deterministic, state-driven sequence:
- Generator agent produces an initial draft.
- Reviewer agent scores the draft against predefined criteria.
- If the score meets or exceeds the acceptance threshold, the output is accepted.
- If the score falls below the threshold, the generator revises the draft using the reviewer's feedback.
- The cycle repeats up to a maximum of N iterations.
- If the threshold remains unmet after N iterations, the workflow escalates to a human operator.

## Key Design Decisions
Implementation requires configuration of four primary parameters:
- **Reviewer Model:** The reviewer may use the same architecture as the generator or a different one. Utilizing distinct models is recommended, as different architectures exhibit complementary error profiles and catch different failure modes.
- **Acceptance Threshold:** Typical scoring thresholds range from 0.7 to 0.85.
- **Maximum Iterations:** Loops should be capped at 3 to 5 iterations to prevent infinite execution cycles.
- **Escalation Path:** A deterministic fallback route must be defined for scenarios where automated revision fails after the iteration limit.

## Performance and Trade-offs
The pattern improves output fidelity by leveraging explicit evaluation criteria to identify errors the generator overlooks. The primary trade-off is computational overhead, resulting in a 2x to 3x increase in token consumption compared to single-pass generation.

## Application Scope
The Reviewer Loop is justified for high-stakes or high-visibility workloads, including:
- Code generation
- Content intended for direct publication
- Decision-making processes with downstream operational consequences

## Integration Patterns
The Reviewer Loop integrates with established orchestration and routing strategies:
- **Model Routing:** Deploy a cost-efficient model for the generator and a higher-capability model for the reviewer to balance performance and token spend.
- **Circuit Breaker:** Implement a hard termination condition after N consecutive failures to prevent resource exhaustion.
- **LangGraph:** Utilize native support for conditional edges and retry loops to manage state transitions and feedback cycles.

## Key Concepts
[[reviewer-loop]]
[[quality-gate]]
[[model-routing]]
[[circuit-breaker]]
[[langgraph]]
[[human-escalation]]
[[token-cost-optimization]]

## Sources
- 2026-04-05-reviewer-loop-pattern.md
