---
backlinks: []
concepts:
- model routing
- claude opus 4.6
- gpt-5.4
- gemini 3.1 pro
- agentic coding
- cost-optimized ai
confidence: medium
created: '2026-04-04'
domain: ai-agents
id: swe-bench
sources:
- raw/2026-04-04-model-routing-and-cost-optimization.md
status: published
title: SWE-bench
updated: '2026-04-04'
---

# SWE-bench

*Sources: 1 primary synthesis | Date: 2026-04-04*

---

## What It Measures

SWE-bench is a benchmark for software engineering performance. In this wiki it is used as a shorthand for “how well does a model solve real coding tasks,” especially compared with toy code benchmarks like HumanEval.

The important reason it appears repeatedly is that it is closer to actual developer work: multi-file changes, repository context, bug-fix behavior, and validation against real tasks rather than isolated function completion.

---

## Why It Matters In This Wiki

SWE-bench is one of the few empirical anchors used in the wiki’s [[Model Routing]] guidance. It helps separate:

- flagship models that are genuinely stronger at coding
- budget models that are “good enough” for narrower tasks
- open-weight models that are viable for local or private-code workflows

That is why routing decisions repeatedly reference it when comparing Claude, GPT, Gemini, DeepSeek, Qwen, and local models.

---

## How To Use It Correctly

Treat SWE-bench as a signal, not a full decision rule.

It is useful for:

- comparing coding-oriented models
- deciding when a cheap model is close enough to a flagship
- spotting when open-weight models are operationally viable

It is not enough on its own for:

- tool-use reliability
- long-horizon autonomy
- format compliance
- multimodal tasks
- org-specific codebase fit

A model can score well on SWE-bench and still be the wrong choice for your workflow if latency, cost, or tool calling matter more.

---

## Practical Interpretation

In the local routing research, SWE-bench supports several practical conclusions:

- top coding models deserve escalation for complex code work
- cheaper coding models can absorb a large share of routine generation
- open-weight models are now close enough to matter operationally

That makes SWE-bench most valuable when paired with cost and role definitions, not when treated as a leaderboard to blindly follow.

---

## Rule Of Thumb

Use SWE-bench to decide how much coding quality you are giving up when you route down to a cheaper model. Then validate that tradeoff against your own repo, tool chain, and review loop.

## Key Concepts
[[Model Routing]] [[Claude Opus 4.6]] [[GPT-5.4]] [[Gemini 3.1 Pro]] [[agentic coding]] [[cost-optimized AI]] [[AI Model Selection & Routing Guide 2026]]

## Sources
- raw/2026-04-04-model-routing-and-cost-optimization.md
