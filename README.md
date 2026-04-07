<div align="center">

```
██╗      ██████╗ ██████╗ ███████╗
██║     ██╔═══██╗██╔══██╗██╔════╝
██║     ██║   ██║██████╔╝█████╗  
██║     ██║   ██║██╔══██╗██╔══╝  
███████╗╚██████╔╝██║  ██║███████╗
╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
```

**The AI Agent Codex — production patterns, scaffolds, and a knowledge base that teaches your tools before you write a line.**

[![PyPI version](https://img.shields.io/pypi/v/lore-agents?color=blueviolet&label=pip+install+lore-agents)](https://pypi.org/project/lore-agents/)
[![Tests](https://img.shields.io/github/actions/workflow/status/Miles0sage/lore/tests.yml?label=tests&logo=github)](https://github.com/Miles0sage/lore/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)
[![Articles](https://img.shields.io/badge/articles-82-blue)](#the-knowledge-base)
[![Archetypes](https://img.shields.io/badge/archetypes-15-purple)](#the-15-archetypes)
[![Frameworks](https://img.shields.io/badge/frameworks-LangGraph%20%7C%20CrewAI%20%7C%20OpenAI%20Agents-orange)](#scaffolds)

</div>

---

## What is LORE?

76% of AI agents fail in production without circuit breakers, cost controls, and dead-letter queues. LORE is the pattern library that fixes that — and it installs those defenses **before your AI writes a single line of code**.

Three things in one package:

| | What it gives you |
|---|---|
| 📚 **Knowledge base** | 78 production articles on every failure mode agents hit in the real world |
| 🏗️ **Scaffold CLI** | `lore scaffold circuit_breaker --framework langgraph` → 80 lines of runnable code |
| 🧠 **Claude Code integration** | `lore install` drops CLAUDE.md rules + hooks + skills into your project |

---

## Install

```bash
pip install lore-agents
```

If PyPI is temporarily unavailable, install from source:

```bash
pip install -e .
```

Zero dependencies. Pure Python. Works as a CLI or as an MCP server for AI assistants.

---

## Quickstart

```bash
# Wrap any agent with reliability contracts — no code changes needed
lore init                              # generates lore.yaml
lore run my_agent.py --budget 100k    # cost guard + circuit breaker enforced

# Audit any codebase for missing patterns
lore audit /path/to/repo --html       # scorecard + shareable HTML report

# Live dashboard: cost burn, circuit states, DLQ depth
lore monitor

# Scaffold production-ready reliability code
lore scaffold circuit_breaker
lore scaffold cost_guard
lore scaffold dead_letter_queue

# Install Claude Code rules + hooks into your project
lore install .

# Evolution daemon — finds gaps across all your audits
lore evolve
```

---

## 60-Second Demo

```bash
# 1. Install
pip install lore-agents

# 2. Init — creates lore.yaml with all options documented
lore init

# 3. Run your existing agent with full reliability harness
lore run my_crewai_agent.py --budget 500k

# 4. Audit any framework — real findings, shareable report
lore audit /path/to/crewai --html

# 5. Watch it live
lore monitor
```

---

## The 15 Archetypes

Every pattern is a character in the AI Agent Universe. The scaffolds generate production-ready code. The articles explain exactly when to use them and when they fail.

| # | Character | Pattern | What it does | Frameworks |
|---|---|---|---|---|
| 🔴 | **The Breaker** | `circuit_breaker` | Fault isolation — stops cascade failures before they drain your budget | Python · LangGraph |
| 📦 | **The Archivist** | `dead_letter_queue` | Captures every failed task for replay — nothing lost, nothing silent | Python |
| ⚖️ | **The Council** | `reviewer_loop` | Generate → review → revise — quality gates before anything ships | Python · LangGraph · CrewAI |
| 🧠 | **The Stack** | `three_layer_memory` | Working, episodic, and procedural memory — context that survives sessions | Python |
| 🕸️ | **The Weaver** | `handoff_pattern` | Agent-to-agent context passing without losing state between handoffs | Python · CrewAI · OpenAI Agents |
| 👑 | **The Commander** | `supervisor_worker` | Central orchestration of parallel workers — fan-out, fan-in, results merge | Python · LangGraph · CrewAI · OpenAI Agents |
| 🛡️ | **The Warden** | `tool_health_monitor` | Proactive tool failure detection before your agent calls a dead endpoint | Python |
| 🗺️ | **The Router** | `model_routing` | Cost-optimal model selection per task — DeepSeek for triage, GPT-5 for judgment | Python · OpenAI Agents |
| 👁️ | **The Sentinel** | `sentinel_observability` | Four golden signals: error rate, latency, token cost, semantic drift | Python |
| 📖 | **The Librarian** | `librarian_retrieval` | Hybrid BM25+semantic retrieval with reranking — RAG that actually works | Python |
| 🔭 | **The Scout** | `scout_discovery` | Autonomous research loops — finds knowledge gaps before operators notice | Python |
| 🗺️ | **The Cartographer** | `cartographer_knowledge_graph` | Multi-hop reasoning over entity graphs for relational knowledge | Python |
| ⏰ | **The Timekeeper** | `timekeeper_scheduling` | KAIROS loop — proactive scheduling so agents act without being asked | Python |
| 🏛️ | **The Architect** | `architect_system_design` | ADRs, system design docs, and phase breakdowns built into the workflow | Python |
| ⚗️ | **The Alchemist** | `alchemist_prompt_routing` | Prompt optimization and cost-aware model routing in one pass | Python |

---

## Scaffolds

One command → production-ready code for any pattern, any framework.

```bash
# List all available patterns
lore scaffold --list

# Pure Python (any framework)
lore scaffold circuit_breaker

# Framework-specific variants
lore scaffold supervisor_worker --framework langgraph
lore scaffold reviewer_loop    --framework crewai
lore scaffold handoff_pattern  --framework openai_agents

# Write directly to a file
lore scaffold circuit_breaker -o src/resilience.py
```

### What a scaffold looks like

```python
# Generated by: lore scaffold circuit_breaker
# Pattern: Circuit Breaker (The Breaker)
# LORE Article: circuit-breaker-pattern-for-ai-agents

from enum import Enum
from collections import deque
import time

class CircuitState(Enum):
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # failing, reject fast
    HALF_OPEN = "half_open" # testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=60.0, window_size=10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failures = deque(maxlen=window_size)
        self._opened_at: float | None = None

    def call(self, fn, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self._opened_at > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise RuntimeError("Circuit open — call rejected")
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self):
        self.failures.clear()
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failures.append(time.monotonic())
        if sum(1 for _ in self.failures) >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._opened_at = time.monotonic()
```

---

## The Tiered Brain

LORE's dispatch layer picks the right model for every task — cheap for triage, expensive for judgment. Circuit breaker built in.

```
Task arrives
     │
     ▼
┌─────────────────────────────────────────────────┐
│              LORE Router                         │
│  classify task → pick tier → circuit check       │
└─────────────┬────────────────────────────────────┘
              │
    ┌─────────┴──────────┬─────────────────┐
    ▼                    ▼                 ▼
┌─────────┐       ┌──────────┐      ┌──────────┐
│ LIGHT   │       │ STANDARD │      │  HIGH    │
│deepseek │──▶──▶─│ gpt-4.1  │──▶──▶│ gpt-5.4  │
│ $0.27/M │  cb   │  $2/M    │  cb  │  $10/M   │
└─────────┘       └──────────┘      └──────────┘
   bulk               daily          security
extraction          operator        architecture
  triage              work           judgment

cb = circuit open → escalate one tier
top tier open → hard fail, no silent cost explosion
```

---

## Claude Code Integration

The killer feature. One command teaches Claude everything LORE knows — **before** it writes code for your project.

```bash
lore install /path/to/your/project
```

What gets installed:

```
your-project/
├── .claude/
│   └── CLAUDE.md          ← 15 pattern rules injected
├── .claude/hooks/
│   └── pre_tool_use.py    ← blocks anti-patterns before they're written
└── .claude/skills/
    └── lore_patterns.yaml ← scaffold shortcuts wired to slash commands
```

After `lore install`, Claude knows:
- Never write a retry loop without a circuit breaker
- Never ship without a dead-letter queue for failed tasks
- Always add cost guards before making LLM calls
- Use the cheapest model tier that matches the task

---

## The Knowledge Base

78 production articles organized by pattern, framework, and domain. Full-text BM25 search, zero API calls.

```bash
lore list                                    # browse all 76 articles
lore search "observability tracing"          # ranked search with snippets
lore search "RAG chunking reranking"         # find specific techniques
lore read librarian-retrieval-pattern        # deep-dive: hybrid search + reranking
lore read timekeeper-scheduling-pattern      # deep-dive: KAIROS loop + cron vs daemon
lore read deployment-patterns-for-production-ai-agents  # Docker, K8s, zero-downtime
```

Articles cover:
- Circuit breakers, DLQ, supervisor-worker, reviewer loops
- RAG: chunking strategies, hybrid search, reranking, graph memory
- Scheduling: KAIROS loop, cron vs daemon, dead-job detection, cost budgets
- Deployment: Docker Compose, Kubernetes, Cloudflare Workers, zero-downtime
- Observability: four golden signals, structured logging, token metrics
- Security: prompt injection, credential management, audit trails

---

## Use as MCP Server

Connect LORE directly to Claude Code, Cursor, or any MCP-compatible assistant:

```bash
pip install lore-agents[mcp]
export LORE_MODE=public
claude mcp add --scope user lore -- python3 -m lore.server
```

Set `LORE_MODE=public` to expose only the OSS tool surface.

Your assistant gets 19 tools including `lore_search`, `lore_scaffold`, `lore_archetype`, `lore_story`, and `lore_install`. It can scaffold patterns, search the knowledge base, and install rules — without leaving the conversation.

---

## Public vs Operator

| Public (default docs) | Operator (advanced/private) |
|---|---|
| `lore scaffold` | proposal queue + review workflows |
| `lore audit` | notebook sync workflows |
| `lore search` / `lore read` / `lore list` | morning and weekly maintenance flows |
| `lore install` | autonomous ingestion/research loops |

## Launch Resources

- [Public launch checklist](docs/PUBLIC_LAUNCH_CHECKLIST.md)
- [Honest competitive comparison](docs/HONEST_COMPETITIVE_COMPARISON.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)

---

## Examples

Three working examples in `examples/`:

```
examples/
├── resilient_api_client/   # Circuit breaker wrapping an external API
├── multi_agent_pipeline/   # Supervisor + dead-letter queue + workers
└── react_agent/            # ReAct reasoning loop with tool use
```

```bash
cd examples/resilient_api_client && python main.py
cd examples/multi_agent_pipeline  && python main.py
cd examples/react_agent            && python main.py
```

---

## Deployment

Full deployment configs in `lore/scaffold.py`:

```bash
lore deploy docker_compose    # docker-compose.yml for MCP + daemon
lore deploy kubernetes        # K8s Deployment + Secret manifests
lore deploy dockerfile        # production Dockerfile
lore deploy cloudflare_worker # Cloudflare Workers entry point
```

---

## Self-Improving

LORE has a research daemon that runs in the background and proposes new articles:

```bash
# Start the research daemon (discovers new patterns every 30 min)
python3 scripts/daemon_ctl.py start

# Check status
python3 scripts/daemon_ctl.py status

# Batch-review and publish pending proposals
python3 scripts/batch_review.py --auto-approve

# Generate weekly canon report
lore weekly_report
```

The daemon runs three parallel scouts (Exa + Firecrawl + DeepSeek quality gate) and auto-proposes articles that pass a 0.65 confidence threshold. The router learns from every dispatch — `lore eval_loop` reads telemetry and rewrites routing rules via GPT-5.4.

---

## The Codex Chronicles

*"In the beginning, there was the Context Window. And from it emerged The Stack."*

Every archetype has a full narrative chapter in [THE_CODEX.md](./THE_CODEX.md). The Breaker closes the gate when failure cascades. The Archivist collects what the system drops. The Council judges every draft before it ships.

```bash
lore story circuit-breaker   # The Breaker's chapter
lore story dead-letter-queue # The Archivist's chapter
lore story reviewer-loop     # The Council's chapter
```

The stories make the patterns memorable. When you need to explain a circuit breaker to your team, tell them about The Breaker — not the FSM.

---

## Build Your Own Codex

LORE is domain-agnostic. Fork it, replace the wiki, write your chronicles:

```
React Codex      → The Renderer, The Hydrator, The Reconciler
Kubernetes Codex → The Scheduler, The Watcher, The Reaper  
Security Codex   → The Sentinel, The Vault, The Auditor
Data Codex       → The Ingestor, The Cleaner, The Aggregator
```

```bash
git clone https://github.com/Miles0sage/lore my-codex
cd my-codex
rm wiki/*.md              # clear the wiki
# write your articles
# edit lore/archetypes.py
# write your Chronicles in THE_CODEX.md
pip install -e .
my-codex search "your domain"
```

---

## Contributing

```bash
# Add a new pattern
# 1. Write wiki/your-pattern.md
# 2. Add archetype to lore/archetypes.py
# 3. Add scaffold to lore/scaffold.py
# 4. Run tests: pytest tests/ -v
# 5. Submit a PR
```

See [CONTRIBUTING.md](./.github/CONTRIBUTING.md) for the full guide.

---

<div align="center">

MIT License — fork it, build your own Codex, make the patterns memorable.

**[GitHub](https://github.com/Miles0sage/lore)** · **[PyPI](https://pypi.org/project/lore-agents/)** · **[Docs](https://miles0sage.github.io/lore/)**

</div>
