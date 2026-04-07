# Lore Platform Overview

**Lore** is a living pattern library and AgentOps harness for intelligent systems. It is the only tool that combines executable governance scaffolds, archetype-driven narratives, a self-evolving knowledge base, and a full install/audit layer into a single operator toolkit.

## What Lore Is

Lore is three things simultaneously:

1. **AgentOps Audit Layer** — `lore audit` uses Gemini's 2M context window to scan an entire enterprise codebase and return a structured JSON report: which agents are missing circuit breakers, which tasks have no DLQ, which workflows have no cost guards. Reports are saved to `.lore/audits/` and automatically mapped to `lore scaffold` / `lore install` remediation commands. Price point: $500–$2K per audit run. 40 enterprise customers = $1M ARR.

2. **Bootstrap/Install Layer** — `lore install` drops hooks, skills, and CLAUDE.md rules into any project. `lore scaffold <pattern>` generates reference implementations for circuit_breaker, dead_letter_queue, reviewer_loop, three_layer_memory, sentinel_observability, model_routing, and tool_health_monitor. This turns pattern knowledge into executable code in seconds.

3. **Operator Feedback Layer** — `lore evolve` runs nightly evolution, compiling raw session notes, audit findings, and new patterns into the canon wiki. The codex grows smarter every night.

## What Lore Is Not

- Not a framework (not LangChain, not Google ADK)
- Not a code editor (not Cursor)
- Not a generic agent runtime
- Not a NotebookLM wrapper
- Not a broad research kitchen sink

## The 26 Canon Articles

Lore's wiki contains 26 foundational articles covering: circuit breakers, dead letter queues, three-layer memory, sentinel observability, model routing, tool health monitors, reviewer loops, handoff protocols, deployment patterns, fleet management, postmortem analysis, router learning, and more.

## The 15 Archetypes

Lore's 15 character archetypes personify system roles: The Breaker (circuit isolation), The Archivist (memory stack), The Council (reviewer loop), The Stack (three-layer memory), The Weaver (handoff), The Commander (fleet), The Warden (security), The Router (model routing), The Sentinel (observability), The Librarian (RAG), The Scout (discovery), The Cartographer (knowledge graph), The Alchemist (prompt routing), The Timekeeper (scheduling), The Architect (system design).

## MCP Server + CLI

Lore ships as:
- A Python package (`pip install lore-agents`)
- An MCP server (`lore.server`) with 30+ tools: `lore_audit`, `lore_scaffold`, `lore_install`, `lore_search`, `lore_ask`, `lore_chronicle`, `lore_evolve`, `lore_dispatch`, `lore_fleet_*`, `lore_postmortem_*`, `lore_route`, and more
- A CLI (`lore audit`, `lore scaffold`, `lore install`, `lore search`, `lore read`, `lore list`)

## Competitive Position

- **vs. LangChain**: LangChain = plumbing (connecting LLMs to tools). Lore = blueprints (proven patterns for how those connections should be structured, governed, and repaired).
- **vs. Cursor**: Cursor writes code faster. Lore ensures that code — however written — remains governed, observable, and production-safe.
- **vs. Google ADK**: Google ADK orchestrates agents. Lore provides the harness reliability layer (circuit breakers, DLQ, verification loops) that wraps around any orchestrator.
- **vs. DevTales**: DevTales generates narrative code history. Lore generates executable governance scaffolds with narrative archetypes as the teaching layer.

## The Positioning Narrative

> "Your agents are failing in production. LangChain gave you the pipes. Google ADK gave you the orchestration. Cursor wrote the code. But nobody gave you the circuit breakers, the dead letter queues, the verification loops, or the audit trails. That's Lore. We are the harness reliability layer — the governance and pattern scaffold that wraps around whatever framework you already use."

## Revenue Path

- **Lore Audit** — $500–$2K per run, enterprise codebase analysis via Gemini 2M
- **Lore Install** — free open source, drives adoption and upsell
- **Enterprise SLA** — recurring contract for audit cycles, pattern updates, support
- **40 customers × $2K/month = $1M ARR in 6–12 months (aggressive path)**

## Current Build Status (2026-04-06)

**Shipped:**
- `lore audit` — Gemini 2M bridge, CLI + MCP, report persistence, action mapping
- `lore scaffold` — 7 patterns with reference implementations
- `lore install` — hooks, skills, CLAUDE.md injection
- `lore evolve` — nightly evolution engine
- `lore dispatch` — model routing with circuit breaker
- 76 canon articles, 15 archetypes, full MCP server

**Next builds (ranked):**
1. PyPI publish — `pip install lore-agents` unblocks all adoption
2. Google ADK/A2A framework support — `lore scaffold supervisor_worker --framework a2a`
3. Harden `lore install` — `--dry-run`, `lore uninstall`, post-install verification
4. Persistent circuit breaker state (Redis backend, not process-local)
5. DLQ with error classification (transient/permanent/ambiguous) and gradual replay

## Critical Gaps (from first live audit)

1. Circuit breaker state is process-local — not production-safe across restarts
2. Failed tasks are not persisted into a replayable DLQ
3. Feedback loops are analytical, not self-applying
4. Codex customization is still hardcoded
5. Dangerous operations need stronger verification coverage

## Market

- Agentic AI infrastructure: $7.84B (2025) → $52B (2030)
- AI captured 50% of all global VC in 2025 ($200B+)
- Seed-stage AI companies command 42% valuation premium
- Lore's target: a16z, Sequoia, Lightspeed — all active in agentic infrastructure
