---
backlinks: []
concepts:
- retrieval-augmented-generation
- three-layer-memory-stack
- bm25
- reranking
- graph-memory
- fine-tuning
- semantic-search
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: librarian-retrieval-pattern
sources:
- raw/2026-04-05-librarian-retrieval-proposal.md
status: published
title: Librarian Retrieval Pattern
updated: '2026-04-05'
---

# Librarian Retrieval Pattern

## Overview
The Librarian governs retrieval for long-running agent systems. Its job is not merely to fetch documents, but to decide what memory should be retrieved, when retrieval is worth the cost, and when another strategy is better. The Librarian is the operational form of retrieval-augmented generation for agents that need continuity across sessions.

## Placement In The Memory Stack
The Librarian primarily governs Layer 2 of [[three-layer-memory-stack]]: external retrieval. This includes BM25 indexes, vector search, graph memory, rerankers, and external knowledge bases. It acts between transient context and long-lived procedural memory, deciding what evidence belongs in the current reasoning window.

## Retrieval Strategy
The Librarian should make retrieval decisions based on corpus size and task type:
- **Small high-signal corpus**: plain BM25 or direct article reads may be enough.
- **Medium corpus with overlapping topics**: semantic retrieval plus reranking becomes valuable.
- **Relationship-heavy tasks**: graph memory outperforms simple similarity search.
- **Very large repeated domain**: fine-tuning or LoRA adaptation may be cheaper than constant long-context retrieval.

The point is not "always use RAG." The point is to use the cheapest retrieval strategy that preserves answer quality.

## When BM25 Is Enough
BM25 is often the right default when:
- the wiki is compact
- article titles are meaningful
- operators care about exact phrase matches
- the corpus changes frequently and embedding maintenance is a burden

This is especially true in tools like Lore, where the canon is deliberately kept small and curated.

## When Reranking Helps
Rerankers are valuable when:
- many articles partially match a concept
- the initial candidate set is noisy
- the same query can mean different things depending on workflow context

Reranking is what turns "similar enough" results into "actually useful now" retrieval.

## When Graph Memory Wins
Graph memory becomes important when the problem is relational rather than lexical:
- which patterns depend on one another
- which frameworks share the same trade-off
- which articles reference concepts that still lack canon coverage

This is why The Librarian often works with The Cartographer rather than replacing it.

## When Fine-Tuning Beats Retrieval
Retrieval is not always the best answer. Fine-tuning or adapters become attractive when:
- the same knowledge must be recalled constantly
- the corpus has stabilized
- context injection cost exceeds the value of live retrieval
- operators need consistent style or decision boundaries, not just recall

The Librarian should know when retrieval has become too expensive or too noisy.

## Failure Modes
The retrieval layer fails when:
- similarity search returns near-duplicates with no curation
- stale documents remain indexed long after canon changed
- operators treat retrieval as a substitute for editorial quality
- everything becomes "RAG" even when a direct read or structured graph query would work better

Good retrieval begins with a good canon.

## Key Concepts
[[retrieval-augmented-generation]]
[[three-layer-memory-stack]]
[[bm25]]
[[reranking]]
[[graph-memory]]
[[semantic-search]]
[[fine-tuning]]

## Sources
- `2026-04-05-librarian-retrieval-proposal.md`
- `2026-04-05-three-layer-memory-stack-for-ai-agents.md`
