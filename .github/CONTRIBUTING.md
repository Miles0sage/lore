# Contributing to The AI Agent Codex

The Codex works best when new entries stay grounded, composable, and easy to index.

## Add a New Pattern

1. Write a raw note in `raw/` in your working wiki workspace.
2. Compile it into `wiki/` with `dwiki compile`.
3. Rebuild indexes with `dwiki index rebuild`.
4. Add or update the matching archetype in `lore/archetypes.py` if the pattern should become canon.
5. Verify the result locally with `python3 -m lore.server` and the `lore_search` or `lore_read` tools.

## Article Guidelines

- Prefer one pattern or concept per article.
- Keep claims specific and operational, not abstract.
- Link related entries so the graph stays navigable.
- Note disagreements between sources instead of flattening them.
- Avoid secrets, tokens, internal URLs, or private infrastructure details.

## Archetype Guidelines

- Give each archetype a clear operational mapping, not just a name.
- Keep the lore memorable, but make the implementation guidance precise.
- Reuse existing archetypes when a pattern is just a variant, not a new class.

## Pull Requests

- Explain what pattern or gap the change covers.
- Mention whether search, story, or archetype behavior changed.
- Include the commands you ran for validation.
