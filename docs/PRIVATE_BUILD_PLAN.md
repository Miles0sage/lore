# Private Build Plan

## Thesis

LORE should be built as a private operator tool first and an open-source reference product second.

The private build should answer one question every day: **what should the Codex learn next, what should be merged, and what should be kept out?**

That means the real product is not just search over articles. The real product is an **evolution loop**:

1. Capture new candidate knowledge
2. Score and review it
3. Compile it into canon
4. Measure coverage, duplication, and drift
5. Publish only the safe/simple slice

## What The Repo Can Already Do

- Serve the Codex over MCP with search, read, list, archetype lookup, story generation, scaffolding, chronicle, evolve, and status.
- Search local markdown articles quickly with BM25.
- Chronicle raw notes and compile them with `dwiki`.
- Expose a narrative frame that makes patterns memorable.
- Warn about missing reliability primitives through Claude hooks.

## What Is Missing

- A reliable private workspace mode with consistent local paths.
- A canonical evolution audit that tells us what to merge, write, or delete next.
- Review gates for newly ingested material before it becomes canon.
- A clean split between private automation features and the public OSS surface.
- Tests and validation around core search/tool behavior.

## Product Split

### Private Version

Keep private:

- Autonomous research and ingestion
- NotebookLM or other paid/private source connectors
- Internal scoring and review workflows
- Morning briefings, change summaries, and merge recommendations
- Any user/session memory or operator telemetry

NotebookLM should be the private synthesis layer:

- `lore_ask` uses the private notebook as the grounded oracle
- nightly evolve pushes reviewed canon into the notebook
- source packs and question packs live privately first
- product planning, merge decisions, and research ranking can be asked against the notebook

### Open-Source Version

Open source:

- Static Codex wiki
- MCP server with local search/read/list/story/archetype tools
- Small scaffold library for core patterns
- Optional local `dwiki` compile/index workflow

Do not open source by default:

- Private research automation
- Proprietary source packs
- Internal ranking heuristics tied to your workflow
- Auto-publish jobs

## Phased Build

## Phase 1: Make Self-Use Real

- Unify path/config resolution so the repo runs against itself locally.
- Make the evolve daemon runnable without private infrastructure.
- Add an evolution audit report to detect duplicate topics, canon gaps, and missing raw inputs.
- Add smoke tests for search and tool dispatch.

## Phase 2: Add Evolution Quality Gates

- Introduce a proposal queue in `raw/` with metadata: source, confidence, owner, review status.
- Score proposals on novelty, evidence quality, and overlap with existing canon.
- Require review before promotion from raw proposal to published article.
- Track rejected proposals so the system learns what not to ingest.
- Split NotebookLM inputs into:
  - canon articles
  - source packs
  - question packs
  - operator handoffs

## Phase 3: Operate It As A Daily Tool

- Generate a morning evolution brief:
  - new proposals
  - duplicate candidates
  - stale articles
  - archetypes lacking canon articles
  - suggested merges and deletions
- Add a weekly “canon maintenance” cycle for dedupe and refresh.
- Add operator-facing commands for approve, reject, merge, and archive.
- Add a NotebookLM sync brief after each approved evolution batch:
  - what changed
  - which articles were pushed
  - what questions to ask next

## Phase 4: Public Simplification

- Ship the clean static corpus.
- Keep only the simple MCP tools in the public release.
- Document how to plug in another wiki workspace locally.
- Remove or hide private-only automation behind env-gated modules.

## Immediate Backlog

1. Merge duplicate articles: `crewai`, `handoff-pattern`, `openai-agents-sdk`.
2. Add canonical article coverage for the character layer that exists only in lore: Sentinel, Librarian, Scout, Cartographer, Alchemist, Timekeeper, Architect.
3. Seed `raw/` with proposal briefs instead of relying on ad hoc future ingestion.
4. Wire NotebookLM as the private oracle and sync target using `scripts/notebooklm_push.py`.
5. Add source-pack and question-pack generation for major research themes.
6. Add tests for `search.py`, `server.py`, and the new evolution audit.
7. Decide the minimum public surface and treat everything else as internal.

## Working Rule

Every new feature should improve one of these:

- ingestion quality
- canon quality
- operator leverage
- publishability of the simple public version

If it only adds more lore without improving one of those, do not build it.
