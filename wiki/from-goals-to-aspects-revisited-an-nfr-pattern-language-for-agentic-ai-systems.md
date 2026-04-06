---
backlinks: []
concepts:
- tool-scope sandboxing
- token budget management
- agentic ai
- crosscutting concerns
- v-graph model
- aspect-rs
- aspect-oriented programming
- non-functional requirements
- pattern language
- i* framework
- action audit trails
- prompt injection detection
- goal-oriented requirements engineering
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: from-goals-to-aspects-revisited-an-nfr-pattern-language-for-agentic-ai-systems
sources:
- raw/2026-04-05-circuit-breaker-pattern-arxiv.md
status: published
title: 'From Goals to Aspects, Revisited: An NFR Pattern Language for Agentic AI Systems'
updated: '2026-04-05'
---

# From Goals to Aspects, Revisited: An NFR Pattern Language for Agentic AI Systems

## Overview
Agentic AI systems—autonomous software agents powered by large language models (LLMs) that plan, reason, and execute tool-calling workflows—exhibit high failure rates in production due to inadequately modularized non-functional requirements (NFRs). Crosscutting concerns including security enforcement, observability, cost management, and fault tolerance are typically implemented in an ad-hoc, scattered manner across agent frameworks. This work revisits and extends the goals-to-aspects methodology originally proposed at RE 2004, adapting it to the agentic AI domain to systematically discover, identify, and modularize crosscutting concerns.

## Methodology & V-Graph Extension
The approach leverages the $i^*$ goal-oriented requirements engineering framework, which models systems as networks of actors with intentional properties (goals, softgoals, tasks, resources) connected by dependency relationships. It utilizes two complementary models:
- **Strategic Dependency (SD):** Models dependencies between actors.
- **Strategic Rationale (SR):** Models internal goal decomposition via AND/OR refinement, means-ends links, and contribution links ($++$, $+$, $-$, $-$) to softgoals.

The core discovery mechanism is the **V-graph model**, which captures crosscutting relationships in goal models:
- **Left vertex:** Functional goal (e.g., "Process Order")
- **Right vertex:** NFR softgoal (e.g., "Security")
- **Bottom vertex:** Implementing tasks that contribute to both vertices

The V-shape identifies where a single task serves distinct functional and non-functional concerns, marking it for extraction as an aspect. The model is extended for agentic AI to capture how agent tasks simultaneously contribute to functional goals (tool execution, LLM interaction) and non-functional softgoals (safety, cost efficiency, compliance).

## Pattern Language
The paper defines a reusable pattern language of 12 patterns organized across four NFR categories: security, reliability, observability, and cost management. Each pattern maps an $i^*$ goal model to a concrete aspect implementation. Four patterns address agent-specific crosscutting concerns absent from traditional AOP literature:
- Tool-scope sandboxing
- Prompt injection detection
- Token budget management
- Action audit trails

## Implementation & Framework
The patterns are implemented using Aspect-Oriented Programming (AOP) in Rust. The implementation leverages the ASPECT-RS framework, which provides an `Aspect` trait with lifecycle hooks including `before`, `after`, `after_error`, and `around`. This enables systematic interception and modularization of crosscutting behaviors at designated join points, replacing scattered authorization checks, inconsistent logging, duplicated rate limiting, and absent cost controls.

## Case Study & Validation
The methodology is validated through a case study analyzing an open-source autonomous agent framework comprising 192 files and 129,040 lines of code (LOC). The analysis quantifies concern scattering across eleven crosscutting concerns (seven established, four newly identified). V-graph analysis successfully identifies both scattered implementations and missing NFR coverage, demonstrating that goal-driven aspect discovery systematically modularizes crosscutting concerns in agentic systems.

## Key Concepts
[[Agentic AI]]
[[Non-Functional Requirements]]
[[Aspect-Oriented Programming]]
[[i* Framework]]
[[V-Graph Model]]
[[Crosscutting Concerns]]
[[Pattern Language]]
[[Goal-Oriented Requirements Engineering]]
[[Prompt Injection Detection]]
[[Token Budget Management]]
[[Tool-Scope Sandboxing]]
[[Action Audit Trails]]
[[ASPECT-RS]]

## Sources
- 2026-04-05-circuit-breaker-pattern-arxiv.md: "From Goals to Aspects, Revisited: An NFR Pattern Language for Agentic AI Systems" by Yijun Yu (The Open University, Milton Keynes, UK)
