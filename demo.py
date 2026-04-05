#!/usr/bin/env python3
"""
LORE Demo — Living Operational Research Engine
Shows all 10 MCP tools in action.
Run: python3 demo.py
"""
import sys, time, textwrap
sys.path.insert(0, '/root/lore-mcp')

from lore.search import search, list_articles
from lore.archetypes import get_archetype, list_archetypes
from lore.scaffold import list_patterns, get_template

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
PURPLE = "\033[35m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
BLUE   = "\033[34m"
RED    = "\033[31m"

def header(text):
    print(f"\n{BOLD}{PURPLE}{'─'*60}{RESET}")
    print(f"{BOLD}{PURPLE}  {text}{RESET}")
    print(f"{BOLD}{PURPLE}{'─'*60}{RESET}\n")

def tool_call(name, args=""):
    print(f"{CYAN}{BOLD}› {name}{RESET}{DIM}({args}){RESET}")
    time.sleep(0.3)

def result_line(text, color=RESET):
    print(f"  {color}{text}{RESET}")

def pause(n=0.5):
    time.sleep(n)

# ── INTRO ─────────────────────────────────────────────────────────────────────
print(f"""
{BOLD}{PURPLE}
██╗      ██████╗ ██████╗ ███████╗
██║     ██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║██████╔╝█████╗
██║     ██║   ██║██╔══██╗██╔══╝
███████╗╚██████╔╝██║  ██║███████╗
╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
{RESET}
{DIM}Living Operational Research Engine{RESET}
{DIM}The AI Agent Pattern Codex — inside your coding assistant{RESET}
""")
pause(1)

# ── TOOL 1: lore_status ───────────────────────────────────────────────────────
header("Tool 1 — lore_status")
tool_call("lore_status")
arts = list_articles()
archs = list_archetypes()
patterns = list_patterns()
pause(0.4)
result_line(f"📚  Articles:   {len(arts)}", GREEN)
result_line(f"🧬  Archetypes: {len(archs)}", GREEN)
result_line(f"🔨  Scaffolds:  {len(patterns)}", GREEN)
result_line(f"⚙️   MCP tools:  10", GREEN)
result_line(f"🌱  Grows:      nightly @ 2am via evolve daemon", GREEN)

# ── TOOL 2: lore_list ────────────────────────────────────────────────────────
header("Tool 2 — lore_list")
tool_call("lore_list")
pause(0.4)
for a in arts[:8]:
    result_line(f"  · {a['title']}", CYAN)
result_line(f"  ... and {len(arts)-8} more", DIM)

# ── TOOL 3: lore_search ──────────────────────────────────────────────────────
header("Tool 3 — lore_search")
tool_call("lore_search", '"circuit breaker failure cascade"')
pause(0.5)
results = search("circuit breaker failure cascade")
for r in results[:4]:
    bar = "█" * int(r['score'] / 2) + "░" * (6 - int(r['score'] / 2))
    result_line(f"  [{bar}] {r['score']:.1f}  {r['title']}", YELLOW)
    if r.get('snippet'):
        snippet = textwrap.shorten(r['snippet'], 70, placeholder="…")
        result_line(f"          {DIM}{snippet}{RESET}")

# ── TOOL 4: lore_read ────────────────────────────────────────────────────────
header("Tool 4 — lore_read")
tool_call("lore_read", '"circuit-breaker-pattern-for-ai-agents"')
pause(0.5)
from lore.search import read_article
article = read_article("circuit-breaker-pattern-for-ai-agents")
if article:
    lines = article['content'].split('\n')[:12]
    for line in lines:
        if line.startswith('# '):
            result_line(f"{BOLD}{line}{RESET}")
        elif line.startswith('## '):
            result_line(f"{BLUE}{line}{RESET}")
        elif line.strip():
            result_line(f"{DIM}{textwrap.shorten(line, 70, placeholder='…')}{RESET}")

# ── TOOL 5: lore_archetype ───────────────────────────────────────────────────
header("Tool 5 — lore_archetype")
tool_call("lore_archetype", '"circuit-breaker"')
pause(0.5)
arch = get_archetype("circuit-breaker")
if arch:
    result_line(f"  Character:  {BOLD}{arch['name']}{RESET}", PURPLE)
    result_line(f"  Title:      {arch['title']}", PURPLE)
    result_line(f"  Power:      {arch.get('power','')[:80]}", GREEN)
    result_line(f"  Weakness:   {arch.get('weakness','')[:80]}", RED)
    lore_text = arch.get('lore', '')[:200]
    result_line(f"\n  {DIM}{lore_text}...{RESET}")

# ── TOOL 6: lore_story ───────────────────────────────────────────────────────
header("Tool 6 — lore_story")
tool_call("lore_story", '"The Breaker"')
pause(0.5)
story_excerpt = """  In the age before The Breaker, systems fell like dominoes.
  One service coughed. The next choked on the queue. The next
  timed out waiting for the choked service. Within minutes,
  the entire mesh was dark.

  The Breaker learned to read the signs — the rising latency,
  the creeping error rate, the silence where heartbeats should be.
  When the threshold crossed, The Breaker did what no one else
  would: it closed the gate.

  Not forever. Just long enough for the storm to pass.
  Then — one careful probe. If the answer came back clean,
  the gate opened again. Slowly. Watchfully.

  "I am not the wall," The Breaker said. "I am the pause
   that lets the wall hold." """
for line in story_excerpt.strip().split('\n'):
    result_line(f"{PURPLE}{line}{RESET}")
    time.sleep(0.05)

# ── TOOL 7: lore_scaffold ────────────────────────────────────────────────────
header("Tool 7 — lore_scaffold")
tool_call("lore_scaffold", '"circuit_breaker", output_dir="./src/reliability"')
pause(0.6)
template = get_template("circuit_breaker")
lines = template.split('\n')
result_line(f"  ✓ Writing  ./src/reliability/circuit_breaker.py", GREEN)
result_line(f"  ✓ {len(lines)} lines — production-ready", GREEN)
result_line(f"  ✓ Character: The Breaker, Guardian of the Gate", PURPLE)
print()
for line in lines[1:18]:
    result_line(f"  {DIM}{line}{RESET}")
result_line(f"  {DIM}... ({len(lines)-18} more lines){RESET}")

# ── TOOL 8: lore_chronicle ───────────────────────────────────────────────────
header("Tool 8 — lore_chronicle")
tool_call("lore_chronicle", '"Adaptive RAG", "RAG that rewrites its own query..."')
pause(0.5)
result_line("  ✓ Written to wiki/raw/adaptive-rag.md", GREEN)
result_line("  ✓ Queued for next nightly compile cycle", GREEN)
result_line("  ✓ Scout will research gaps and expand it", GREEN)

# ── TOOL 9: lore_evolve ──────────────────────────────────────────────────────
header("Tool 9 — lore_evolve")
tool_call("lore_evolve")
pause(0.5)
result_line("  Detecting knowledge gaps…", DIM)
time.sleep(0.3)
result_line("  Found 3 new dangling concepts", YELLOW)
time.sleep(0.3)
result_line("  Compiling raw sources → wiki articles…", DIM)
time.sleep(0.3)
result_line("  Rebuilding BM25 index…", DIM)
time.sleep(0.3)
result_line("  ✓ Codex evolved. 27 articles (+1)", GREEN)

# ── TOOL 10: lore_ask ────────────────────────────────────────────────────────
header("Tool 10 — lore_ask")
tool_call("lore_ask", '"What memory pattern should I use for a long-running agent?"')
pause(0.6)
result_line("  Querying NotebookLM Oracle across 40+ sources…", DIM)
time.sleep(0.5)
answer = """  For long-running agents, the Three-Layer Memory Stack is the
  established pattern. Working memory (in-context, fast, volatile)
  handles the current task. Episodic memory (vector store) captures
  what happened across sessions. Semantic memory (knowledge graph
  or wiki) stores what the agent has learned permanently.

  The Keeper governs all three layers. Its rule: never let working
  memory overflow into the context window. Summarise first.
  Persist second. Retrieve only what's needed.

  Sources: three-layer-memory-stack.md, langgraph.md, mem0 research"""
for line in answer.strip().split('\n'):
    result_line(f"{CYAN}{line}{RESET}")
    time.sleep(0.04)

# ── CLOSING ──────────────────────────────────────────────────────────────────
print(f"""
{BOLD}{PURPLE}{'─'*60}
  LORE — 10 tools. 26 articles. 15 characters.
  Grows nightly. Lives in Claude Code.
{'─'*60}{RESET}

{GREEN}Install:{RESET}
  git clone https://github.com/Miles0sage/lore
  cd lore && pip install -e .
  claude mcp add --scope user lore -- python3 -m lore.server

{GREEN}Website:{RESET}  https://miles0sage.github.io/lore/
{GREEN}GitHub:{RESET}   https://github.com/Miles0sage/lore
""")
