---
backlinks: []
concepts:
- proactive-research
- discovery-loops
- gap-analysis
- notebooklm
- source-evaluation
- cartographer-knowledge-graph-pattern
- reviewer-loop-pattern
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: scout-discovery-pattern
sources:
- raw/2026-04-05-scout-discovery-proposal.md
status: published
title: Scout Discovery Pattern
updated: '2026-04-05'
---

# Scout Discovery Pattern

## Overview
The Scout is the discovery engine in an evolutionary knowledge system. It does not wait passively for a human to request a topic. Instead, it looks for canon gaps, stale patterns, broken links, emerging frameworks, and unaddressed concepts, then turns those findings into reviewable proposals.

## Mission
The Scout's purpose is to answer: what should the system learn next?

That means it should continuously inspect:
- dangling concepts in the knowledge graph
- new topics mentioned in working conversations
- stale frameworks whose guidance may no longer be current
- missing canon coverage for already-defined archetypes
- source packs that need refresh or consolidation

## Discovery Loop
The Scout should operate as a loop:
1. detect a gap
2. gather candidate sources
3. compare overlap with existing canon
4. write a proposal, not final canon
5. hand that proposal to review

The critical design principle is that the Scout should propose, not publish.

## Source Handling
The Scout works best when it preserves evidence rather than flattening it. When two sources disagree, the Scout should retain that disagreement in the proposal rather than pretending the conflict is resolved. This keeps the editorial decision where it belongs: with review.

## Relationship To Other Patterns
- [[cartographer-knowledge-graph-pattern]] tells the Scout where the map is incomplete.
- [[reviewer-loop-pattern]] prevents low-quality research from becoming canon.
- [[librarian-retrieval-pattern]] gives the Scout access to the current body of knowledge before it proposes something new.
- [[timekeeper-scheduling-pattern]] is what makes the Scout proactive instead of manual.

## Good Scout Behavior
A good Scout:
- finds missing patterns before operators ask
- produces compact, reviewable proposals
- identifies overlap before generating duplicate canon
- separates raw source collection from canonical publication

A bad Scout floods the system with noisy notes and calls that "learning."

## Practical Use In Lore
In Lore, the Scout is represented by the proposal queue itself. The queue is where gaps become candidate knowledge. Once the operator has a morning brief, the Scout has already done its part: finding what deserves attention.

## Key Concepts
[[proactive-research]]
[[discovery-loops]]
[[gap-analysis]]
[[notebooklm]]
[[source-evaluation]]
[[cartographer-knowledge-graph-pattern]]
[[reviewer-loop-pattern]]

## Sources
- `2026-04-05-scout-discovery-proposal.md`
