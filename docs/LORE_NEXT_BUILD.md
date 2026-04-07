# Lore Next Build Plan 2026-04-07

## Completed 2026-04-06
- Added `lore audit` (Gemini CLI audit runner, plan parser, saved reports in `.lore/audits`).
- Registered the tool via `lore.cli` and `lore.server`, added config/getters, and exercised it via `tests/test_audit.py` and the CLI command.
- Documented the broader product decision in `docs/LORE_PRODUCT_DECISIONS_2026-04-06.md` and captured sources in `docs/LORE_AUDIT_SOURCE_PACK.md`.
- Verified `pytest tests/test_audit.py tests/test_server.py tests/test_config.py -q` succeeded and created fresh audit reports (latest: `20260406-093246-what-is-the-best-gemini-cli.json`).

## Plan for 2026-04-07
1. Wrap `lore.audit.run_audit` with Lore patterns: circuit breaker, sentinel observability (prompt size/cost/lats), and a DLQ for failed audit prompts.
2. Promote the feature by adding a README section, usage example, and highlighting the Gemini CLI integration story.
3. Extend `lore.cli` to surface `audit --apply-fixes` and turn some findings into actionable `lore scaffold`/`lore install` commands.
4. Harden `lore install`: add `--dry-run`, record installations, provide `lore uninstall`, and offer verification after installing hooks.
5. Capture audit findings in `.lore/audits/` plus a summary doc for the team and coach NotebookLM with the latest plan/results.

## Questions to Ask NotebookLM
1. How should Lore position Gemini CLI to emphasize audits without making it the entire product?
2. What inspections should we add to future `lore install` verification steps?
3. Which `lore audit` findings are easiest to close to prove value quickly?
