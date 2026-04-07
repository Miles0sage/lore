# Lore Audit Feature — Codex Build 2026-04-06

## What Was Built

### lore audit — First Shipped Slice

Codex shipped the `lore_audit` command and MCP tool on 2026-04-06. 

**Components:**
- `lore/audit.py` — core audit engine
- CLI command: `lore audit`
- MCP tool: `lore_audit`
- Gemini CLI as long-context analysis backend
- Repository bundling (up to 120 files, 400K chars)
- Report persistence to `.lore/audits/` as timestamped JSON
- Remediation output — suggests `lore scaffold` / `lore install` actions

**Tests:** `tests/test_audit.py`, `tests/test_server.py` — all passing

### How It Works

1. `collect_audit_files(root)` — scans repo, excludes build dirs, prioritizes `lore/` > `tests/` > `docs/`
2. `build_audit_bundle(root)` — concatenates files into a single text bundle (max 400K chars)
3. `build_audit_prompt(question, bundle)` — constructs structured Gemini prompt requesting JSON output
4. `_run_gemini_cli(prompt)` — calls `gemini -m gemini-2.5-pro` via subprocess
5. `_extract_json_object(raw)` — parses JSON from Gemini output (handles fenced code blocks)
6. `suggest_lore_actions(parsed)` — maps findings to `lore scaffold` / `lore install` commands
7. `_write_report(question, report)` — persists to `.lore/audits/{timestamp}-{slug}.json`

### First Live Audit Findings

Top problems identified:
1. Circuit breaker state is process-local and not production-safe
2. Failed tasks are not persisted into a replayable DLQ
3. Feedback loops are analytical, not self-applying
4. Codex customization is still hardcoded
5. Dangerous operations need stronger verification coverage

### Action Mapping

Audit findings automatically map to lore patterns:
- "circuit" → `lore scaffold circuit_breaker`
- "dead letter" / "dlq" → `lore scaffold dead_letter_queue`
- "review" / "verification" → `lore scaffold reviewer_loop`
- "memory" / "resume" → `lore scaffold three_layer_memory`
- "routing" → `lore scaffold model_routing`
- "observability" / "telemetry" → `lore scaffold sentinel_observability`
- "health" → `lore scaffold tool_health_monitor`

### Next Builds (from NotebookLM ranking)

1. Wrap `run_audit` with circuit breaker + sentinel observability + DLQ for failed prompts
2. Add `audit --apply-fixes` CLI flag to turn findings into actionable commands
3. Harden `lore install`: `--dry-run`, record installations, `lore uninstall`, post-install verification
4. Operator memory so repeated audits keep context
5. README section highlighting Gemini CLI integration story

### Gemini CLI Decision

Gemini used as on-demand long-context reader, not Lore's default brain.
- Best role: fleet audit, full codebase audit, Lore self-improvement over wiki + telemetry + postmortems
- Not: broad strategic chat, generic Gemini integration across every command

### Reuse Assets Identified

- `google-mcp/tools_gemini.py` — minimal long-context adapter
- `ai-factory/health_monitor.py` — loop/drift heuristics and recovery classes
- `openclaw-agents` — readiness UX concepts for better `lore install`
- `segundo/agent_sessions.py` — lightweight operator memory (later)