# Lore Release Checklist

This checklist exists to keep the public release simpler than the private operator build.

## Public Release Must Keep

- Static Codex wiki
- Local search, read, list, archetype, and story tools
- Small scaffold library
- Optional local compile/index workflow

## Public Release Must Exclude Or Hide

- NotebookLM sync and private notebook IDs
- Proposal scoring heuristics tied to internal workflow
- Morning brief and weekly maintenance flows
- Operator telemetry
- Private source packs and question packs
- Autonomous ingestion and review automation

## Before Public Release

- Remove any hardcoded private notebook references
- Confirm docs do not imply NotebookLM is required
- Confirm operator-only commands are either hidden or clearly marked private
- Confirm public README describes the simple version, not the internal stack
- Confirm tests still pass without private credentials

## Private Build Checks

- Proposal queue is working
- Morning brief is useful
- Weekly canon report is useful
- Approved canon syncs cleanly to NotebookLM
- Public/private split is still clear in docs and code
