---
backlinks: []
concepts:
- knowledge-graphs
- graph-memory
- dangling-concepts
- orphan-articles
- multi-hop-reasoning
- scout-discovery-pattern
- librarian-retrieval-pattern
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: cartographer-knowledge-graph-pattern
sources:
- raw/2026-04-05-cartographer-knowledge-graph-proposal.md
status: published
title: Cartographer Knowledge Graph Pattern
updated: '2026-04-05'
---

# Cartographer Knowledge Graph Pattern

## Overview
The Cartographer treats a knowledge base as a graph instead of a pile of documents. Articles are nodes, links are edges, referenced-but-missing topics are dangling concepts, and isolated pages are orphans. This graph view makes it possible to reason about coverage, relationship quality, and knowledge gaps in a way retrieval alone cannot.

## Why It Matters
Traditional search answers "what looks similar?" The Cartographer answers:
- what is missing?
- what is disconnected?
- which concepts are central?
- which patterns have become isolated from the rest of the canon?

This is the pattern that turns Lore from a document set into a navigable system.

## Core Responsibilities
- map article-to-article links
- detect dangling concepts without canon coverage
- identify orphan articles with weak integration
- surface dense clusters and weakly connected zones
- guide discovery priorities based on graph topology

## Graph Memory Versus Similarity Search
Graph memory is most useful when the operator cares about relationships:
- which frameworks depend on a handoff model
- which reliability patterns reinforce one another
- which scheduling patterns should connect to discovery and review loops

Similarity search may find an article about memory. Graph memory can reveal how memory, routing, observability, and scheduling relate in the same system.

## In Lore
The Cartographer is what should eventually power:
- gap detection for the morning brief
- duplicate and overlap suggestions
- discovery priorities for The Scout
- internal consistency checks before publication

Even a simple wikilink graph is enough to make the system smarter than a plain markdown folder.

## Failure Modes
Graph work fails when:
- links are not curated
- missing concepts are detected but never reviewed
- the graph becomes decorative rather than operational
- every relationship is treated as equally important

The Cartographer is useful only when graph findings change what the team writes next.

## Key Concepts
[[knowledge-graphs]]
[[graph-memory]]
[[dangling-concepts]]
[[orphan-articles]]
[[multi-hop-reasoning]]
[[scout-discovery-pattern]]
[[librarian-retrieval-pattern]]

## Sources
- `2026-04-05-cartographer-knowledge-graph-proposal.md`
