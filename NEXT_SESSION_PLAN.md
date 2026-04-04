# LORE — Next Session Plan
**Saved: 2026-04-05 | Pick up here next session**

## What LORE is
Living Operational Research Engine — self-growing AI agent pattern wiki + MCP server for Claude Code.
- `/root/lore-mcp/` — MCP server (9 tools)
- `/root/wikis/ai-agents/` — 26-article Codex, 115 nodes, 208 edges
- `THE_CODEX.md` — 15-chapter narrative universe (The Breaker, The Council, etc.)
- `/etc/cron.d/lore-evolve` — 2am daemon auto-grows wiki

## GitHub Repo — IN PROGRESS
Repo: `Miles0sage/ai-agent-codex` (create if not exists)

### What goes in the repo
```
ai-agent-codex/
  README.md              ← flagship README (see spec below)
  THE_CODEX.md           ← 15-chapter story (copy from /root/lore-mcp/)
  pyproject.toml         ← LORE MCP installable package
  lore/                  ← MCP server (copy from /root/lore-mcp/lore/)
    server.py
    search.py
    archetypes.py
    __init__.py
  wiki/                  ← 26 Codex articles (copy from /root/wikis/ai-agents/wiki/)
  scripts/
    evolve_daemon.sh     ← auto-evolve script
  dwiki.yaml             ← wiki config (copy from /root/wikis/ai-agents/dwiki.yaml)
  .github/
    CONTRIBUTING.md      ← how to add new patterns + archetypes
```

### What stays OUT (private)
- AI Factory internals (/root/ai-factory/)
- OpenClaw/openclaw
- notebooklm_push.py backend details (NotebookLM cookie)
- Personal API keys

## README Spec
Title: "The AI Agent Codex — A Living Pattern Library for Intelligent Systems"
Sections:
1. Hook: "Circuit breakers, dead letter queues, reviewer loops — not just patterns. Characters."
2. The 15 archetypes listed with names (The Breaker, The Archivist, etc.)
3. Quick install: `claude mcp add lore -- python3 -m lore.server`
4. 3 demo screenshots: lore_search, lore_story, lore_status output
5. "Build your own Codex" section — fork guide
6. The Codex Chronicles excerpt (Chapter II: The Breaker)
7. Contributing

## Next Session Tasks (in order)
1. `gh repo create Miles0sage/ai-agent-codex --public --description "..."`
2. Copy files into repo dir: lore/, wiki/, THE_CODEX.md, pyproject.toml, scripts/, dwiki.yaml
3. Write README.md (use AI Factory / Opus for quality)
4. `git add . && git commit && git push`
5. `dwiki serve` → deploy to Vercel (public Codex website)
6. Tweet thread draft using THE_CODEX.md excerpt
7. HN submission draft: "Show HN: LORE — Living AI Agent Codex with character archetypes"

## Key Files Reference
- MCP server: `/root/lore-mcp/lore/server.py`
- Archetypes (15): `/root/lore-mcp/lore/archetypes.py`
- Codex Chronicles: `/root/lore-mcp/THE_CODEX.md`
- Wiki articles: `/root/wikis/ai-agents/wiki/*.md`
- Wiki config: `/root/wikis/ai-agents/dwiki.yaml`
- Evolve daemon: `/root/lore-mcp/scripts/evolve_daemon.sh`
- Cron: `/etc/cron.d/lore-evolve`

## Claude Code MCP
Already registered globally:
`claude mcp add --scope user lore -- python3 -m lore.server`
Runs from /root/lore-mcp

## The Pitch (for README/HN)
"Most pattern libraries are dead the day they're written. LORE detects its own knowledge gaps,
researches them autonomously, compiles new articles nightly, and lives inside your AI coding
assistant. It also has characters: The Breaker guards the gate. The Archivist keeps the lost
messages. The Council judges every output. Install once. It grows forever."
