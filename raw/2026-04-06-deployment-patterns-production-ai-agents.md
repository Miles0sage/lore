---
compiled: true
compiled_to: null
confidence: 0.85
created_at: 2026-04-06 00:00:00+00:00
evidence_score: 0.6
novelty_score: 0.8
overlap_score: 0.2
owner: lore-oracle
priority_score: 0.76
proposal_type: article
publish_recommendation: review_now
review_notes: batch auto-published
reviewer: lore-batch-review
source: manual
status: published
strategic_score: 0.9
title: Deployment Patterns for Production AI Agents
updated_at: 2026-04-05 23:29:56+00:00
---

# Deployment Patterns for Production AI Agents

## The Three Deployment Models

### 1. Sidecar Agent
The agent runs as a sidecar process alongside the main application. Shares the application's network namespace but not its filesystem or credentials. Best for agents that augment an existing service without owning a user-facing surface.

### 2. Stateless Worker
The agent is a pure function: receive task, produce output, exit. No persistent state between invocations. State lives in an external store (Redis, Supabase, S3). The supervisor launches workers on demand and garbage-collects them. This is the safest deployment model — no ambient state to corrupt.

### 3. Long-Running Daemon
The agent maintains a persistent event loop and processes tasks from a queue. Requires explicit state management, heartbeat monitoring, and graceful shutdown. Use the KAIROS loop pattern (check → act → rest) to avoid busy-waiting and runaway costs.

## Configuration Discipline

Agents should receive their configuration through a narrow, explicit interface:
- Environment variables for secrets (never baked into images)
- A single config object passed at startup (not discovered from the filesystem)
- Feature flags separate from secrets (change behaviour without credential rotation)

## Health and Observability

Every production agent needs:
- `/health` endpoint or heartbeat signal
- Structured log output (JSON, not prose)
- Token and cost counters exposed as metrics
- Dead-letter queue depth as a key alert signal

## Deployment Anti-Patterns

- **Fat credential bundles** — giving the agent all keys "just in case"
- **Mutable shared filesystem** — two agents writing to the same directory
- **Unbounded retry loops** — no circuit breaker, no max_retries
- **Silent cost escalation** — failures that automatically route to more expensive models

## Related Patterns

- The Breaker (circuit breaker)
- The Archivist (dead letter queue)
- The Timekeeper (KAIROS loop, scheduled jobs)
- The Warden (credential management)
