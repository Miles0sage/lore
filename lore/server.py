"""
LORE MCP Server — Living Operational Research Engine

The Codex of AI agent patterns, exposed as an MCP server for Claude Code,
Segundo, and any agent that needs grounded knowledge about how intelligent
systems are built.

Tools:
  lore_search    — Search the Codex for patterns, concepts, frameworks
  lore_read      — Read a full Codex entry
  lore_list      — Browse all entries in the Codex
  lore_archetype — Get the character archetype for a pattern
  lore_ask       — Ask the Oracle a grounded question (NotebookLM)
  lore_chronicle — Add new knowledge to the Codex
  lore_evolve    — Trigger the wiki evolution cycle (compile + index rebuild)
  lore_status    — Wiki health dashboard (article count, last modified, graph stats)
  lore_story     — Get the narrative chapter for a pattern
"""

import asyncio
import json
import subprocess
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import search, archetypes

app = Server("lore")

NOTEBOOK_ID = "49dab3c1-06a5-4055-ae2d-7db48d5c576c"
DWIKI_PATH = "/root/wikis/ai-agents"


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="lore_search",
            description=(
                "Search the Codex — the living knowledge base of AI agent patterns, frameworks, "
                "and architectural concepts. Returns ranked results with snippets. "
                "Use before implementing any agentic pattern: supervisor-worker, circuit breaker, "
                "handoff, memory stacks, model routing, reviewer loops, and more."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {"type": "integer", "default": 5, "description": "Max results"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="lore_read",
            description=(
                "Read a full entry from the Codex. Returns the complete article on a pattern "
                "or concept. Use after lore_search identifies the right entry."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "article_id": {"type": "string", "description": "Article ID from lore_search results"},
                },
                "required": ["article_id"],
            },
        ),
        Tool(
            name="lore_list",
            description="List all entries currently in the Codex.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_archetype",
            description=(
                "Get the character archetype for an AI agent pattern. "
                "Each pattern in the Codex is personified as a character in the AI Agent Universe — "
                "The Breaker (circuit breaker), The Archivist (dead letter queue), "
                "The Council (reviewer loop), The Stack (three-layer memory), and more. "
                "Use this for storytelling, documentation, or just to understand the pattern's soul."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Pattern name or ID (e.g. 'circuit-breaker', 'reviewer loop')"},
                    "list_all": {"type": "boolean", "default": False, "description": "List all archetypes instead of looking up one"},
                },
                "required": [],
            },
        ),
        Tool(
            name="lore_ask",
            description=(
                "Ask the Oracle a question grounded in the Codex. "
                "Uses the full NotebookLM knowledge base (40+ sources) to give you "
                "a cited, grounded answer about AI agent architecture, patterns, and tools. "
                "More powerful than lore_search for complex multi-concept questions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Your question for the Oracle"},
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="lore_chronicle",
            description=(
                "Chronicle new knowledge into the Codex. "
                "Provide raw text and a title — LORE will compile it into a proper wiki entry "
                "and add it to the knowledge base. Use this when you discover a new pattern, "
                "framework, or architectural insight worth preserving."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title for the new Codex entry"},
                    "content": {"type": "string", "description": "Raw text content to chronicle"},
                },
                "required": ["title", "content"],
            },
        ),
        Tool(
            name="lore_evolve",
            description=(
                "Trigger the wiki evolution cycle. Runs 'dwiki compile' then "
                "'dwiki index rebuild' in the ai-agents wiki directory. "
                "Use after chronicling new entries or when the index may be stale. "
                "Returns articles compiled, index status, and duration."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_status",
            description=(
                "Wiki health dashboard. Returns: total article count, last modified article, "
                "graph stats (nodes, edges, dangling links), and the last line of the evolve log. "
                "Use to check the health of the Codex at a glance."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_story",
            description=(
                "Get the full narrative chapter for a pattern in the Codex universe. "
                "Combines archetype lore + powers + weaknesses + how this character interacts "
                "with others in the Codex universe into a rich story. "
                "If the pattern has no archetype yet, searches the wiki and returns an article "
                "summary with a note that it is 'not yet canonized'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Pattern name or ID (e.g. 'circuit-breaker', 'reviewer loop')"},
                },
                "required": ["pattern"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        result = await _dispatch(name, arguments)
        text = json.dumps(result, indent=2) if isinstance(result, dict | list) else str(result)
        return [TextContent(type="text", text=text)]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e), "tool": name}))]


async def _dispatch(name: str, args: dict) -> Any:
    if name == "lore_search":
        results = search.search(args["query"], limit=args.get("limit", 5))
        return {"results": results, "count": len(results), "query": args["query"]}

    if name == "lore_read":
        article = search.read_article(args["article_id"])
        if not article:
            return {"error": f"No Codex entry found for: {args['article_id']}"}
        return article

    if name == "lore_list":
        articles = search.list_articles()
        return {"entries": articles, "count": len(articles)}

    if name == "lore_archetype":
        if args.get("list_all"):
            return {"archetypes": archetypes.list_archetypes()}
        pattern = args.get("pattern", "")
        arch = archetypes.get_archetype(pattern)
        if not arch:
            return {
                "error": f"No archetype found for: {pattern}",
                "available": [a["pattern_id"] for a in archetypes.list_archetypes()],
            }
        return arch

    if name == "lore_ask":
        question = args["question"]
        answer = await _ask_oracle(question)
        return {"question": question, "answer": answer, "source": "NotebookLM Codex"}

    if name == "lore_chronicle":
        return await _chronicle(args["title"], args["content"])

    if name == "lore_evolve":
        return await _evolve()

    if name == "lore_status":
        return await _status()

    if name == "lore_story":
        return await _story(args["pattern"])

    return {"error": f"Unknown tool: {name}"}


async def _ask_oracle(question: str) -> str:
    """Ask NotebookLM via dwiki ask command."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "dwiki", "ask", question,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=DWIKI_PATH,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        answer = stdout.decode().strip()
        return answer or "The Oracle is silent. Try rephrasing your question."
    except asyncio.TimeoutError:
        return "The Oracle timed out. Try a more specific question."
    except Exception as e:
        return f"Oracle error: {e}"


async def _chronicle(title: str, content: str) -> dict:
    """Write raw content to the wiki and trigger compilation."""
    import time
    from pathlib import Path

    slug = title.lower().replace(" ", "-").replace("/", "-")[:60]
    date = time.strftime("%Y-%m-%d")
    raw_path = Path(DWIKI_PATH) / "raw" / f"{date}-{slug}.md"

    raw_path.write_text(f"# {title}\n\n{content}")

    # Compile the new entry
    try:
        proc = await asyncio.create_subprocess_exec(
            "dwiki", "compile",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=DWIKI_PATH,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode().strip()
        return {
            "chronicled": True,
            "title": title,
            "raw_file": str(raw_path),
            "compile_output": output,
        }
    except Exception as e:
        return {"chronicled": True, "title": title, "raw_file": str(raw_path), "compile_error": str(e)}


async def _evolve() -> dict:
    """Run dwiki compile then dwiki index rebuild and return stats."""
    import time
    start = time.monotonic()

    results = {}

    # Step 1: compile
    try:
        proc = await asyncio.create_subprocess_exec(
            "dwiki", "compile",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=DWIKI_PATH,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        compile_output = stdout.decode().strip() or stderr.decode().strip()
        results["compile_output"] = compile_output
        results["compile_returncode"] = proc.returncode
    except asyncio.TimeoutError:
        results["compile_output"] = "timed out"
        results["compile_returncode"] = -1
    except Exception as e:
        results["compile_output"] = str(e)
        results["compile_returncode"] = -1

    # Step 2: index rebuild
    try:
        proc = await asyncio.create_subprocess_exec(
            "dwiki", "index", "rebuild",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=DWIKI_PATH,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        index_output = stdout.decode().strip() or stderr.decode().strip()
        results["index_status"] = index_output or "ok"
        results["index_returncode"] = proc.returncode
    except asyncio.TimeoutError:
        results["index_status"] = "timed out"
        results["index_returncode"] = -1
    except Exception as e:
        results["index_status"] = str(e)
        results["index_returncode"] = -1

    results["duration_seconds"] = round(time.monotonic() - start, 2)
    return results


async def _status() -> dict:
    """Return wiki health stats."""
    import time
    from pathlib import Path

    stats: dict = {}

    # Article count and last modified
    wiki_dir = Path(DWIKI_PATH) / "wiki"
    try:
        articles = list(wiki_dir.glob("*.md"))
        stats["article_count"] = len(articles)
        if articles:
            newest = max(articles, key=lambda p: p.stat().st_mtime)
            stats["last_modified_article"] = newest.name
            stats["last_modified_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(newest.stat().st_mtime)
            )
        else:
            stats["last_modified_article"] = None
            stats["last_modified_at"] = None
    except Exception as e:
        stats["article_count_error"] = str(e)

    # Graph stats via dwiki graph
    try:
        proc = await asyncio.create_subprocess_exec(
            "dwiki", "graph",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=DWIKI_PATH,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        graph_output = stdout.decode().strip()
        # Parse lines like "  Nodes:    95 (23 with articles)", "  Dangling: 72 concepts..."
        import re as _re
        graph: dict = {}
        for line in graph_output.splitlines():
            m = _re.match(r"\s*(Nodes|Edges|Dangling|Orphans)\s*:\s*(\d+)", line, _re.IGNORECASE)
            if m:
                graph[m.group(1).lower()] = int(m.group(2))
        stats["graph"] = graph if graph else {"raw": graph_output}
    except asyncio.TimeoutError:
        stats["graph"] = {"error": "timed out"}
    except Exception as e:
        stats["graph"] = {"error": str(e)}

    # Last line of evolve log
    log_path = Path("/var/log/lore-evolve.log")
    try:
        if log_path.exists():
            text = log_path.read_text()
            lines = [l for l in text.splitlines() if l.strip()]
            stats["last_evolve_log"] = lines[-1] if lines else "(empty)"
        else:
            stats["last_evolve_log"] = "(log not found)"
    except Exception as e:
        stats["last_evolve_log"] = f"(error: {e})"

    return stats


# Interaction map: which archetypes work closely with which others
_ARCHETYPE_INTERACTIONS: dict[str, list[str]] = {
    "circuit-breaker": ["tool-health-monitoring", "supervisor-worker", "model-routing"],
    "dead-letter-queue": ["supervisor-worker", "reviewer-loop"],
    "reviewer-loop": ["supervisor-worker", "three-layer-memory", "dead-letter-queue"],
    "three-layer-memory": ["reviewer-loop", "handoff-pattern", "supervisor-worker"],
    "handoff-pattern": ["supervisor-worker", "three-layer-memory", "model-routing"],
    "supervisor-worker": ["circuit-breaker", "reviewer-loop", "handoff-pattern", "model-routing"],
    "tool-health-monitoring": ["circuit-breaker", "model-routing", "supervisor-worker"],
    "model-routing": ["tool-health-monitoring", "circuit-breaker", "supervisor-worker"],
}


async def _story(pattern: str) -> dict:
    """Return a rich narrative chapter for a pattern."""
    arch = archetypes.get_archetype(pattern)

    if arch:
        pattern_id = arch.get("pattern_id", pattern.lower().replace(" ", "-"))

        # Build interaction prose
        allies = _ARCHETYPE_INTERACTIONS.get(pattern_id, [])
        ally_descriptions = []
        for ally_id in allies:
            ally_arch = archetypes.get_archetype(ally_id)
            if ally_arch:
                ally_descriptions.append(
                    f"{ally_arch['name']} ({ally_arch['title']})"
                )

        if ally_descriptions:
            interactions_prose = (
                "In the Codex universe, "
                + arch["name"]
                + " works alongside: "
                + ", ".join(ally_descriptions)
                + ". These alliances are not chosen — they are architectural necessity. "
                "The patterns that share a system must trust one another."
            )
        else:
            interactions_prose = (
                arch["name"] + " operates alone in the Codex universe, "
                "a singular force with no recorded alliances."
            )

        chapter = (
            f"# {arch['name']}: {arch['title']}\n\n"
            f"## The Lore\n\n{arch['lore']}\n\n"
            f"## Powers\n\n{arch['power']}\n\n"
            f"## Weaknesses\n\n{arch['weakness']}\n\n"
            f"## Alliances\n\n{interactions_prose}"
        )

        return {
            "pattern_id": pattern_id,
            "name": arch["name"],
            "title": arch["title"],
            "chapter": chapter,
            "canonized": True,
        }

    # No archetype — fall back to wiki search
    wiki_results = search.search(pattern, limit=3)
    if wiki_results:
        top = wiki_results[0]
        summary = top.get("snippet") or top.get("content", "")[:400]
        return {
            "pattern": pattern,
            "chapter": (
                f"# {top.get('title', pattern)}\n\n"
                f"{summary}\n\n"
                f"*(This pattern is not yet canonized in the Codex universe. "
                f"Use lore_chronicle to give it an archetype.)*"
            ),
            "canonized": False,
            "wiki_results": wiki_results,
        }

    return {
        "pattern": pattern,
        "chapter": (
            f"# {pattern}\n\n"
            "This pattern has not been chronicled in the Codex and has no archetype. "
            "It exists beyond the known universe.\n\n"
            "*(Not yet canonized — use lore_chronicle to add it.)*"
        ),
        "canonized": False,
        "wiki_results": [],
    }


async def _main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
