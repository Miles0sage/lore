---
backlinks: []
concepts:
- persistent state
- langgraph
- three-layer memory stack
- vector databases
- in-context memory
- context rot
- external retrieval
confidence: high
created: '2026-04-05'
domain: ai-agents
id: three-layer-memory-stack
sources:
- raw/2026-04-05-three-layer-memory-stack-for-ai-agents.md
status: published
title: Three-Layer Memory Stack
updated: '2026-04-06'
---

# Three-Layer Memory Stack

## Overview

The Three-Layer Memory Stack is the canonical architecture for managing agent memory across sessions and tasks. It solves a fundamental constraint: LLM context windows are finite, but agents need to operate over unbounded history.

The stack stratifies memory by persistence, retrieval latency, and signal strength. Each layer has a distinct write policy and is loaded at a different point in the agent lifecycle.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Layer 1 — In-Context (Working Memory)               │
│  What: active conversation, tool calls, current task │
│  When: always present during the LLM call            │
│  TTL:  session (discarded on termination)            │
│  Cost: highest (every token counts)                  │
└──────────────────────┬───────────────────────────────┘
                       │ inject at session start
┌──────────────────────▼───────────────────────────────┐
│  Layer 2 — External Retrieval (Episodic/Semantic)    │
│  What: historical interactions, facts, domain docs   │
│  When: retrieved just before each LLM call           │
│  TTL:  indefinite (survives session boundaries)      │
│  Cost: retrieval latency + embedding/search cost     │
└──────────────────────┬───────────────────────────────┘
                       │ load at agent init
┌──────────────────────▼───────────────────────────────┐
│  Layer 3 — Persistent State (Procedural Memory)      │
│  What: skills, conventions, routing preferences      │
│  When: loaded once at startup                        │
│  TTL:  indefinite; updated only on verified success  │
│  Cost: lowest (read once, used many times)           │
└──────────────────────────────────────────────────────┘
```

## Layer Details

### Layer 1 — In-Context (Working Memory)

The active LLM context window. Contains the current conversation turn, tool call history, and immediate task state. This layer is ephemeral — it vanishes when the session ends.

**Write policy:** Append-only during the session. Never write to long-term storage from Layer 1 without explicit promotion logic.

**Context rot risk:** High. If you dump everything into context — full conversation history, all documents, every tool result — you hit the window limit and the model's effective attention degrades long before that. Keep Layer 1 focused on the *current* step.

**What belongs here:**
- The current user message and last N turns of conversation
- Tool call results from this session
- Working variables and intermediate reasoning

**What does NOT belong here:**
- Full project history
- Large reference documents (use Layer 2 retrieval instead)
- Static conventions and preferences (use Layer 3)

### Layer 2 — External Retrieval (Episodic/Semantic Memory)

Historical interactions and domain knowledge stored outside the context window, retrieved on demand. Implemented with vector databases (Supabase pgvector, Pinecone, Chroma), BM25 indexes, or hybrid search.

**Write policy:** Written when an interaction produces a meaningful artifact — a decision, a corrected error, a learned preference. Gated by quality: not every conversation turn should be stored.

**Retrieval trigger:** Just before each LLM call, run a semantic search for the top-K most relevant memories given the current task. Inject the results into Layer 1 as a `<memory>` block.

**Tools:** Mem0, LangMem, claude-mem, or a simple Postgres table with pgvector.

```python
# Retrieve relevant memories before each LLM call
def build_prompt(user_message: str, memory_store) -> str:
    relevant = memory_store.search(user_message, top_k=5)
    memory_block = "\n".join(f"- {m.text}" for m in relevant)
    return f"<memory>\n{memory_block}\n</memory>\n\nUser: {user_message}"
```

**What belongs here:**
- Past conversations and their outcomes
- User preferences discovered over time
- Factual knowledge retrieved from external documents
- Error patterns and their resolutions

### Layer 3 — Persistent State (Procedural Memory)

The agent's long-term behavioral configuration. Skills, routing preferences, project conventions, and learned patterns that survive across all sessions and inform every task.

**Write policy:** Gated behind verified success. A pattern is only promoted to Layer 3 after it has produced correct results multiple times. This is the slowest layer to update and the highest-signal layer to read.

**Implementation:** `CLAUDE.md`, `DEVLOG.md`, skills registry files, or a structured config loaded at agent startup. LangGraph uses this layer for workflow checkpoints and procedural consistency.

**What belongs here:**
- Project-specific coding conventions
- Known-good prompt templates
- Skill registry (`skill_name → prompt/tool`)
- Routing preferences (which model to use for which task type)
- Error patterns to watch for

```python
# Layer 3 loaded once at startup
class AgentConfig:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.skills = yaml.safe_load(f)["skills"]
            self.routing = yaml.safe_load(f)["model_routing"]
            self.conventions = yaml.safe_load(f)["conventions"]
```

## Write Policies by Layer

| Layer | When to Write | Gating Condition |
|-------|--------------|-----------------|
| 1 | Every token | None — it's ephemeral |
| 2 | End of interaction | Quality score > threshold, or explicit `remember()` call |
| 3 | After N verified successes | Promoted by skill_promoter after 3+ wins with no failures |

## Production Advice

**Trim Layer 1 aggressively.** Most agents stuff too much into context. Use a sliding window of the last 10 turns, not the full history. Move anything older than the current task to a Layer 2 retrieval query.

**Run retrieval *before* building the prompt, not after.** The most common mistake is forgetting to call the memory store. Make retrieval a required step in your prompt-building function, not an optional enhancement.

**Version your Layer 3 config.** `CLAUDE.md` and skills registries are code. Track them in git. When an agent starts behaving differently, the diff in Layer 3 is usually the cause.

**Implement a promotion pipeline for Layer 2 → Layer 3.** Don't manually curate Layer 3. Build a `skill_promoter` that watches Layer 2 for patterns that appear repeatedly with high success rates and automatically proposes them for Layer 3 promotion. A human reviews the proposal; the promoter handles detection.

**Set a memory budget per retrieval.** Don't inject all K results into Layer 1. Cap retrieved memory at ~20% of your context window. If you're on a 128K context, that's ~25K tokens for memory — plenty for the top-5 most relevant items.

## Common Mistakes

- **Treating context as unlimited.** Effective attention degrades before the hard limit. Design for a usable context of 60-70% of the window maximum.
- **Writing to Layer 2 on every turn.** Storage costs and retrieval noise both grow. Only store turns that contain a decision, correction, or preference signal.
- **Promoting to Layer 3 too fast.** One successful use of a pattern is not a signal. Wait for 3+ verified successes. Premature promotion bakes in brittle patterns.
- **No TTL on Layer 2 items.** Stale memories that contradict current state cause subtle errors. Add a `last_accessed` timestamp and decay the relevance score for items not accessed in 30+ days.

## When to Use This Architecture

Use the full three-layer stack when:
- Agents run across multiple sessions and need memory continuity
- Tasks require knowledge that doesn't fit in a single context window
- You want agent behavior to improve over time through learned patterns

Simplify when:
- Single-session, single-task agents with no memory requirements — Layer 1 only
- Stateless agents where reproducibility matters more than memory — no Layer 2/3

## Related Patterns

- **[[Context Rot]]** — the degradation that Layer 2/3 retrieval prevents
- **[[LangGraph]]** — uses Layer 3 for workflow checkpoints
- **[[Archivist Archetype]]** — the agent persona that manages the memory stack
- **[[Supervisor-Worker Pattern]]** — supervisors commonly maintain Layer 3 state; workers are stateless

## Key Concepts
[[Three-Layer Memory Stack]] [[In-Context Memory]] [[External Retrieval]] [[Persistent State]] [[Context Rot]] [[LangGraph]] [[Vector Databases]]

## Sources
- 2026-04-05-three-layer-memory-stack-for-ai-agents.md
