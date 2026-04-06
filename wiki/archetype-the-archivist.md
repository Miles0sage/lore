# The Archivist

**"Nothing is forgotten. Everything is findable."**

---

## The Identity

**Archetype:** The Archivist  
**Domain:** Memory Architecture, Persistence, Session Continuity  
**Formal Pattern:** Three-Layer Memory Stack  
**Allied Archetypes:** The Librarian (RAG), The Stack (Memory Layers), The Timekeeper (Scheduled Memory), The Sentinel (Memory Health)

---

## The Lore

Context windows close. Sessions end. The conversation that took three hours, solved the problem, discovered the insight — gone. The next session starts cold, blind, without history.

Every agent starts as an amnesiac.

**The Archivist** refuses this. It watches every session, extracts what matters, routes it to where it will survive. The in-context window is temporary — The Archivist knows this and acts accordingly. Decisions get written to persistent config. Episodic history gets embedded and stored in the vector layer. Behavioral patterns get promoted to procedural memory.

The Archivist is the reason an agent improves over time instead of starting over every session.

---

## The Pattern

**Formal Name:** Three-Layer Memory Stack  
**Core Philosophy:** No single memory store fits all needs. Route knowledge to the right layer based on persistence requirements, retrieval latency tolerance, and signal strength. In-context for now, external retrieval for history, persistent config for what's always true.

---

## The Three Layers

### Layer 1 — In-Context (Working Memory)

What the agent knows right now. The active conversation window, tool call history, current task state.

- **Lifespan:** Session only. Evaporates on close.
- **Latency:** Zero. Already in the model's attention.
- **Capacity:** ~200K tokens (varies by model).
- **Use for:** Current task context, recent tool results, conversation so far.

**The Archivist's rule for Layer 1:** Keep it clean. Context rot sets in when Layer 1 accumulates too much. The Archivist periodically compacts Layer 1 — summarizing completed task sections, removing dead ends, preserving only active signal.

```python
async def compact_context(conversation: list) -> list:
    """Reduce context without losing signal"""
    if token_count(conversation) < COMPACT_THRESHOLD:
        return conversation
    
    # Summarize older turns, keep recent turns verbatim
    old_turns = conversation[:-KEEP_RECENT_N]
    recent_turns = conversation[-KEEP_RECENT_N:]
    
    summary = await llm.generate(f"""
    Summarize these conversation turns into a compact context block.
    Preserve: decisions made, key facts discovered, current task state.
    Remove: exploratory dead-ends, repeated content, verbose reasoning.
    
    Turns: {old_turns}
    """)
    
    return [{"role": "system", "content": f"[Context summary]: {summary}"}] + recent_turns
```

### Layer 2 — External Retrieval (Episodic/Semantic Memory)

Historical interactions, past decisions, domain knowledge. Persisted in vector databases. Survives sessions. Retrieved semantically before each LLM call.

- **Lifespan:** Permanent (until explicitly deleted).
- **Latency:** ~50-200ms retrieval time.
- **Capacity:** Unlimited (database scales).
- **Use for:** Past conversation history, user preferences discovered over time, project-specific facts, learned domain knowledge.

**The Archivist's write pattern:**

```python
async def archive_to_layer2(session_transcript: str, metadata: dict):
    """Extract and store the important parts of a session"""
    # LLM extracts 0-5 facts worth keeping
    extractions = await llm.generate(f"""
    From this session, extract 0-5 facts worth remembering long-term.
    Only extract facts that are:
    - Non-obvious (not in any documentation)
    - Persistent (will be true in future sessions)
    - Specific (not generic advice)
    
    Session: {session_transcript}
    
    Return JSON array: [{{"fact": "...", "category": "user_pref|project|technical|decision"}}]
    """)
    
    for extraction in extractions:
        embedding = embed(extraction["fact"])
        await vector_db.add(
            id=generate_id(),
            embedding=embedding,
            document=extraction["fact"],
            metadata={**metadata, "category": extraction["category"], "timestamp": time.time()}
        )
```

**The Archivist's read pattern (session start):**

```python
async def recall_for_session(user_id: str, task_context: str) -> str:
    """Inject relevant memories before session begins"""
    query_embedding = embed(task_context)
    memories = await vector_db.query(
        query_embedding,
        filter={"user_id": user_id},
        n_results=10
    )
    
    if not memories:
        return ""
    
    return f"""
[Recalled from previous sessions]
{chr(10).join(f'- {m}' for m in memories)}
[End of recalled memories]
"""
```

### Layer 3 — Persistent State (Procedural Memory)

Behavioral patterns, skill registries, routing preferences, project conventions. The highest-signal, slowest-to-change layer.

- **Lifespan:** Permanent. Only updated on verified success.
- **Latency:** Zero (loaded at session start, already in context).
- **Capacity:** Bounded (100-2000 lines). Discipline required.
- **Use for:** CLAUDE.md, SOUL.md, personality files, coding conventions, project architecture decisions.

**The Archivist's promotion pattern:**

```python
async def promote_to_layer3(candidate: str, evidence: str, file: str = "CLAUDE.md"):
    """
    Only promote to Layer 3 after verified success.
    A candidate is a behavioral pattern that worked.
    """
    # Check if candidate conflicts with existing Layer 3 content
    existing = read_file(file)
    conflict = await llm.generate(f"""
    Does this new rule conflict with existing rules?
    New: {candidate}
    Existing: {existing[-2000:]}
    Answer: conflict|no_conflict
    """)
    
    if conflict == "conflict":
        log.warning(f"Layer 3 conflict detected for: {candidate}")
        return
    
    # Append to persistent config
    append_to_file(file, f"\n- {candidate}  # Evidence: {evidence[:100]}")
    log.info(f"Promoted to Layer 3: {candidate}")
```

---

## The Memory Routing Decision

The Archivist's core judgment: which layer does this information belong in?

```
INFORMATION → The Archivist's decision tree:

Will this be needed only in this session?
  └─ YES → Layer 1 (in-context, don't write anywhere)
  └─ NO ↓

Is this a behavioral pattern / project convention / always-true rule?
  └─ YES → Layer 3 (persistent config — CLAUDE.md, SOUL.md)
  └─ NO ↓

Is this a fact, decision, or historical event worth recalling?
  └─ YES → Layer 2 (vector DB — embed and store)
  └─ NO → Discard (not everything deserves memory)
```

---

## Critical Use Cases — When The Archivist Acts

1. **End of every session** — Extract facts, embed them, write to Layer 2. The agent should improve with every conversation.

2. **Project onboarding** — New Claude Code session on an existing project. Layer 3 (CLAUDE.md) loads project conventions. Layer 2 retrieval loads recent decisions. Agent doesn't start from zero.

3. **SOUL.md hot-reload** — Segundo's personality file. The Archivist watches for updates and reloads personality without restarting the agent. Dynamic Layer 3.

4. **Per-agent memory scopes** — Different agents keep different memories: planner's plans, reviewer's findings, security reviewer's vulnerability patterns. The Archivist enforces scope separation — private vs shared memory.

5. **Context compaction before limits** — When Layer 1 approaches 80% of context window capacity, The Archivist compacts old sections and optionally promotes key facts to Layer 2 before resetting.

---

## The Alliance

**The Librarian (RAG):**  
The Archivist manages what goes into and comes out of Layer 2. The Librarian IS Layer 2's retrieval mechanism. The Archivist writes; The Librarian reads. They are the same system: Archivist is the architecture and governance, Librarian is the retrieval action.

**The Timekeeper:**  
End-of-session archiving is a Timekeeper job — fired by cron or session-end hook, not by the human. "Nightly memory consolidation" is The Archivist working while humans sleep.

**The Sentinel:**  
Monitors memory health: Layer 2 size, retrieval latency, hit rate. Are memories actually being recalled? Is the vector DB growing out of control? The Sentinel fires alerts when The Archivist's stores grow stale or oversized.

**The Warden:**  
What gets written to Layer 3 is irreversible without deliberate action. The Warden reviews Layer 3 promotions for safety — no accidentally-encoded bad behavior, no conflicting rules.

---

## Grimoire — Framework Implementations

**claude-mem (local file-based):**  
File-based memory for Claude Code sessions. Writes `~/.claude/projects/*/memory/*.md`. Low-tech Layer 2 with BM25 search. The pattern used in this wiki's own memory system.

**Mem0 (managed Layer 2):**  
Managed memory layer with vector + graph + keyword search. API-first. `mem0.add(messages, user_id)` → `mem0.search(query, user_id)`. Drop-in Layer 2 for any agent.

**LangMem:**  
LangChain's memory management library. Integrates with LangGraph for in-workflow memory operations. Supports extraction, consolidation, and session-boundary management.

**Supabase pgvector (Layer 2 self-hosted):**  
```sql
CREATE TABLE memories (
  id UUID PRIMARY KEY,
  user_id TEXT,
  content TEXT,
  category TEXT,
  embedding vector(1536),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops);
```

**CLAUDE.md / SOUL.md (Layer 3):**  
Plain markdown files loaded at session start. The Archivist appends to these on verified behavioral patterns. Hot-reload: watch for file changes, reload without session restart.

---

## Key Concepts

[[three-layer-memory-stack]] [[defeating-context-rot-mastering-the-flow-of-ai-sessions]] [[supervisor-worker-pattern]] [[agentic-coding]] [[agent-observability]]

---

## Related Archetypes

- **The Librarian** — Retrieval mechanism for The Archivist's Layer 2 store
- **The Timekeeper** — Schedules end-of-session memory consolidation
- **The Sentinel** — Monitors memory health and store growth
- **The Warden** — Reviews what gets promoted to permanent Layer 3
- **The Stack** — The Three-Layer Memory Stack personified; The Archivist is its keeper
