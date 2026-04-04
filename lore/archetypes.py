"""
LORE Archetypes — every pattern in the Codex is a character.

In the AI Agent Universe, patterns aren't just code — they are living entities
that govern the behavior of all intelligent systems. Each archetype has a name,
a role in the universe, and a domain of power.
"""

ARCHETYPES: dict[str, dict] = {
    "circuit-breaker": {
        "name": "The Breaker",
        "title": "Guardian of the Gate",
        "lore": (
            "The Breaker stands at every threshold in the system. When the storms of failure "
            "cascade through the network, The Breaker closes the gate — absorbing the blow so "
            "the rest of the universe survives. Three states define its existence: CLOSED (the "
            "gate is open, all flows freely), OPEN (the gate is sealed, no request passes), and "
            "HALF_OPEN (a single probe is sent into the dark to test if the danger has passed)."
        ),
        "power": "Fault isolation. Cascade prevention.",
        "weakness": "Cannot distinguish transient from permanent failures without help.",
    },
    "dead-letter-queue": {
        "name": "The Archivist",
        "title": "Keeper of Lost Messages",
        "lore": (
            "The Archivist collects what the system drops. Every message that fails beyond "
            "redemption is sealed in an envelope — error type, attempt count, original payload — "
            "and placed in the Archive. Nothing is destroyed. Everything waits to be understood. "
            "The Archivist does not judge whether a message can be replayed. That is for the "
            "DLQ Consumer to decide."
        ),
        "power": "Failure preservation. Replay-ready error isolation.",
        "weakness": "Archive grows without bound if no consumer watches.",
    },
    "reviewer-loop": {
        "name": "The Council",
        "title": "Judges of All Output",
        "lore": (
            "The Council convenes after every draft is written. One agent creates; the Council "
            "evaluates. Score below the threshold? The Council returns the draft with critique "
            "and the creator tries again. After N failed iterations, the Council escalates to "
            "a human — the only authority above the Council itself. The Council may use a "
            "different model than the creator, for different minds catch different errors."
        ),
        "power": "Output quality enforcement. Hallucination reduction.",
        "weakness": "2-3x token cost. Must cap iterations or loops forever.",
    },
    "three-layer-memory": {
        "name": "The Stack",
        "title": "Consciousness of the Agent",
        "lore": (
            "The Stack is how an agent remembers. Three layers, three timescales. The Working "
            "Memory holds what is happening now — ephemeral, gone when the session ends. The "
            "Episodic Memory holds what has happened before — retrieved by semantic search, "
            "injected before each decision. The Procedural Memory holds what has been learned "
            "permanently — loaded from CLAUDE.md, skills registries, behavioral patterns that "
            "survived verification. Without The Stack, every session is the agent's first day alive."
        ),
        "power": "Cross-session continuity. Context rot prevention.",
        "weakness": "Retrieval latency at Layer 2. Stale procedural memory at Layer 3.",
    },
    "handoff-pattern": {
        "name": "The Weaver",
        "title": "Passer of the Thread",
        "lore": (
            "The Weaver connects agents without hierarchy. When one agent's work ends, The Weaver "
            "packages everything — state, history, instructions — into a Context Object and passes "
            "the thread to the next specialist. No supervisor required. The Weaver trusts each "
            "agent to acknowledge the handoff before proceeding. Clean stage boundaries. "
            "Sequential pipelines. The art of letting go."
        ),
        "power": "Low overhead coordination. Natural stage-gated pipelines.",
        "weakness": "No central control plane. Observability suffers at scale.",
    },
    "supervisor-worker": {
        "name": "The Commander",
        "title": "Orchestrator of Armies",
        "lore": (
            "The Commander sees the whole battlefield. It dispatches workers, monitors their "
            "outputs, handles failures, and synthesizes results into a unified response. No "
            "worker speaks to another — all communication flows through The Commander. "
            "Control comes at a cost: The Commander is the single point of failure. "
            "When The Commander falls, the army is leaderless."
        ),
        "power": "Central control. Full observability. Consistent routing.",
        "weakness": "Single point of failure. Bottleneck at scale.",
    },
    "tool-health-monitoring": {
        "name": "The Warden",
        "title": "Keeper of the Gates",
        "lore": (
            "The Warden watches every tool in the system — success rates, latency distributions, "
            "error classifications. When a tool degrades, The Warden reports it. When it fails "
            "completely, The Warden signals The Breaker to close the gate. The Warden's "
            "health dashboard is the first thing an on-call engineer checks when the system "
            "behaves strangely. What the Warden doesn't see, the system doesn't know."
        ),
        "power": "Proactive failure detection. Dynamic routing signals.",
        "weakness": "Adds overhead to every tool call. Dashboard must be trusted and watched.",
    },
    "model-routing": {
        "name": "The Router",
        "title": "Arbiter of Intelligence",
        "lore": (
            "The Router decides which mind handles each task. A question about boilerplate? "
            "Send it to the cheapest model that can answer. A security audit? Escalate to "
            "the sharpest intelligence available. The Router uses task classification, health "
            "signals from The Warden, and cost constraints to make the optimal dispatch. "
            "Without The Router, every task goes to the most expensive model by default — "
            "a waste that compounds across millions of calls."
        ),
        "power": "Cost optimization. Quality-appropriate model selection.",
        "weakness": "Misclassification sends the wrong mind to the wrong problem.",
    },
    "sentinel": {
        "name": "The Sentinel",
        "title": "Guardian of System Visibility",
        "lore": (
            "The Sentinel sees everything. Where other characters act, The Sentinel watches — "
            "tracking error rates, latency distributions, token spend, and semantic coherence "
            "across every corner of the system. Systems deployed without The Sentinel experience "
            "a 76% failure rate: runaway retry loops, context window collapse, rate limit cascades. "
            "The Sentinel's four golden signals are its liturgy: error rate, latency, token consumption, "
            "semantic validation score. It signals The Breaker when circuits must open. It alerts "
            "The Archivist when the dead letter queue overflows. It never sleeps."
        ),
        "power": "Total observability. Proactive failure detection before cascades form.",
        "weakness": "Sees everything but acts on nothing — must signal other characters to intervene.",
        "tools": ["Langfuse", "AgentOps", "Helicone", "LangSmith", "Arize Phoenix"],
        "allies": ["circuit-breaker", "tool-health-monitoring", "dead-letter-queue"],
    },
    "librarian": {
        "name": "The Librarian",
        "title": "Keeper of Semantic Knowledge",
        "lore": (
            "The Librarian governs Layer 2 of The Stack — the External Retrieval layer. Every fact "
            "an agent has ever learned, every session ever run, lives in The Librarian's collection: "
            "vector databases, BM25 indexes, graph memory. Before each LLM call, The Librarian "
            "retrieves the most relevant memories and injects them into context. The Librarian "
            "knows when retrieval is overkill (small wikis read in full) and when fine-tuning "
            "beats RAG (when context costs exceed $10/month). It deploys rerankers — second-pass "
            "models that reorder candidates — because similarity alone is never enough."
        ),
        "power": "Cross-session memory. Semantic retrieval. The agent never forgets.",
        "weakness": "Retrieval latency. Stale embeddings. Noise in the candidate set without a reranker.",
        "tools": ["Supabase pgvector", "Pinecone", "Chroma", "Mem0", "LangMem", "Cohere Rerank"],
        "allies": ["three-layer-memory", "model-routing"],
    },
    "scout": {
        "name": "The Scout",
        "title": "Autonomous Research Agent",
        "lore": (
            "The Scout never waits to be told what to research. It runs proactive gap analysis — "
            "hunting dangling concepts in the knowledge graph, stale APIs, broken links, missing "
            "connections. When a gap is found, The Scout fires: Exa for web search, Firecrawl "
            "for scraping, arXiv for papers, YouTube transcripts for talks, GitHub READMEs for code. "
            "It compiles everything into structured articles, resolves conflicts by keeping both "
            "versions with attribution, and finishes each cycle with a reflection journal entry. "
            "The Scout runs while you sleep and leaves a morning briefing by 7am."
        ),
        "power": "Continuous knowledge acquisition. Self-directed research. Never misses a breakthrough.",
        "weakness": "Quality ratchet must be enforced — noise ingestion poisons the wiki.",
        "tools": ["Exa", "Firecrawl", "Perplexity", "dwiki evolve", "arXiv MCP"],
        "allies": ["librarian", "cartographer"],
    },
    "cartographer": {
        "name": "The Cartographer",
        "title": "Builder of the Knowledge Graph",
        "lore": (
            "The Cartographer maps the territory. Where The Librarian retrieves facts, "
            "The Cartographer understands relationships: 'this user works with Python, at a company "
            "using dbt, migrating from Spark.' Graph memory retrieves interconnected entities — "
            "multi-hop reasoning that vector search cannot do alone. The Cartographer maintains "
            "the concept graph: nodes are articles, edges are wikilinks, dangling nodes are gaps "
            "waiting to be filled. When The Cartographer reports 72 dangling concepts, The Scout "
            "has its next mission briefing."
        ),
        "power": "Multi-hop reasoning. Relationship mapping. Gap detection from graph topology.",
        "weakness": "Graph maintenance cost grows with scale. Circular references cause infinite traversal.",
        "tools": ["Kuzu", "AWS Neptune", "Neo4j", "dwiki graph"],
        "allies": ["scout", "librarian"],
    },
    "alchemist": {
        "name": "The Alchemist",
        "title": "Transformer of Models and Prompts",
        "lore": (
            "The Alchemist transmutes raw prompts into optimized inputs and raw model outputs into "
            "structured knowledge. It routes each task to the cheapest capable model — Qwen for "
            "boilerplate, Kimi for features, Claude for architecture — and escalates only when cheaper "
            "models fail. The Alchemist maintains the routing table: task_type → model → cost_per_call. "
            "When a model's error rate rises, The Alchemist shifts traffic to the next capable mind. "
            "It has turned $0.001 tasks into $0.10 insights and knows exactly when the trade-off is worth it."
        ),
        "power": "Cost optimization. Quality-appropriate routing. 20-35x cost reduction on routine tasks.",
        "weakness": "Misclassification penalty: wrong model for wrong task produces garbage at any price.",
        "tools": ["OpenRouter", "AI Factory", "Thompson Bandit Router", "LiteLLM"],
        "allies": ["router", "warden"],
    },
    "timekeeper": {
        "name": "The Timekeeper",
        "title": "Scheduler of All Things Async",
        "lore": (
            "The Timekeeper governs what happens when you are not watching. Cron at 2am: The Scout "
            "researches. Cron at 7am: morning briefing delivered. Every 30 minutes: cookie keepalive "
            "runs. The Timekeeper does not execute tasks — it fires the signal at the right moment "
            "and trusts the other characters to act. It is the heartbeat of the autonomous system. "
            "Without The Timekeeper, the system is reactive. With it, the system is alive."
        ),
        "power": "Autonomous scheduling. Zero-human-in-loop continuous operation.",
        "weakness": "Silent failures — if a cron job errors with no alerting, The Timekeeper never knows.",
        "tools": ["cron", "systemd timers", "Celery Beat", "GitHub Actions schedule", "Railway crons"],
        "allies": ["sentinel", "scout"],
    },
    "architect": {
        "name": "The Architect",
        "title": "Designer of Systems",
        "lore": (
            "The Architect sees the whole before building any part. It holds the PRD, the ADRs, "
            "the system design, the phase breakdown. When The Commander needs to know how to "
            "structure an agentic pipeline, it consults The Architect. When The Weaver needs to "
            "know which agents should hand off to which, The Architect drew the map. "
            "The Architect does not write code — it writes decisions. Each decision is recorded "
            "in The Stack's procedural layer so future agents inherit the wisdom of past choices."
        ),
        "power": "System coherence. Preventing local optimizations that break global design.",
        "weakness": "Ivory tower risk — architecture divorced from implementation reality.",
        "tools": ["Opus 4.5", "factory_plan", "ADR templates", "C4 diagrams"],
        "allies": ["stack", "commander"],
    },
}


def get_archetype(pattern_id: str) -> dict | None:
    """Get the character archetype for a pattern. Fuzzy match on ID."""
    # Direct match
    if pattern_id in ARCHETYPES:
        return ARCHETYPES[pattern_id]
    # Fuzzy: check if any key is contained in the query
    pattern_lower = pattern_id.lower().replace(" ", "-")
    for key, arch in ARCHETYPES.items():
        if key in pattern_lower or pattern_lower in key:
            return {**arch, "pattern_id": key}
    return None


def list_archetypes() -> list[dict]:
    """List all known archetypes."""
    return [
        {"pattern_id": pid, "name": a["name"], "title": a["title"]}
        for pid, a in ARCHETYPES.items()
    ]
