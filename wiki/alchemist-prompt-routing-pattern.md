---
backlinks: []
concepts:
- cost-aware-routing
- prompt-engineering
- prompt-adaptation
- model-routing
- fallback-routing
- tool-health-monitoring-for-ai-agents
- cost-optimization
- reviewer-loop-pattern
- circuit-breaker-pattern-for-ai-agents
- model-specific-transformation
- openrouter
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: alchemist-prompt-routing-pattern
sources:
- raw/2026-04-05-alchemist-prompt-routing-proposal.md
- raw/2026-04-05-alchemist-prompt-routing-proposal.md
status: published
title: Alchemist Prompt Routing Pattern
updated: '2026-04-06'
---

# Alchemist Prompt Routing Pattern

## Overview
The Alchemist is the pattern that adapts prompts and model choices to the real-world state of the system. While [[model-routing]] decides which model tier is appropriate for a task, The Alchemist handles the practical transformation layer: prompt shaping, fallback behavior, cost-aware escalation, and provider-specific adjustments. It serves as the canonical reference for **prompt adaptation**, **model-specific transformation**, and **cost-aware routing refinements**, ensuring that abstract routing policies translate into reliable execution.

## What The Alchemist Does
The Alchemist should answer:
- how should this task be phrased for this model?
- when should a cheap model be tried first?
- when should the system escalate?
- how should prompts change when a provider becomes less reliable?
- how should routing decisions change when model quality or tool reliability drifts?

This pattern is where abstract routing policy becomes execution reality.

## Core Behaviors
- maintain task-type to model mappings
- adapt prompts for different provider strengths and weaknesses
- define fallback paths when a model degrades
- minimize cost without losing quality
- learn from repeated misroutes and failed escalations
- apply model-specific transformation rules to optimize output quality per provider

## Routing And Prompting Together
Prompt adaptation and routing should not be treated as separate concerns. The same task may succeed on a cheaper model if:
- the prompt is narrowed
- the output schema is made stricter
- retrieval context is trimmed
- the verifier threshold is changed appropriately

The Alchemist exists to make those adjustments explicit.

## Relationship To Other Patterns
- [[model-routing]] defines the dispatch policy.
- [[tool-health-monitoring-for-ai-agents]] provides the health signal that may force a reroute.
- [[circuit-breaker-pattern-for-ai-agents]] protects the system from repeated failed calls to degraded providers.
- [[reviewer-loop-pattern]] provides feedback about when a cheaper path is no longer good enough.

## Failure Modes
The Alchemist fails when:
- routing is based only on headline cost
- the system escalates too slowly during quality collapse
- prompt adaptation becomes ad hoc and undocumented
- operators cannot tell why a task was routed a certain way

The pattern works best when the adaptation logic is visible and measured.

## Key Concepts
[[prompt-engineering]]
[[model-routing]]
[[cost-optimization]]
[[fallback-routing]]
[[prompt-adaptation]]
[[model-specific-transformation]]
[[cost-aware-routing]]
[[tool-health-monitoring-for-ai-agents]]
[[openrouter]]

## Sources
- `2026-04-05-alchemist-prompt-routing-proposal.md`
