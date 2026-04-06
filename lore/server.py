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
import os
import subprocess
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import archetypes, briefing, dispatch, distill, eval_loop, evolution, fleet, maintenance, notebook, packs, postmortem, proposals, publisher, router_learner, routing, search, teaching
from .config import get_evolve_log_path, get_raw_dir, get_wiki_dir, get_workspace_root

app = Server("lore")

NOTEBOOK_ID = os.environ.get("LORE_NOTEBOOK_ID", "")
DWIKI_PATH = str(get_workspace_root())


@app.list_tools()
async def list_tools() -> list[Tool]:
    all_tools = [
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
            name="lore_evolution_report",
            description=(
                "Audit the Codex as a product, not just a wiki. Returns duplicate content, "
                "coverage gaps between articles/archetypes/scaffolds, and the highest-priority "
                "next steps for a private evolutionary build."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_proposal_create",
            description=(
                "Create a scored proposal in the private raw queue. "
                "Use this for new ideas that should be reviewed before they enter canon."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Proposal title"},
                    "content": {"type": "string", "description": "Proposal body"},
                    "source": {"type": "string", "default": "manual", "description": "Source type: manual, paper, repo, video, official-docs, note"},
                    "owner": {"type": "string", "default": "unknown", "description": "Human or agent owner"},
                    "confidence": {"type": "number", "default": 0.6, "description": "0.0-1.0 confidence in this proposal"},
                    "proposal_type": {"type": "string", "default": "article", "description": "article, source-pack, question-pack, handoff"},
                },
                "required": ["title", "content"],
            },
        ),
        Tool(
            name="lore_proposal_list",
            description=(
                "List proposals from the private raw queue, ranked by priority. "
                "Use this before morning review or publication decisions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Optional status filter"},
                    "limit": {"type": "integer", "default": 10, "description": "Max proposals to return"},
                },
            },
        ),
        Tool(
            name="lore_proposal_review",
            description=(
                "Update a proposal review state. "
                "Use to move proposals through proposed, in_review, approved, rejected, merged, published, or archived."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "Proposal id or slug fragment"},
                    "status": {"type": "string", "description": "New proposal status"},
                    "reviewer": {"type": "string", "default": "", "description": "Reviewer name"},
                    "notes": {"type": "string", "default": "", "description": "Review notes"},
                },
                "required": ["proposal_id", "status"],
            },
        ),
        Tool(
            name="lore_morning_brief",
            description=(
                "Generate the daily operator brief for Lore. "
                "Summarizes proposal queue health, duplicate topics, missing canon, and concrete next actions."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_publish",
            description=(
                "Promote an approved proposal into canon by writing a wiki article and marking the proposal as published. "
                "Use after review gates, not before."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proposal_id": {"type": "string", "description": "Proposal id or slug fragment"},
                    "reviewer": {"type": "string", "default": "", "description": "Reviewer/publisher name"},
                    "notes": {"type": "string", "default": "", "description": "Publication notes"},
                },
                "required": ["proposal_id"],
            },
        ),
        Tool(
            name="lore_notebook_sync",
            description=(
                "Push recently published canon into the configured Lore NotebookLM notebook and return a sync brief. "
                "This is private-only operator functionality."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {"type": "number", "default": 24, "description": "How far back to scan for modified canon articles"},
                    "dry_run": {"type": "boolean", "default": False, "description": "If true, build the sync pack without pushing"},
                },
            },
        ),
        Tool(
            name="lore_weekly_report",
            description=(
                "Generate the weekly canon maintenance report for private operators. "
                "Surfaces duplicate groups, canon gaps, low-value proposals, and next actions."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_pack_generate",
            description=(
                "Generate a first-pass source pack and question pack for a Lore theme. "
                "Use this for private NotebookLM ingestion and operator research loops."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "description": "Theme name like memory, routing, reliability, or research"},
                    "limit": {"type": "integer", "default": 5, "description": "Max articles in the source pack"},
                },
                "required": ["theme"],
            },
        ),
        Tool(
            name="lore_route",
            description=(
                "Classify a Lore task and assign it to the appropriate brain tier. "
                "Routes lightweight delegated work to DeepSeek, standard operator work to GPT-4.1, "
                "and high-judgment review/security tasks to GPT-5.4."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "Short task label like proposal_triage, canon_review, security_arch"},
                    "description": {"type": "string", "default": "", "description": "Optional natural-language task description"},
                },
                "required": ["task_type"],
            },
        ),
        Tool(
            name="lore_router_status",
            description=(
                "Show Lore's routing telemetry: model usage, acceptance/revision rates, dead-letter queue depth, "
                "and the current recommended task split."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 200, "description": "How many recent events to summarize"},
                },
            },
        ),
        Tool(
            name="lore_dispatch",
            description=(
                "Dispatch a task to the correct brain tier and get a real LLM response. "
                "Routes light work (extraction, triage, dedup) to DeepSeek, "
                "standard work (briefs, drafts, operator tasks) to GPT-4.1, "
                "and high-judgment work (security review, canon decisions, architecture) to GPT-5.4. "
                "Applies a circuit breaker: if a model tier fails repeatedly it escalates one tier up "
                "rather than silently routing all traffic to the most expensive model."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "Short label: proposal_triage, canon_review, morning_brief, security_arch, etc."},
                    "prompt": {"type": "string", "description": "The full prompt to send to the model"},
                    "system": {"type": "string", "default": "", "description": "Optional system prompt"},
                    "description": {"type": "string", "default": "", "description": "Short description for telemetry logs"},
                    "max_tokens": {"type": "integer", "default": 1024, "description": "Max tokens in response"},
                },
                "required": ["task_type", "prompt"],
            },
        ),
        Tool(
            name="lore_batch_review",
            description=(
                "Approve and publish all high-priority proposals in the raw queue in one pass. "
                "Targets proposals with publish_recommendation=review_now and priority_score >= threshold. "
                "Use this to drain the queue after a research cycle or after seeding new proposals."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "min_priority": {"type": "number", "default": 0.60, "description": "Minimum priority_score to auto-approve"},
                    "reviewer": {"type": "string", "default": "lore-batch", "description": "Reviewer name logged on each proposal"},
                    "dry_run": {"type": "boolean", "default": False, "description": "If true, show what would be published without writing"},
                },
            },
        ),
        Tool(
            name="lore_circuit_status",
            description=(
                "Show the current circuit breaker state for all model tiers. "
                "Reports failure counts and whether each model's circuit is open or closed. "
                "Use after dispatch errors to diagnose which models are degraded."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_eval_report",
            description=(
                "Show the current routing evaluation report. Analyzes router telemetry to identify "
                "per-model stats (failure rate, acceptance rate, cost) and misrouted tasks. "
                "Use to understand how well the brain router is performing before triggering a self-rewrite."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 500, "description": "How many recent events to analyze"},
                },
            },
        ),
        Tool(
            name="lore_router_learn",
            description=(
                "Trigger a self-rewrite cycle for the brain router. Reads telemetry, builds an eval report, "
                "sends it to GPT-5.4 for analysis, and updates .lore/routing_rules.json with improved keyword "
                "routing. Safety-gated: max 3 keyword changes per cycle. Creates a backup of previous rules."
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
        Tool(
            name="lore_scaffold",
            description=(
                "Generate production-ready scaffolding for an AI agent pattern and write it "
                "directly into your project. 15 archetypes: The Breaker, Archivist, Council, "
                "Commander, Warden, Weaver, Router, Stack, Sentinel, Librarian, Scout, "
                "Cartographer, Timekeeper, Architect, Alchemist. "
                "Supports framework variants: python (default), langgraph, crewai, openai_agents. "
                "Use after lore_search or lore_story identifies the right pattern."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "enum": [
                            "circuit_breaker", "dead_letter_queue", "reviewer_loop",
                            "supervisor_worker", "tool_health_monitor",
                            "handoff_pattern", "model_routing", "three_layer_memory",
                            "sentinel_observability", "librarian_retrieval",
                            "scout_discovery", "cartographer_knowledge_graph",
                            "timekeeper_scheduling", "architect_system_design",
                            "alchemist_prompt_routing",
                            "react_loop", "reflexion_loop", "plan_execute",
                        ],
                        "description": "Which pattern to scaffold",
                    },
                    "framework": {
                        "type": "string",
                        "enum": ["python", "langgraph", "crewai", "openai_agents"],
                        "default": "python",
                        "description": "Framework variant (default: pure python). Falls back to python if variant unavailable.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to write the file into (default: current working directory)",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": False,
                        "description": "If true, return the code without writing to disk",
                    },
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="lore_deploy",
            description=(
                "Generate deployment infrastructure scaffolds for AI agent systems. "
                "Produces Docker Compose, Kubernetes, Cloudflare Workers, or Dockerfile "
                "templates ready for production. Use to quickly bootstrap deployment config "
                "for multi-agent systems."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": ["docker_compose", "kubernetes", "cloudflare_worker", "dockerfile"],
                        "description": "Which deployment template to generate",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Directory to write the file into (optional, default: return content only)",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": True,
                        "description": "If true, return the template without writing to disk",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="lore_distill_report",
            description=(
                "Show trajectory distillation report with optimization opportunities. "
                "Analyzes successful dispatch trajectories grouped by task type, "
                "showing per-model success rates, costs, and latency. "
                "Identifies where cheaper models could be used to save cost."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 100, "description": "Max recent trajectories to analyze"},
                },
            },
        ),
        Tool(
            name="lore_postmortem_report",
            description=(
                "Show auto-postmortem report with failure analysis. "
                "Groups recent dispatch failures by class (timeout, rate_limit, auth_error, etc.), "
                "identifies the most failing task types and models, "
                "and generates defensive routing rules."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 50, "description": "Max recent postmortems to analyze"},
                },
            },
        ),
        Tool(
            name="lore_teach",
            description=(
                "Compile a Codex pattern into an injectable context package for another agent. "
                "Formats: claude_md (CLAUDE.md rules), system_prompt (LLM injection), "
                "skill (Claude Code skill file), mcp_description (tool description text). "
                "Use this to PUSH patterns into other agents' contexts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Pattern name or ID (e.g. 'circuit-breaker', 'reviewer-loop')"},
                    "format": {
                        "type": "string",
                        "default": "claude_md",
                        "enum": ["claude_md", "system_prompt", "skill", "mcp_description"],
                        "description": "Output format for the compiled lesson",
                    },
                },
                "required": ["pattern"],
            },
        ),
        Tool(
            name="lore_fleet_register",
            description=(
                "Register an agent to receive pattern updates from Lore. "
                "Specify the agent's preferred format and which patterns it subscribes to."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Unique agent identifier"},
                    "name": {"type": "string", "description": "Human-readable agent name"},
                    "format": {
                        "type": "string",
                        "enum": ["claude_md", "system_prompt", "skill", "mcp_description"],
                        "description": "Preferred lesson format",
                    },
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Pattern IDs to subscribe to, or ['*'] for all",
                    },
                },
                "required": ["agent_id", "name", "format", "patterns"],
            },
        ),
        Tool(
            name="lore_fleet_list",
            description="List all agents registered in the Lore fleet.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="lore_fleet_brief",
            description=(
                "Generate fleet-wide update packages for all registered agents. "
                "Compiles lessons for changed patterns, filtered per agent's subscriptions "
                "and formatted in each agent's preferred format."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of changed pattern IDs. If omitted, compiles all teachable patterns.",
                    },
                },
            },
        ),
        Tool(
            name="lore_teachable",
            description=(
                "List all patterns that have enough content to teach (archetype + article minimum). "
                "Shows which patterns have archetypes, articles, and scaffolds available."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]
    if _LORE_MODE == "public":
        return [t for t in all_tools if t.name not in _PRIVATE_TOOLS]
    return all_tools


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

    if name == "lore_evolution_report":
        return evolution.build_evolution_report()

    if name == "lore_proposal_create":
        return proposals.create_proposal(
            args["title"],
            args["content"],
            source=args.get("source", "manual"),
            owner=args.get("owner", "unknown"),
            confidence=float(args.get("confidence", 0.6)),
            proposal_type=args.get("proposal_type", "article"),
        )

    if name == "lore_proposal_list":
        results = proposals.list_proposals(
            status=args.get("status"),
            limit=args.get("limit", 10),
        )
        return {"proposals": results, "count": len(results)}

    if name == "lore_proposal_review":
        return proposals.review_proposal(
            args["proposal_id"],
            args["status"],
            reviewer=args.get("reviewer", ""),
            notes=args.get("notes", ""),
        )

    if name == "lore_morning_brief":
        return _morning_brief()

    if name == "lore_publish":
        return publisher.publish_proposal(
            args["proposal_id"],
            reviewer=args.get("reviewer", ""),
            notes=args.get("notes", ""),
        )

    if name == "lore_notebook_sync":
        return await _notebook_sync(
            hours=float(args.get("hours", 24)),
            dry_run=bool(args.get("dry_run", False)),
        )

    if name == "lore_weekly_report":
        return _weekly_report()

    if name == "lore_pack_generate":
        return packs.build_theme_pack(
            args["theme"],
            limit=args.get("limit", 5),
        )

    if name == "lore_batch_review":
        return _batch_review(
            min_priority=float(args.get("min_priority", 0.60)),
            reviewer=str(args.get("reviewer", "lore-batch")),
            dry_run=bool(args.get("dry_run", False)),
        )

    if name == "lore_dispatch":
        return await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: dispatch.dispatch_task(
                args["task_type"],
                args["prompt"],
                system=args.get("system", ""),
                description=args.get("description", ""),
                max_tokens=int(args.get("max_tokens", 1024)),
            ),
        )

    if name == "lore_circuit_status":
        return dispatch.get_circuit_status()

    if name == "lore_eval_report":
        return eval_loop.build_eval_report(limit=int(args.get("limit", 500)))

    if name == "lore_router_learn":
        return router_learner.learn_from_telemetry()

    if name == "lore_route":
        plan = routing.classify_task(
            task_type=args["task_type"],
            description=args.get("description", ""),
        )
        routing.log_router_event(
            task_type=plan["task_type"],
            model=plan["model"],
            status="planned",
            description=plan.get("description", ""),
        )
        return plan

    if name == "lore_router_status":
        return routing.build_router_status(limit=int(args.get("limit", 200)))

    if name == "lore_story":
        return await _story(args["pattern"])

    if name == "lore_scaffold":
        return await _scaffold(
            args["pattern"],
            args.get("output_dir", "."),
            args.get("dry_run", False),
            args.get("framework", "python"),
        )

    if name == "lore_deploy":
        return await _deploy(
            args["name"],
            args.get("output_dir"),
            args.get("dry_run", True),
        )

    if name == "lore_distill_report":
        return distill.get_distillation_report(limit=int(args.get("limit", 100)))

    if name == "lore_postmortem_report":
        return postmortem.get_postmortem_report(limit=int(args.get("limit", 50)))

    if name == "lore_teach":
        return teaching.compile_lesson(
            args["pattern"],
            format=args.get("format", "claude_md"),
        )

    if name == "lore_fleet_register":
        return fleet.register_agent(
            args["agent_id"],
            args["name"],
            args["format"],
            args["patterns"],
        )

    if name == "lore_fleet_list":
        agents = fleet.list_agents()
        return {"agents": agents, "count": len(agents)}

    if name == "lore_fleet_brief":
        changed = args.get("patterns")
        brief = teaching.compile_fleet_brief(changed)
        # For each registered agent, filter to their subscribed patterns
        agents = fleet.list_agents()
        agent_briefs = []
        for agent in agents:
            agent_patterns = agent.get("patterns", [])
            agent_format = agent.get("format", "claude_md")
            agent_lessons = []
            for lesson in brief["lessons"]:
                pid = lesson["pattern"]
                if "*" in agent_patterns or pid in agent_patterns:
                    # Re-compile in agent's preferred format if different
                    if lesson["format"] != agent_format:
                        recompiled = teaching.compile_lesson(pid, format=agent_format)
                        if "error" not in recompiled:
                            agent_lessons.append(recompiled)
                    else:
                        agent_lessons.append(lesson)
            agent_briefs.append({
                "agent_id": agent.get("id"),
                "agent_name": agent.get("name"),
                "format": agent_format,
                "lessons": agent_lessons,
                "lesson_count": len(agent_lessons),
            })
        return {
            "fleet_size": len(agents),
            "total_patterns": len(brief["lessons"]),
            "summary": brief["summary"],
            "agent_briefs": agent_briefs,
        }

    if name == "lore_teachable":
        patterns = teaching.list_teachable_patterns()
        return {"patterns": patterns, "count": len(patterns)}

    return {"error": f"Unknown tool: {name}"}


async def _ask_oracle(question: str) -> str:
    """Ask NotebookLM via dwiki ask command."""
    if not NOTEBOOK_ID:
        return (
            "lore_ask requires a NotebookLM notebook. "
            "Set LORE_NOTEBOOK_ID env var to your notebook ID, then restart. "
            "See: https://github.com/Miles0sage/lore#setup for instructions."
        )
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
    raw_dir = get_raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{date}-{slug}.md"

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
    log_path = get_evolve_log_path()
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


def _morning_brief() -> dict:
    report = evolution.build_evolution_report()
    brief_dict, brief_text = briefing.build_and_format_morning_brief(
        evolution_report=report,
        proposal_summary=report.get("proposal_summary"),
    )
    routing.log_router_event(
        task_type="morning_brief",
        model="gpt-4.1",
        status="ok",
        description="Generated morning operator brief",
        accepted=True,
    )
    return {"brief": brief_dict, "text": brief_text}


def _weekly_report() -> dict:
    report = maintenance.build_weekly_report()
    routing.log_router_event(
        task_type="weekly_report",
        model="gpt-4.1",
        status="ok",
        description="Generated weekly canon maintenance report",
        accepted=True,
    )
    return {
        "report": report,
        "text": maintenance.format_weekly_report(report),
    }


async def _notebook_sync(hours: float, dry_run: bool) -> dict:
    import time

    start = time.monotonic()
    proposal_queue = proposals.list_proposals(limit=200)
    approved_articles = [
        proposal
        for proposal in proposal_queue
        if proposal.get("status") == "published"
    ]
    sync_pack = notebook.build_notebooklm_sync_pack(
        proposal_queue=proposal_queue,
        approved_articles=approved_articles,
        report=evolution.build_evolution_report(),
    )

    if dry_run:
        routing.log_router_event(
            task_type="notebook_sync",
            model="gpt-5.4",
            status="ok",
            description="Built NotebookLM sync pack in dry-run mode",
            accepted=True,
        )
        return {
            "dry_run": True,
            "notebook_id": NOTEBOOK_ID or None,
            "sync_pack": sync_pack,
        }

    if not NOTEBOOK_ID:
        routing.log_router_event(
            task_type="notebook_sync",
            model="gpt-5.4",
            status="error",
            description="Notebook sync requested without notebook id",
            error="missing_notebook_id",
        )
        return {
            "error": "lore_notebook_sync requires LORE_NOTEBOOK_ID to be set",
            "sync_pack": sync_pack,
        }

    script_path = get_workspace_root() / "scripts" / "notebooklm_push.py"
    if not script_path.exists():
        routing.log_router_event(
            task_type="notebook_sync",
            model="gpt-5.4",
            status="error",
            description="Notebook sync requested without push script",
            error=f"missing_script:{script_path}",
        )
        return {
            "error": f"NotebookLM push script not found: {script_path}",
            "sync_pack": sync_pack,
        }

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script_path),
        "--notebook-id",
        NOTEBOOK_ID,
        "--wiki-dir",
        str(get_wiki_dir()),
        "--hours",
        str(hours),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(get_workspace_root()),
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
    output = stdout.decode().strip()
    error_output = stderr.decode().strip()
    routing.log_router_event(
        task_type="notebook_sync",
        model="gpt-5.4",
        status="ok" if proc.returncode == 0 else "error",
        description=f"Notebook sync run for last {hours} hours",
        accepted=proc.returncode == 0,
        latency_s=time.monotonic() - start,
        error=error_output,
    )

    return {
        "dry_run": False,
        "notebook_id": NOTEBOOK_ID,
        "returncode": proc.returncode,
        "stdout": output,
        "stderr": error_output,
        "sync_pack": sync_pack,
    }


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


async def _scaffold(pattern: str, output_dir: str, dry_run: bool, framework: str = "python") -> dict:
    """Generate pattern scaffold and optionally write to disk."""
    from . import scaffold as scaffold_mod
    from pathlib import Path

    template = scaffold_mod.get_template(pattern, framework=framework)
    if not template:
        return {
            "error": f"No scaffold for pattern: {pattern}",
            "available": scaffold_mod.list_patterns(),
        }

    # Determine if we used a framework variant or fell back to python
    used_framework = framework
    if framework != "python":
        key = f"{pattern}_{framework}"
        if key not in scaffold_mod.FRAMEWORK_TEMPLATES:
            used_framework = "python"  # fell back

    arch = archetypes.get_archetype(pattern.replace("_", "-"))
    character = arch["name"] if arch else pattern

    file_name = f"{pattern}.py" if used_framework == "python" else f"{pattern}_{used_framework}.py"
    file_path = None
    written = False
    if not dry_run:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        file_path = str(out / file_name)
        Path(file_path).write_text(template)
        written = True

    return {
        "pattern": pattern,
        "character": character,
        "framework": used_framework,
        "file": file_path,
        "written": written,
        "preview": template[:300] + "...",
        "lines": template.count("\n"),
    }


async def _deploy(name: str, output_dir: str | None, dry_run: bool) -> dict:
    """Generate deployment template and optionally write to disk."""
    from . import scaffold as scaffold_mod
    from pathlib import Path

    template = scaffold_mod.get_deploy_template(name)
    if not template:
        return {
            "error": f"No deploy template for: {name}",
            "available": scaffold_mod.list_deploy_templates(),
        }

    ext_map = {
        "docker_compose": "docker-compose.yml",
        "kubernetes": "k8s-manifests.yml",
        "cloudflare_worker": "worker.js",
        "dockerfile": "Dockerfile",
    }
    filename = ext_map.get(name, f"{name}.txt")
    file_path = None
    written = False

    if not dry_run and output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        file_path = str(out / filename)
        Path(file_path).write_text(template)
        written = True

    return {
        "name": name,
        "file": file_path,
        "written": written,
        "content": template,
        "lines": template.count("\n"),
    }


def _batch_review(min_priority: float, reviewer: str, dry_run: bool) -> dict:
    queue = proposals.list_proposals(limit=100)
    candidates = [
        p for p in queue
        if p["publish_recommendation"] in {"review_now"}
        and float(p["priority_score"]) >= min_priority
        and p["status"] in {"proposed", "in_review"}
    ]
    if not candidates:
        return {"approved": [], "published": [], "failed": [], "message": "No review_now proposals found"}

    if dry_run:
        return {
            "dry_run": True,
            "would_process": [{"id": p["id"], "title": p["title"], "priority": p["priority_score"]} for p in candidates],
        }

    approved, published, failed = [], [], []
    for p in candidates:
        pid = p["id"]
        try:
            proposals.review_proposal(pid, "approved", reviewer=reviewer, notes="batch auto-approved")
            approved.append(pid)
        except Exception as e:
            failed.append({"id": pid, "error": f"approve: {e}"})
            continue
        try:
            result = publisher.publish_proposal(pid, reviewer=reviewer)
            published.append(result["article_id"])
            routing.log_router_event(
                task_type="publish",
                model="gpt-5.4",
                status="ok",
                description=f"batch published: {result['article_id']}",
                accepted=True,
            )
        except Exception as e:
            failed.append({"id": pid, "error": f"publish: {e}"})

    # Generate sync brief + follow-up questions for NotebookLM
    sync_pack = {}
    if published:
        try:
            published_proposals = [p for p in proposals.list_proposals(limit=200) if p.get("status") == "published"]
            sync_pack = notebook.build_notebooklm_sync_pack(
                proposal_queue=proposals.list_proposals(limit=200),
                approved_articles=published_proposals,
            )
        except Exception:
            pass

    return {
        "approved_count": len(approved),
        "published_count": len(published),
        "failed_count": len(failed),
        "approved": approved,
        "published": published,
        "failed": failed,
        "sync_brief": sync_pack.get("summary", ""),
        "followup_questions": sync_pack.get("followup_questions", []),
    }


# ── Public/private mode gate ──────────────────────────────────────────────────
# Set LORE_MODE=public to expose only the clean OSS tool set.
# Private tools (proposals, routing, dispatch, briefing, sync) are hidden.
_PRIVATE_TOOLS = {
    "lore_proposal_create", "lore_proposal_list", "lore_proposal_review",
    "lore_morning_brief", "lore_publish", "lore_notebook_sync",
    "lore_weekly_report", "lore_pack_generate", "lore_evolution_report",
    "lore_route", "lore_router_status", "lore_dispatch", "lore_circuit_status",
    "lore_batch_review", "lore_eval_report", "lore_router_learn",
    "lore_teach", "lore_fleet_register", "lore_fleet_list",
    "lore_fleet_brief", "lore_teachable",
    "lore_distill_report", "lore_postmortem_report",
}

_LORE_MODE = os.environ.get("LORE_MODE", "private").lower()


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


async def _main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
