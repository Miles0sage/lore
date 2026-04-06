---
backlinks: []
concepts:
- large-language-models
- condorcet-jury-theorem
- confabulation-consensus
- reasoning-tree
- agent-auditor
- llm-as-judge
- majority-voting
- multi-agent-systems
- anti-consensus-preference-optimization
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: auditing-multi-agent-llm-reasoning-trees-outperforms-majority-vote-and-llm-as-ju
sources:
- raw/2026-04-05-chain-of-thought-auditing-arxiv.md
status: published
title: Auditing Multi-Agent LLM Reasoning Trees Outperforms Majority Vote and LLM-as-Judge
updated: '2026-04-05'
---

# Auditing Multi-Agent LLM Reasoning Trees Outperforms Majority Vote and LLM-as-Judge

## Overview
Multi-agent systems (MAS) built on large language models (LLMs) extend reasoning capacity through debate, dynamic computation graphs, and structured communication topologies. Despite sophisticated generation and interaction mechanisms, most frameworks aggregate final outputs using majority voting. This heuristic discards the evidential structure of reasoning traces and fails under conditions of correlated agent bias. This paper introduces `AgentAuditor`, a structure-adaptive auditing framework that replaces statistical voting with evidence-based path search over a reasoning tree.

## Problem Statement
- **Majority Voting Limitations:** Majority voting relies on the Condorcet Jury Theorem assumption that agent errors are independent. LLM agents share similar pre-training manifolds, alignment biases, and prompt anchoring, causing this assumption to collapse.
- **Confabulation Consensus:** Agents frequently reinforce each other's hallucinated rationales, converging on incorrect answers with high confidence. Repeated incorrect intermediate claims make frequency a poor proxy for validity.
- **LLM-as-Judge Deficiencies:** Naive judging is computationally inefficient and scales poorly with trace length. Long prefixes and late-stage hallucinations dilute attention, while judge models exhibit sycophancy and conformity bias, often defaulting to majority views even when minority branches contain stronger evidence.

## AgentAuditor Framework
`AgentAuditor` transitions from statistical aggregation to substantive evaluation by constructing and traversing a `Reasoning Tree`.
- **Tree Construction:** Explicitly represents agreements and divergences across multiple agent reasoning traces.
- **Localized Verification:** Resolves conflicts by comparing reasoning branches at critical divergence points, converting global adjudication into efficient, localized verification.
- **Evidence-Based Adjudication:** Selects the most justified path based on structural evidence rather than answer frequency, remaining agnostic to popularity signals and specific MAS configurations.

## Anti-Consensus Preference Optimization (ACPO)
To train the adjudicator, the authors propose Anti-Consensus Preference Optimization (ACPO):
- Trains the adjudicator specifically on majority-failure cases where popular consensus is incorrect.
- Implements a reward function that prioritizes evidence-based minority selections over frequent but flawed rationales.
- Decouples selection probability from answer frequency to mitigate conformity bias.

## Evaluation Results
- Evaluated across 5 popular multi-agent system settings.
- Yields up to 5% absolute accuracy improvement over majority voting baselines.
- Yields up to 3% absolute accuracy improvement over LLM-as-Judge baselines.
- Demonstrates reliable selection of correct minority answers when majority traces share hallucinated intermediate claims.

## Key Concepts
[[multi-agent-systems]]
[[large-language-models]]
[[majority-voting]]
[[confabulation-consensus]]
[[reasoning-tree]]
[[agent-auditor]]
[[anti-consensus-preference-optimization]]
[[llm-as-judge]]
[[condorcet-jury-theorem]]

## Sources
- arXiv:2602.09341v1 [cs.AI] (10 Feb 2026). "Auditing Multi-Agent LLM Reasoning Trees Outperforms Majority Vote and LLM-as-Judge" by Wei Yang, Shixuan Li, Heng Ping, Peiyu Zhang, Paul Bogdan, Jesse Thomason. License: CC BY 4.0. URL: https://arxiv.org/abs/2602.09341
