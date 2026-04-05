# Lore Operator Workflow

This is the private operating loop for Lore. It is meant for daily use by the team, not for the public OSS cut.

## 1. Proposal Intake

Use `lore_proposal_create` when you find something worth preserving but not yet ready for canon.

Each proposal should capture:

- a clear title
- the source type, such as `paper`, `repo`, `video`, `official-docs`, `note`, or `manual`
- the owner
- a confidence estimate
- the proposal body
- the intended proposal type, such as `article`, `source-pack`, `question-pack`, or `handoff`

Lore scores proposals automatically for:

- novelty
- overlap with existing canon
- evidence quality
- strategic importance

If a proposal looks like a duplicate or near-duplicate, treat it as a merge candidate rather than fresh canon.

## 2. Review States

Use `lore_proposal_list` to inspect the queue, then `lore_proposal_review` to move items through the lifecycle.

Valid states are:

- `proposed`
- `in_review`
- `approved`
- `rejected`
- `merged`
- `published`
- `archived`

Practical rule:

- `proposed` means it exists but has not been triaged
- `in_review` means it is under active human or agent review
- `approved` means it can be promoted into canon or a source pack
- `rejected` means it should not enter canon in its current form
- `merged` means it was folded into another item
- `published` means it is canon or ready for downstream sync
- `archived` means it is no longer active but kept for history

## 3. Morning Brief

Use the morning brief to decide what matters before writing more content.

The brief should answer:

- what proposals are waiting
- which items are highest priority
- what duplicates need merging
- what canon gaps still exist
- what should be asked next

The operator should use the brief to choose one of four actions:

- approve
- reject
- merge
- publish

Do not use the brief as a passive dashboard. It is a decision aid.

## 4. NotebookLM Sync

NotebookLM is the private synthesis layer.

Lore should push approved canon and curated knowledge into the Lore notebook so the notebook can answer higher-level questions about product direction, merge decisions, and research ranking.

Sync intent:

- canon articles go in
- source packs go in
- question packs go in
- operator handoffs go in

Do not sync raw noise by default.

NotebookLM should be used for:

- grounded Q&A
- synthesis across sources
- planning next research questions
- validating the direction of the private build

## 5. Private vs Public

Keep private:

- proposal scoring
- review workflow
- NotebookLM sync
- source packs and question packs
- morning brief generation
- operator telemetry
- autonomous research and ingestion

Keep public:

- the static Codex wiki
- local search and read tools
- archetype and story tools
- the small scaffold library
- the optional local compile/index workflow

The public version should be simpler than the private version. If a feature depends on internal judgment, private data, or NotebookLM, it stays private.

## 6. Daily Use

A normal operator loop should look like this:

1. Check the morning brief.
2. Review top proposals.
3. Approve, reject, or merge items.
4. Promote approved material into canon.
5. Sync approved canon to NotebookLM.
6. Ask NotebookLM what to research or fix next.

If the loop does not improve ingestion quality, canon quality, operator leverage, or publishability, it is not part of the core workflow.
