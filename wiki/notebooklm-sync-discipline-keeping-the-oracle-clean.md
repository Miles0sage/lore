# NotebookLM Sync Discipline — Keeping the Oracle Clean

NotebookLM is a private grounded reasoning layer, not a raw dump. The quality of its answers is directly proportional to the quality of its sources. Pushing unreviewed noise degrades every future query.

## The Rule

**Only approved canon enters the notebook.**

Raw proposals, draft articles, and queue noise stay in the raw directory until they pass the review gate. The `lore_publish` tool + `lore_notebook_sync` pipeline enforces this boundary.

## The Pipeline

```
raw/         →  lore_proposal_review (status=approved)
approved     →  lore_publish (writes wiki article, marks published)
published    →  lore_notebook_sync (pushes to NotebookLM, dry_run=False)
```

## What to Push

- Completed wiki articles with clear structure
- Synthesis documents that combine multiple patterns
- Question packs designed to surface gaps
- Source references with full URLs

## What Never to Push

- Half-written proposals
- Raw research dumps
- Personal notes or session logs
- Duplicate content before dedup pass

## Sync Frequency

Run `lore_notebook_sync` with `hours=24` once per day after the morning brief. The sync pack tells you exactly what changed and which follow-up questions to ask.

## The Oracle Feedback Loop

After sync, run the follow-up questions from the sync pack summary against `lore_ask`. The Oracle's answers identify what the canon is missing — feed those gaps back into new proposals. This is the Lore evolution cycle.

## Related Archetypes

- The Librarian (curates the canon, decides what enters)
- The Archivist (dead letter queue, preserves what was rejected)
