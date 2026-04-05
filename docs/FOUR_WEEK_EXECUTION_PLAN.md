# Lore Four-Week Execution Plan

## Goal

Turn Lore from a searchable pattern library into a private, evolutionary operator tool that:

- captures new knowledge
- scores and reviews it
- promotes only strong material into canon
- syncs canon into NotebookLM as the private oracle
- keeps the public version simple

This plan is optimized for **internal usefulness first**. The open-source version is a later packaging exercise, not the main build target for the first month.

## Success Criteria After 4 Weeks

At the end of four weeks, Lore should be able to do the following reliably:

- run against its own local repo/workspace without path confusion
- track new knowledge proposals in a structured queue
- score and review proposals before publication
- detect duplicates, canon gaps, and stale areas
- produce a morning operator brief
- sync approved canon into the Lore NotebookLM notebook
- keep the public-facing feature set clearly separated from private automation

## Product Rule

Every feature built in this month must improve at least one of:

- ingestion quality
- canon quality
- operator leverage
- publishability of the simpler public version

If a feature only adds more lore or more narrative surface area, do not build it in month one.

## Build Principles

- Private-first beats public polish.
- Canon quality beats article count.
- Review gates beat auto-ingestion.
- Morning workflow beats passive storage.
- NotebookLM is the private synthesis layer, not the public product.
- The public repo should expose the clean codex, not the messy operator machinery.

## Week 1: Make Self-Use Real

### Objective

Stabilize the repo so Lore can run cleanly against itself as a local private workspace and expose the real current state of the codex.

### Why This Comes First

If the workspace is inconsistent, every later automation step becomes fragile. Path confusion, missing scripts, or broken local assumptions will make the “evolutionary” story fake. Week 1 is about making the base real.

### Main Outcomes

- one coherent local workspace mode
- evolution audit working
- core flows locally testable
- duplicate content surfaced and ready for cleanup

### Deliverables

1. Unified workspace/config resolution

Target:

- `lore` should work whether it is pointed at the repo itself or at another wiki workspace.
- `LORE_WIKI_DIR` should support either workspace root or direct `wiki/` path.

Files:

- [config.py](/root/lore/lore/config.py)
- [server.py](/root/lore/lore/server.py)
- [search.py](/root/lore/lore/search.py)
- [evolve_daemon.sh](/root/lore/scripts/evolve_daemon.sh)

Done when:

- local search works from repo checkout
- chronicle/evolve/status do not rely on hidden external paths
- logs and raw/wiki paths resolve predictably

2. Evolution audit report

Target:

- Lore should be able to answer: what is duplicated, what is missing, what needs canon coverage, what has no raw intake.

Files:

- [evolution.py](/root/lore/lore/evolution.py)
- [server.py](/root/lore/lore/server.py)

Done when:

- audit lists duplicate article groups
- audit lists uncovered archetypes
- audit lists practical next priorities

3. Local tests for core building blocks

Target:

- basic confidence in config resolution, search behavior, and audit behavior

Files:

- [tests/test_config.py](/root/lore/tests/test_config.py)
- [tests/test_search.py](/root/lore/tests/test_search.py)
- [tests/test_evolution.py](/root/lore/tests/test_evolution.py)

Done when:

- tests pass locally
- regressions in path handling or search are caught quickly

4. Duplicate-content cleanup pass

Target:

- merge or explicitly mark duplicate topics:
  - `crewai`
  - `handoff-pattern`
  - `openai-agents-sdk`

Why:

- dedupe is the first real test of canon maintenance
- it forces a standard for canonical slugs and article ownership

Done when:

- each topic has one canonical article
- secondary duplicates are removed or converted into redirects/merge notes

### Suggested Daily Breakdown

Day 1:

- finalize path/config handling
- verify local `search`, `status`, `evolve`, `chronicle`

Day 2:

- expand and verify evolution audit
- document current duplicate sets and coverage gaps

Day 3:

- add/fix tests
- standardize wiki-root assumptions across scripts/hooks

Day 4:

- merge duplicate topics
- decide canonical slug conventions

Day 5:

- clean README/docs to match actual runtime
- produce a “week 1 state” checkpoint

### Risks

- hidden external dependencies still exist
- duplicate articles contain conflicting material that requires editorial judgment
- test coverage remains too shallow

### Week 1 Exit Criteria

- `pytest` passes
- local workspace mode is stable
- audit works
- duplicate merge plan is either completed or clearly staged

## Week 2: Build The Proposal Queue And Review Gates

### Objective

Create the machinery that turns raw ideas into reviewed canon instead of directly turning every new note into published content.

### Why This Comes Second

Without review gates, “evolution” means uncontrolled growth. The whole point of Lore is to become a better memory system than a normal wiki, which means rejecting bad knowledge is as important as ingesting good knowledge.

### Main Outcomes

- structured proposal intake
- explicit review statuses
- promotion path from proposal to canon
- NotebookLM sync aligned to approved material only

### Deliverables

1. Proposal schema in `raw/`

Target:

- every proposal should carry metadata like:
  - title
  - source
  - created_at
  - owner
  - confidence
  - novelty score
  - overlap notes
  - review status
  - publish recommendation

Implementation options:

- YAML frontmatter in markdown proposal files
- separate JSON sidecars if needed later

Recommended v1:

- markdown files with frontmatter

Done when:

- new proposals can be created in a consistent format
- review state is machine-readable

2. Review state machine

Target states:

- `proposed`
- `in_review`
- `approved`
- `rejected`
- `merged`
- `published`
- `archived`

Why:

- Lore needs lifecycle, not just files

Done when:

- there is a clear path from proposal to canon
- rejected ideas are retained for learning

3. Proposal scoring

Target:

- score proposals for:
  - novelty
  - evidence quality
  - overlap with existing canon
  - strategic importance

Important:

- v1 scoring can be heuristic and simple
- it does not need to be “smart” to be useful

Good enough v1:

- overlap: compare tokens/titles against existing wiki
- novelty: penalize duplicates, reward uncovered archetypes/themes
- evidence quality: based on source type and completeness

Done when:

- proposals can be sorted into “review first” versus “ignore for now”

4. Promotion pipeline

Target:

- approved proposal moves into canon article generation/compile flow
- rejected proposal stays searchable in private ops history but does not enter canon

Done when:

- there is a clear command or script path from approved raw file to published article

5. NotebookLM sync boundaries

Target:

- sync only approved canon to NotebookLM by default
- define separate categories for:
  - canon articles
  - source packs
  - question packs
  - operator handoffs

Files:

- [notebooklm_push.py](/root/lore/scripts/notebooklm_push.py)

Done when:

- NotebookLM is fed intentionally, not as a dumping ground

### Suggested Daily Breakdown

Day 1:

- define proposal frontmatter schema
- create sample proposal files

Day 2:

- implement review statuses and parsing utilities

Day 3:

- implement heuristic scoring
- add tests for proposal parsing/scoring

Day 4:

- wire proposal approval to publication flow
- draft NotebookLM category boundaries

Day 5:

- run a real batch of 5 to 10 proposals through the review process
- revise schema based on friction

### Risks

- scoring becomes overcomplicated too early
- proposals are too loose and become inconsistent
- approval/publish path still depends too much on manual editing

### Week 2 Exit Criteria

- proposal schema exists
- review states exist
- at least one approved proposal has moved into canon
- NotebookLM sync policy is explicit

## Week 3: Make Lore A Daily Operator Tool

### Objective

Turn Lore into something you actually use every day, not just a better repo structure.

### Why This Comes Third

If the daily operating loop does not become habitual, Lore will drift back into “interesting internal wiki.” The habit-forming part is the operator brief and the next-action loop.

### Main Outcomes

- morning evolution brief
- actionable operator commands
- NotebookLM sync brief
- canonical missing content seeded

### Deliverables

1. Morning evolution brief

Target:

- one command/tool that summarizes:
  - new proposals
  - top proposals by score
  - duplicate candidates
  - stale articles
  - uncovered archetype areas
  - recommended merges
  - recommended next questions for NotebookLM

Recommended output style:

- concise, operator-first, high signal

Potential tool name:

- `lore_morning_brief`

Done when:

- you can start the day with one Lore-generated brief instead of manually inspecting the repo

2. Operator commands

Target commands/actions:

- approve proposal
- reject proposal
- merge duplicate
- archive stale proposal
- publish approved proposal
- sync latest canon to NotebookLM

Done when:

- common editorial actions do not require manual file surgery

3. NotebookLM sync brief

Target:

- after each approved publish batch, generate:
  - what changed
  - which articles were pushed
  - what source packs/question packs were updated
  - what to ask NotebookLM next

Why:

- Lore should create the next question, not wait passively

Done when:

- every sync results in suggested follow-up prompts

4. Seed missing canon areas

Priority targets:

- Sentinel
- Librarian
- Scout
- Cartographer
- Alchemist
- Timekeeper
- Architect

Why:

- these archetypes are already part of the Lore identity but not fully represented as canon coverage

Done when:

- each missing archetype has either a canonical article or a live approved proposal

5. First real weekly use cycle

Target:

- run Lore through one end-to-end operator week:
  - ingest
  - review
  - publish
  - sync
  - ask NotebookLM
  - refine next backlog

Done when:

- the workflow is proven in actual use, not just by reading code

### Suggested Daily Breakdown

Day 1:

- define brief format
- implement a first pass from audit + proposal data

Day 2:

- add approve/reject/publish actions

Day 3:

- implement sync brief
- generate next-question prompts automatically

Day 4:

- seed missing archetype proposals/articles

Day 5:

- run full weekly cycle retro
- document friction points

### Risks

- morning brief becomes too verbose
- operator commands are not ergonomic enough to use daily
- NotebookLM sync remains too manual

### Week 3 Exit Criteria

- morning brief exists and is useful
- operator actions exist
- sync brief exists
- at least several missing canon areas are seeded or published

## Week 4: Maintenance, Separation, And Public Packaging Boundary

### Objective

Stabilize the maintenance rhythm and explicitly define what belongs in the private product versus the public repo.

### Why This Comes Fourth

Too many tools fail because they never separate “internal messy power tool” from “public clean artifact.” Week 4 makes that separation explicit so you can keep moving fast privately without ruining the public release.

### Main Outcomes

- weekly canon maintenance cycle
- private/public boundary documented in code and docs
- minimal public feature set defined
- private automation clearly isolated

### Deliverables

1. Weekly canon maintenance cycle

Target:

- scheduled maintenance pass that checks:
  - duplicate content
  - stale articles
  - low-value proposals
  - missing canonical coverage
  - NotebookLM source quality

Potential output:

- `weekly_canon_report.md`

Done when:

- Lore has a maintenance rhythm instead of only reactive edits

2. Public/private feature boundary

Public:

- static wiki
- local search/read/list/story/archetype tools
- small scaffold library
- optional local compile/index

Private:

- proposal scoring
- review gates
- NotebookLM sync
- source packs
- question packs
- morning briefs
- operator telemetry
- autonomous ingestion

Done when:

- boundary is documented and enforced in code structure or env gating

3. Source-pack and question-pack generation

Target:

- for major themes, Lore should be able to produce:
  - a compact NotebookLM source pack
  - a compact question pack for synthesis

Why:

- this is how Lore becomes a research amplifier, not just a wiki

Done when:

- at least one theme can generate both pack types reliably

4. Public simplification pass

Target:

- identify what should be removed or hidden before open sourcing the simpler version

Checklist:

- no private notebook IDs
- no private source references
- no implicit operator-only commands in public docs
- no hidden assumption that NotebookLM exists

Done when:

- public repo can be understood without internal stack context

5. Four-week retrospective and next-month plan

Target:

- decide whether month two focuses on:
  - better proposal scoring
  - better operator UX
  - more canon coverage
  - more automated ingestion

Done when:

- next month is chosen based on usage evidence, not enthusiasm

### Suggested Daily Breakdown

Day 1:

- define weekly maintenance report format

Day 2:

- enforce public/private feature boundary in docs and module layout

Day 3:

- build first source-pack/question-pack generator

Day 4:

- perform public simplification review

Day 5:

- write retrospective and month-two priorities

### Risks

- public/private line stays fuzzy
- private workflows leak into public docs
- source-pack generation becomes overly manual

### Week 4 Exit Criteria

- weekly maintenance cycle exists
- public/private boundary is explicit
- at least one source-pack/question-pack flow exists
- month-two priorities are evidence-based

## Cross-Week Running Backlog

These should be tracked throughout the month, not treated as one-off tasks:

- merge duplicate topics
- fill missing archetype coverage
- improve search/result quality
- tighten docs to match actual behavior
- keep NotebookLM questions and source packs high signal
- avoid adding ornamental lore without operator value

## Recommended Minimal Commands/Tools To Add During This Month

Priority order:

1. `lore_evolution_report`
2. `lore_notebook_sync`
3. `lore_morning_brief`
4. `lore_proposal_create`
5. `lore_proposal_review`
6. `lore_publish`

## Weekly Review Questions

Ask these every Friday:

- Did Lore reduce operator time spent deciding what to read, merge, or write?
- Did this week improve canon quality or just increase content volume?
- What proposals were rejected, and why?
- What duplicate or stale content still exists?
- What did NotebookLM help answer that local search could not?
- What should stay private that we are still accidentally treating as public?

## The Hard Constraint

Do not treat article count as success.

In month one, success is:

- stronger intake
- stronger filtering
- stronger canon
- stronger daily operator loop

If article count goes up but clarity goes down, the month failed.
