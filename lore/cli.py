"""
LORE CLI — The AI Agent Codex from the command line.

Zero dependencies. Zero API keys. Zero setup.

Usage:
    lore scaffold circuit_breaker
    lore scaffold circuit_breaker --framework langgraph
    lore scaffold --list
    lore search "circuit breaker retry"
    lore read circuit-breaker-pattern
    lore list
    lore archetype circuit-breaker
    lore story circuit-breaker
"""

import argparse
import json
import os
import sys
from pathlib import Path


def _deploy_cmd(args: argparse.Namespace) -> int:
    from .scaffold import DEPLOY_TEMPLATES, get_deploy_template, list_deploy_templates

    if args.list:
        templates = list_deploy_templates()
        print(f"{'Name':<25} {'Lines':<8} Preview")
        print("-" * 70)
        for t in templates:
            print(f"{t['name']:<25} {t['lines']:<8} {t['preview']}")
        print(f"\n{len(templates)} deploy templates available.")
        return 0

    if not args.name:
        print("Error: template name required. Use --list to see available templates.", file=sys.stderr)
        return 1

    template = get_deploy_template(args.name)
    if template is None:
        print(f"Error: no deploy template found for '{args.name}'", file=sys.stderr)
        available = ", ".join(DEPLOY_TEMPLATES.keys())
        print(f"Available: {available}", file=sys.stderr)
        return 1

    if args.output:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        # Choose appropriate filename based on template type
        ext_map = {
            "docker_compose": "docker-compose.yml",
            "kubernetes": "k8s-manifests.yml",
            "cloudflare_worker": "worker.js",
            "dockerfile": "Dockerfile",
        }
        filename = ext_map.get(args.name, f"{args.name}.txt")
        out_path = out_dir / filename
        out_path.write_text(template)
        print(f"Wrote {out_path}")
    else:
        print(template)

    return 0


def _scaffold_cmd(args: argparse.Namespace) -> int:
    from .scaffold import TEMPLATES, FRAMEWORK_TEMPLATES, get_template, list_patterns

    if args.list:
        patterns = list_patterns()
        print(f"{'Pattern':<35} {'Archetype':<20} {'Frameworks'}")
        print("-" * 80)
        for p in patterns:
            fws = ", ".join(p["frameworks"])
            print(f"{p['pattern']:<35} {p['archetype']:<20} {fws}")
        print(f"\n{len(patterns)} patterns available.")
        return 0

    if not args.pattern:
        print("Error: pattern name required. Use --list to see available patterns.", file=sys.stderr)
        return 1

    template = get_template(args.pattern, framework=args.framework or "python")
    if template is None:
        print(f"Error: no template found for pattern '{args.pattern}'", file=sys.stderr)
        available = ", ".join(TEMPLATES.keys())
        print(f"Available patterns: {available}", file=sys.stderr)
        return 1

    if args.output:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = f"_{args.framework}" if args.framework and args.framework != "python" else ""
        filename = f"{args.pattern}{suffix}.py"
        out_path = out_dir / filename
        out_path.write_text(template)
        print(f"Wrote {out_path}")
    else:
        print(template)

    return 0


def _search_cmd(args: argparse.Namespace) -> int:
    from .search import search

    query = " ".join(args.query)
    if not query:
        print("Error: search query required.", file=sys.stderr)
        return 1

    results = search(query, limit=args.limit)
    if not results:
        print(f"No results for '{query}'.")
        return 0

    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['title']} (id: {r['id']}, score: {r['score']})")
        print(f"   {r['snippet']}")

    print(f"\n{len(results)} result(s). Use 'lore read <id>' to read full article.")
    return 0


def _read_cmd(args: argparse.Namespace) -> int:
    from .search import read_article

    result = read_article(args.article_id)
    if result is None:
        print(f"Error: article '{args.article_id}' not found.", file=sys.stderr)
        return 1

    print(result["content"])
    return 0


def _list_cmd(args: argparse.Namespace) -> int:
    from .search import list_articles

    articles = list_articles()
    if not articles:
        print("No articles found in the Codex.")
        return 0

    print(f"{'ID':<60} Title")
    print("-" * 90)
    for a in articles:
        print(f"{a['id']:<60} {a['title']}")
    print(f"\n{len(articles)} articles in the Codex.")
    return 0


def _archetype_cmd(args: argparse.Namespace) -> int:
    from .archetypes import get_archetype, list_archetypes

    if args.all:
        archs = list_archetypes()
        print(f"{'Pattern ID':<30} {'Name':<20} Title")
        print("-" * 75)
        for a in archs:
            print(f"{a['pattern_id']:<30} {a['name']:<20} {a['title']}")
        print(f"\n{len(archs)} archetypes in the Codex.")
        return 0

    if not args.pattern:
        print("Error: pattern name required. Use --all to list all archetypes.", file=sys.stderr)
        return 1

    arch = get_archetype(args.pattern)
    if arch is None:
        print(f"Error: no archetype found for '{args.pattern}'.", file=sys.stderr)
        return 1

    print(json.dumps(arch, indent=2))
    return 0


def _rules_cmd(args: argparse.Namespace) -> int:
    from .claude_code import generate_claude_md_rules

    patterns = None
    if args.patterns:
        patterns = [p.strip() for p in args.patterns.split(",") if p.strip()]

    rules = generate_claude_md_rules(patterns)
    print(rules)
    return 0


def _install_cmd(args: argparse.Namespace) -> int:
    from .claude_code import install_rules

    output_dir = args.dir or "."
    patterns = None
    if args.patterns:
        patterns = [p.strip() for p in args.patterns.split(",") if p.strip()]

    result = install_rules(output_dir, patterns)
    print(result["summary"])
    print(f"  CLAUDE.md : {result['claude_md']}")
    if result["hooks_written"]:
        for h in result["hooks_written"]:
            print(f"  hook      : {h}")
    if result["skills_written"]:
        for s in result["skills_written"]:
            print(f"  skill     : {s}")
    if result["hooks_skipped"]:
        print(f"  skipped (no hook template): {', '.join(result['hooks_skipped'])}")
    return 0


def _evolve_cmd(args: argparse.Namespace) -> int:
    from .evolve import run_evolution

    result = run_evolution(
        audit_dir=__import__("pathlib").Path(args.audit_dir) if args.audit_dir else None,
    )
    audits = result["audits_analyzed"]
    gaps = result["top_gaps"]
    proposed = result["proposed_patterns"]

    print(f"Audits analyzed: {audits}")
    if gaps:
        print("\nTop gap patterns:")
        for pattern, count in gaps[:10]:
            print(f"  {pattern}: {count}x")
    else:
        print("No recurring gap patterns found.")

    if proposed:
        print(f"\nNew patterns proposed ({len(proposed)}):")
        for stub in proposed:
            print(f"  {stub['pattern']} (flagged {stub['frequency']}x)")
    else:
        print("\nNo new patterns proposed (all recurring gaps already have templates).")

    print(f"\nEvolution report: {result['report_path']}")
    return 0


def _audit_cmd(args: argparse.Namespace) -> int:
    from .audit import run_audit, generate_html_report
    from pathlib import Path

    question = args.question or (
        "Audit this codebase for missing Lore patterns, operational risks, and highest-value fixes."
    )
    result = run_audit(
        args.path or ".",
        question=question,
        model=args.model,
        max_files=args.max_files,
        max_chars=args.max_chars,
    )
    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    report = result["report"]
    print(report.get("summary", "No summary returned."))
    findings = report.get("top_findings", [])
    if findings:
        print("\nTop findings:")
        for finding in findings[:5]:
            print(f"- [{finding.get('severity', 'unknown')}] {finding.get('title', 'Untitled')}")
    actions = result.get("lore_actions", [])
    if actions:
        print("\nSuggested Lore actions:")
        for action in actions:
            print(f"- {action['command']}")
    print(f"\nSaved audit: {result['report_path']}")

    if getattr(args, "html", False):
        html = generate_html_report(result)
        html_path = Path(result["report_path"]).with_suffix(".html")
        html_path.write_text(html, encoding="utf-8")
        print(f"HTML report:  {html_path}")

    return 0


def _story_cmd(args: argparse.Namespace) -> int:
    from .archetypes import get_archetype, ARCHETYPES

    pattern = args.pattern
    arch = get_archetype(pattern)

    if arch is None:
        print(f"Error: no archetype found for '{pattern}'.", file=sys.stderr)
        return 1

    # Resolve pattern_id
    pattern_id = arch.get("pattern_id", pattern.lower().replace(" ", "-"))
    if pattern_id not in ARCHETYPES and pattern in ARCHETYPES:
        pattern_id = pattern

    # Build interactions (same logic as server._story)
    _ARCHETYPE_INTERACTIONS = {
        "circuit-breaker": ["dead-letter-queue", "tool-health-monitoring", "supervisor-worker"],
        "dead-letter-queue": ["circuit-breaker", "reviewer-loop", "supervisor-worker"],
        "reviewer-loop": ["supervisor-worker", "dead-letter-queue", "model-routing"],
        "three-layer-memory": ["model-routing", "reviewer-loop", "handoff-pattern"],
        "handoff-pattern": ["supervisor-worker", "three-layer-memory", "model-routing"],
        "supervisor-worker": ["circuit-breaker", "reviewer-loop", "handoff-pattern", "model-routing"],
        "tool-health-monitoring": ["circuit-breaker", "model-routing", "supervisor-worker"],
        "model-routing": ["tool-health-monitoring", "circuit-breaker", "supervisor-worker"],
    }

    allies = _ARCHETYPE_INTERACTIONS.get(pattern_id, [])
    ally_descriptions = []
    for ally_id in allies:
        ally_arch = get_archetype(ally_id)
        if ally_arch:
            ally_descriptions.append(f"{ally_arch['name']} ({ally_arch['title']})")

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

    print(chapter)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lore",
        description="LORE — The AI Agent Codex. 15 production patterns, scaffolds, and a searchable knowledge base.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # scaffold
    sc = subparsers.add_parser("scaffold", help="Generate production-ready code for an AI agent pattern")
    sc.add_argument("pattern", nargs="?", help="Pattern name (e.g. circuit_breaker, react_loop, reflexion_loop, plan_execute)")
    sc.add_argument("--framework", "-f", help="Framework variant: langgraph, crewai, openai_agents")
    sc.add_argument("--output", "-o", help="Output directory (default: stdout)")
    sc.add_argument("--list", "-l", action="store_true", help="List all available patterns")

    # deploy
    dp = subparsers.add_parser("deploy", help="Generate deployment infrastructure scaffolds")
    dp.add_argument("name", nargs="?", help="Template name (e.g. docker_compose, kubernetes, cloudflare_worker, dockerfile)")
    dp.add_argument("--output", "-o", help="Output directory (default: stdout)")
    dp.add_argument("--list", "-l", action="store_true", help="List all available deploy templates")

    # search
    sr = subparsers.add_parser("search", help="BM25 search over the Codex knowledge base")
    sr.add_argument("query", nargs="+", help="Search query")
    sr.add_argument("--limit", "-n", type=int, default=5, help="Max results (default: 5)")

    # read
    rd = subparsers.add_parser("read", help="Read a full article from the Codex")
    rd.add_argument("article_id", help="Article ID (from search results or list)")

    # list
    subparsers.add_parser("list", help="List all articles in the Codex")

    # archetype
    ar = subparsers.add_parser("archetype", help="Get the character archetype for a pattern")
    ar.add_argument("pattern", nargs="?", help="Pattern ID (e.g. circuit-breaker)")
    ar.add_argument("--all", "-a", action="store_true", help="List all archetypes")

    # story
    st = subparsers.add_parser("story", help="Get the narrative chapter for a pattern")
    st.add_argument("pattern", help="Pattern ID (e.g. circuit-breaker)")

    # rules
    ru = subparsers.add_parser("rules", help="Print CLAUDE.md imperative rules from Lore patterns")
    ru.add_argument("--patterns", "-p", help="Comma-separated pattern IDs (e.g. circuit_breaker,dead_letter_queue). Default: all.")

    # install
    ins = subparsers.add_parser("install", help="Install Lore rules, hooks, and skills into a project directory")
    ins.add_argument("--dir", "-d", default=".", help="Target project directory (default: current directory)")
    ins.add_argument("--patterns", "-p", help="Comma-separated pattern IDs to install. Default: all available.")

    # evolve
    ev = subparsers.add_parser("evolve", help="Analyze audit history and propose new scaffold patterns")
    ev.add_argument("--audit-dir", help="Path to audit JSON directory (default: .lore/audits)")

    # audit
    au = subparsers.add_parser("audit", help="Run a large-context Lore audit over a codebase")
    au.add_argument("path", nargs="?", default=".", help="Project path to audit (default: current directory)")
    au.add_argument("--question", "-q", help="Override the audit question")
    au.add_argument("--model", "-m", default="gemini-2.5-pro", help="Gemini model to use")
    au.add_argument("--max-files", type=int, default=120, help="Max files to include in the audit bundle")
    au.add_argument("--max-chars", type=int, default=400000, help="Max characters to send to the audit backend")
    au.add_argument("--html", action="store_true", help="Also write a shareable HTML scorecard alongside the JSON report")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "scaffold": _scaffold_cmd,
        "deploy": _deploy_cmd,
        "search": _search_cmd,
        "read": _read_cmd,
        "list": _list_cmd,
        "archetype": _archetype_cmd,
        "story": _story_cmd,
        "rules": _rules_cmd,
        "install": _install_cmd,
        "audit": _audit_cmd,
        "evolve": _evolve_cmd,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
