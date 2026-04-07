# Lore Product Decisions — 2026-04-06

This note captures the current product direction after querying the Lore and Claude Code NotebookLM notebooks and shipping the first `lore_audit` slice.

## Core Decision

Lore should be built as:
- an AgentOps audit layer
- a bootstrap/install layer
- an operator feedback layer

Lore should not be built as:
- a NotebookLM product wrapper
- a generic agent framework
- a broad research kitchen sink

## NotebookLM Decision

NotebookLM stays separate.

Use it as:
- a private synthesis oracle
- a daily operator planning tool
- a source-ranking and merge-decision aid

Do not make it the public product core.

## Gemini / Google CLI Decision

Gemini should be used as an on-demand long-context reader, not Lore's default brain.

Best first role:
1. fleet audit
2. full codebase audit
3. Lore self-improvement over wiki + telemetry + postmortems

Not first:
- broad strategic chat product surface
- generic Gemini integration across every command

## What Was Built

### `lore_audit`

First shipped slice:
- CLI command: `lore audit`
- MCP tool: `lore_audit`
- Gemini CLI backend
- repository bundling and report persistence
- remediation output with suggested `lore scaffold` / `lore install` actions

Audit reports are saved under:
- `.lore/audits/`

## What The First Live Audit Said

Top problems:
1. circuit breaker state is still process-local and not production-safe
2. failed tasks are not persisted into a replayable DLQ
3. feedback loops are analytical, not self-applying
4. codex customization is still hardcoded
5. dangerous operations need stronger verification coverage

## Ranked Next Builds

From NotebookLM after shipping the first audit:
1. improve `lore install` so users can see what hooks, skills, and dependencies are actually active
2. add audit-to-remediation loops so audit findings turn into specific Lore actions
3. add lightweight operator memory so repeated audits keep context

## Reuse Guidance

Strip in next:
- `google-mcp/tools_gemini.py`: minimal long-context adapter
- `ai-factory/health_monitor.py`: loop/drift heuristics and recovery classes
- `openclaw-agents` skills readiness UX concepts for better `lore install`
- `segundo/agent_sessions.py`: lightweight operator memory later

Keep out for now:
- full AI Factory orchestration
- full Segundo runtime
- GUI-heavy OpenClaw surface area
- broad NotebookLM product integration
- multi-agent sprawl inside Lore itself
