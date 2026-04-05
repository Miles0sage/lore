---
backlinks: []
concepts:
- scheduling
- cron
- background-jobs
- discovery-loops
- keepalive-jobs
- scout-discovery-pattern
- morning-briefs
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: timekeeper-scheduling-pattern
sources:
- raw/2026-04-05-timekeeper-scheduling-proposal.md
status: published
title: Timekeeper Scheduling Pattern
updated: '2026-04-05'
---

# Timekeeper Scheduling Pattern

## Overview
The Timekeeper is the scheduling pattern that makes an agent system proactive instead of purely reactive. It governs when work should happen without a human trigger: nightly research, keepalive jobs, morning briefs, maintenance loops, and queue cleanup. If the Scout discovers knowledge gaps, The Timekeeper is what ensures that discovery loop actually runs.

## Why It Matters
Without scheduling, an agent system only acts when prompted. That means:
- research never becomes a routine
- maintenance is always postponed
- stale canon stays stale
- operators carry the burden of remembering every recurring task

The Timekeeper is what turns one-off automation into a living workflow.

## Core Jobs
- trigger nightly discovery or ingestion loops
- generate morning briefings before operators arrive
- run keepalive jobs for fragile integrations
- schedule weekly canon maintenance
- enforce periodic sync to the private synthesis layer

## Good Scheduling Design
A strong scheduling layer should be:
- explicit about cadence
- observable when jobs fail
- safe to rerun
- separate from business logic

The Timekeeper should fire the signal, not embed every task inline.

## In Lore
The Timekeeper is central to Lore's evolutionary claim. It is what should eventually ensure:
- proposal intake is not only manual
- morning briefs appear consistently
- weekly canon reports run on schedule
- NotebookLM sync happens after approved publication batches

If those actions happen only when someone remembers, the system is not truly alive.

## Failure Modes
The scheduling pattern fails when:
- cron jobs die silently
- recurring tasks are coupled too tightly to interactive tooling
- there is no recovery or alerting path for missed runs
- the system schedules too much low-value work and creates noise

The Timekeeper should increase reliability, not create invisible background chaos.

## Key Concepts
[[scheduling]]
[[cron]]
[[background-jobs]]
[[discovery-loops]]
[[keepalive-jobs]]
[[scout-discovery-pattern]]
[[morning-briefs]]

## Sources
- `2026-04-05-timekeeper-scheduling-proposal.md`
