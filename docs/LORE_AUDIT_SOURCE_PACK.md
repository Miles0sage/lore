# Lore Audit Source Pack

Date: 2026-04-06

Purpose: capture the highest-value reusable assets from adjacent local projects that can make Lore a real AgentOps product faster, without dragging their entire architectures into this repo.

## Product Direction

Lore should become an AgentOps audit and bootstrap layer.

That means:
- public surface: `lore scaffold`, `lore install`, `lore audit`
- private/operator surface: NotebookLM sync, proposal review, morning brief, evolution loop
- long-context model role: read very large repos and return structured gaps, not replace Lore's control plane

## Reusable Assets To Strip In

### 1. `google-mcp/tools_gemini.py`

What it gives:
- a minimal Gemini adapter for large-context analysis
- clean boundary between Lore and Google's model stack

Why it matters:
- Lore needs one heavy reader for full-codebase or fleet-scale audits
- the adapter is tiny and easy to reason about

What to keep:
- single-purpose analysis entry point
- optional dependency model

What to avoid:
- turning Lore into a generic Google MCP clone
- exposing Gemini as the default brain for everyday tasks

Immediate use in Lore:
- back `lore_audit` with Gemini for large-context repository analysis

### 2. `segundo/agent_sessions.py`

What it gives:
- persistent working memory
- project-specific context
- extracted reusable skills from past successful jobs

Why it matters:
- Lore's next useful jump after audit is continuity
- repeated operator questions and repeated audit follow-ups should not start from zero every session

What to keep:
- small JSON-backed session records
- recent task summaries
- per-project notes

What to avoid:
- importing the whole Segundo agent runtime
- overbuilding memory before the audit product proves value

Immediate use in Lore:
- later add lightweight operator memory for recurring audits and remediation loops

### 3. `ai-factory/health_monitor.py`

What it gives:
- stuck-loop detection
- low-progress drift detection
- reusable error classification patterns

Why it matters:
- a real AgentOps product should detect silent failure modes, not just describe patterns
- loop/drift/resource failure classes map cleanly onto Lore postmortems and audit findings

What to keep:
- loop/drift heuristics
- error-class to recovery-action mapping

What to avoid:
- AI Factory's full worker orchestration stack
- daemon/process supervision complexity

Immediate use in Lore:
- enrich audit findings and postmortem summaries with recovery guidance

### 4. `openclaw-agents` skills install UX

What it gives:
- explicit skill readiness state
- missing dependency display
- install affordances instead of silent failure

Why it matters:
- `lore install` is one of Lore's best adoption wedges
- installation must feel operational, not just "files were written somewhere"

What to keep:
- readiness/status framing
- missing env/bin/config reporting

What to avoid:
- importing GUI-specific code
- building a Mac app around Lore

Immediate use in Lore:
- improve `lore install` output into a clearer bootstrap report

## What Lore Should Build Now

### Build Now

1. `lore_audit`
- Gemini-backed large-context audit
- structured JSON report
- save reports into `.lore/audits/`

2. better `lore install`
- readiness-style output
- tell users what hooks, skills, and dependencies are actually active

3. audit-to-remediation loop
- use Lore findings to recommend specific scaffold/install actions

### Build Next

4. lightweight operator memory
- keep recurring audit context and past findings

5. fleet audit mode
- audit multiple agent repos/scripts in one run

6. richer failure classification
- loop, drift, resource, auth, timeout, permission

## What To Keep Out

- generic research sprawl
- broad NotebookLM product integration
- full multi-agent orchestration inside Lore
- UI-heavy skill management
- giant framework ambitions before audit proves demand

## Clean Product Position

Lore is not "another agent framework."

Lore is:
- the audit layer that finds missing production patterns
- the bootstrap layer that injects reliability into coding agents
- the operator layer that turns failures into reusable rules

Gemini reads the whole system.
Lore decides what matters.
