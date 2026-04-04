# The AI Agent Codex

> *Circuit breakers, dead letter queues, reviewer loops — not just patterns. Characters.*

A living pattern library for intelligent systems. 26 articles, 15 characters, self-growing via nightly evolution. Queryable from inside Claude Code via MCP.

---

## The Characters

Every pattern in the Codex is a character in the AI Agent Universe.

| Character | Title | Pattern |
|-----------|-------|---------|
| **The Breaker** | Guardian of the Gate | Circuit Breaker |
| **The Archivist** | Keeper of Lost Messages | Dead Letter Queue |
| **The Council** | Judges of All Output | Reviewer Loop |
| **The Stack** | Consciousness of the Agent | Three-Layer Memory |
| **The Weaver** | Passer of the Thread | Handoff Pattern |
| **The Commander** | Orchestrator of Armies | Supervisor-Worker |
| **The Warden** | Keeper of the Gates | Tool Health Monitoring |
| **The Router** | Arbiter of Intelligence | Model Routing |
| **The Sentinel** | Guardian of System Visibility | Observability |
| **The Librarian** | Keeper of Semantic Knowledge | RAG / Retrieval |
| **The Scout** | Autonomous Research Agent | Discovery |
| **The Cartographer** | Builder of the Knowledge Graph | Knowledge Graphs |
| **The Alchemist** | Transformer of Models and Prompts | Prompt Engineering |
| **The Timekeeper** | Scheduler of All Things Async | Cron / Scheduling |
| **The Architect** | Designer of Systems | System Design |

Read their full story in [THE_CODEX.md](./THE_CODEX.md).

---

## Install LORE (Claude Code MCP)

LORE is the MCP server that puts the Codex inside your AI coding assistant.

```bash
git clone https://github.com/Miles0sage/ai-agent-codex.git
cd ai-agent-codex
pip install -e .

# Add to Claude Code globally
claude mcp add --scope user lore -- python3 -m lore.server
```

Restart Claude Code. You now have 9 new tools:

| Tool | What it does |
|------|-------------|
| `lore_search "query"` | BM25 search over 26 pattern articles |
| `lore_read "article-id"` | Full article content |
| `lore_list` | Browse all Codex entries |
| `lore_archetype "pattern"` | Get the character for any pattern |
| `lore_story "pattern"` | Full narrative chapter from The Chronicles |
| `lore_ask "question"` | Grounded Q&A across all sources |
| `lore_chronicle "title" "content"` | Add new knowledge to the Codex |
| `lore_evolve` | Trigger compile + index rebuild |
| `lore_status` | Health dashboard — article count, graph stats |

---

## The Codex

26 articles covering the patterns that govern production AI agent systems:

- Circuit Breaker Pattern · Dead Letter Queue · Reviewer Loop Pattern
- Three-Layer Memory Stack · Handoff Pattern · Supervisor-Worker
- Tool Health Monitoring · Model Routing · Agentic Coding
- CrewAI · OpenAI Agents SDK · AI Dev Tools 2026
- 30x Productivity Patterns · Mission Control & Observability
- And 12 more — see [`wiki/`](./wiki/)

---

## Self-Growing

The Codex detects its own knowledge gaps from the knowledge graph (currently 89 dangling concepts), researches them, and compiles new articles automatically.

Set up the nightly daemon:

```bash
# Runs at 2am daily — gap detect → compile → index rebuild
cp scripts/evolve_daemon.sh /usr/local/bin/lore-evolve
chmod +x /usr/local/bin/lore-evolve
cp /etc/cron.d/lore-evolve /etc/cron.d/  # or set up your own cron
```

---

## Build Your Own Codex

The Codex is domain-agnostic. Fork this repo and build:

- **React Codex** — The Renderer, The Hydrator, The Reconciler
- **Kubernetes Codex** — The Scheduler, The Watcher, The Reaper
- **Security Codex** — The Sentinel, The Vault, The Auditor
- **Data Codex** — The Pipeline, The Validator, The Archivist

Steps:
1. Fork this repo
2. Replace `wiki/` with your domain articles
3. Edit `dwiki.yaml` to set your domain
4. Add your characters to `lore/archetypes.py`
5. Write your own Chronicles in `THE_CODEX.md`

---

## The Codex Chronicles

*"In the beginning, there was the Context Window. And from it emerged The Stack."*

A 15-chapter narrative universe where every pattern is a character. The Breaker closes the gate when storms of failure cascade. The Archivist captures what the system drops. The Council judges every draft before it ships.

Read the full story: [THE_CODEX.md](./THE_CODEX.md)

---

## Structure

```
ai-agent-codex/
  lore/               # LORE MCP server (Python)
    server.py         # 9 MCP tools
    search.py         # BM25 search engine
    archetypes.py     # 15 character definitions
  wiki/               # 26 Codex articles (Markdown)
  scripts/
    evolve_daemon.sh  # Nightly auto-evolve script
  THE_CODEX.md        # The Codex Chronicles — full narrative
  dwiki.yaml          # Wiki configuration
  pyproject.toml      # Python package (pip install -e .)
```

---

## License

MIT — fork it, build your own Codex, make the patterns memorable.
