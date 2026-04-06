# The Scout

**"First into the unknown. Back with the truth."**

---

## The Identity

**Archetype:** The Scout  
**Domain:** Web Research, External Search, Discovery, Information Gathering  
**Formal Pattern:** Research Agent  
**Allied Archetypes:** The Librarian (RAG), The Archivist (Memory), The Alchemist (Extraction), The Council (Supervisor-Worker)

---

## The Lore

The system has questions. The answers are out there — on the web, in academic papers, in GitHub repos, in earnings calls, in tweets. But the world is vast, noisy, and hostile to naive search.

**The Scout** goes first. Before the agent reasons, before the system decides, before a word is written — The Scout has already been out, assessed the terrain, and returned with what matters. Not everything. Not the noise. The signal.

The Scout doesn't hand you the web. It hands you the answer.

A bad Scout returns with 10,000 results. A good Scout returns with three paragraphs, sourced and grounded. The difference is the Scout's judgment — knowing what to search, how deep to go, when to stop.

---

## The Pattern

**Formal Name:** Research Agent  
**Core Philosophy:** Decompose a research question into targeted searches across multiple sources, synthesize results into structured knowledge, and return grounded findings — not raw links. The Scout is the difference between "I searched for X" and "Here's what's true about X."

---

## The Mechanism

### Tool Stack

The Scout assembles a tool stack by source type:

```python
SCOUT_TOOLS = {
    # Semantic web search — best for current events, recent content
    "web_semantic": exa.search,           # semantic neural search
    "web_keyword": perplexity.search,     # keyword + synthesis
    "web_deep": perplexity.deep_research, # multi-step research mode
    
    # Academic sources
    "arxiv": arxiv_mcp.search,            # papers + preprints
    "scholar": google_scholar.search,     # peer-reviewed literature
    "patents": patents_mcp.search,        # patent filings
    
    # Code & technical
    "github": github_mcp.search_repos,    # repositories, code
    "github_code": github_mcp.search_code,# specific implementations
    
    # Structured data
    "wikipedia": wikipedia_mcp.search,    # encyclopedic facts
    "news": google_news.search,           # current news
    "trends": google_trends.get,          # interest over time
    
    # Video
    "youtube": youtube_mcp.search,        # find relevant videos
    "transcript": youtube_mcp.transcript, # extract from video
}
```

### The Research Loop

```python
async def scout(question: str, depth: str = "standard") -> dict:
    """
    The Scout's core research loop.
    depth: "quick" (1-2 sources) | "standard" (3-5) | "deep" (multi-step)
    """
    plan = await planner_llm.generate(f"""
    Research question: {question}
    
    Create a research plan:
    1. What sources are most relevant? (web/academic/code/news)
    2. What are 3 specific search queries to run?
    3. What would a complete answer require?
    
    Return JSON: {{"sources": [...], "queries": [...], "completeness_criteria": "..."}}
    """)
    
    # Execute searches in parallel
    search_tasks = []
    for query in plan["queries"]:
        for source in plan["sources"]:
            search_tasks.append(SCOUT_TOOLS[source](query))
    
    raw_results = await asyncio.gather(*search_tasks, return_exceptions=True)
    
    # Filter failures (The Breaker has already protected individual calls)
    valid_results = [r for r in raw_results if not isinstance(r, Exception)]
    
    # Synthesize
    synthesis = await synthesizer_llm.generate(f"""
    Research question: {question}
    
    Raw findings:
    {format_results(valid_results)}
    
    Synthesize into:
    1. Direct answer (2-3 sentences)
    2. Key findings (bullet points with sources)
    3. Confidence level (high/medium/low) and why
    4. What's uncertain or contested
    5. Recommended next searches if needed
    """)
    
    return {
        "question": question,
        "answer": synthesis,
        "sources_checked": len(search_tasks),
        "sources_used": len(valid_results),
        "depth": depth
    }
```

### Multi-Step Deep Research

For complex questions, the Scout iterates — each finding informing the next search:

```python
async def deep_scout(question: str, max_iterations: int = 5) -> dict:
    """ReAct-style iterative research"""
    context = []
    
    for i in range(max_iterations):
        # Reason: what do I know, what do I need?
        reasoning = await llm.generate(f"""
        Question: {question}
        What I know so far: {context}
        
        What should I search next? Or is this complete?
        Return: {{"action": "search|done", "query": "...", "source": "...", "reason": "..."}}
        """)
        
        if reasoning["action"] == "done":
            break
        
        # Act: run the search
        result = await SCOUT_TOOLS[reasoning["source"]](reasoning["query"])
        context.append({
            "query": reasoning["query"],
            "source": reasoning["source"],
            "finding": result[:1000],  # truncate to prevent context rot
            "reason": reasoning["reason"]
        })
    
    # Final synthesis
    return await synthesize(question, context)
```

---

## Source Selection Strategy

The Scout chooses sources based on question type:

| Question Type | Primary Source | Secondary | Avoid |
|---------------|---------------|-----------|-------|
| Current events | Perplexity, Exa | Google News | Wikipedia (stale) |
| Technical "how to" | GitHub code search | arXiv, docs | Wikipedia |
| Academic claims | arXiv, Scholar | Wikipedia | News (not peer-reviewed) |
| Market/trends | Google Trends, News | Perplexity | Wikipedia |
| People/companies | Exa people search | News | arXiv |
| Code implementations | GitHub repos | arXiv (for ML) | News |
| Historical facts | Wikipedia | Scholar | Twitter/X |
| Product comparisons | Exa semantic | Perplexity | Single source |

---

## Critical Use Cases — When to Summon The Scout

1. **Before building anything** — "What has already been built? What are the stars? What are the patterns?" The Scout surveys the landscape before the team commits to an approach.

2. **Competitive intelligence** — "What are competitors doing? What's the market doing? What are users saying?" The Scout finds the signal.

3. **Research pipelines** — In a Supervisor-Worker system, the supervisor dispatches Scouts in parallel to gather information before synthesis workers combine findings.

4. **Newsletter and content agents** — The Scout finds the best content published this week. The Alchemist extracts key insights. The human receives a curated digest.

5. **Due diligence agents** — "Tell me everything about this company / person / technology." The Scout runs across all source types and returns a structured report.

6. **NotebookLM as Scout** — `notebooklm_ask` is The Scout querying a curated knowledge base. 59 articles → answer with 233 citations. The Scout with a curated library beats raw web search for known domains.

---

## Scout Quality Metrics

A Scout's output quality is measurable:

```python
SCOUT_METRICS = {
    "source_diversity": len(unique_sources) / len(total_sources),  # > 0.6 is good
    "citation_rate": len(cited_claims) / len(total_claims),        # > 0.8
    "search_efficiency": useful_results / total_searches,          # > 0.5
    "answer_confidence": confidence_score,                         # high/medium/low
    "hallucination_risk": 1 - citation_rate,                       # low is good
}
```

If citation_rate drops below 0.6, the Scout is hallucinating. If source_diversity is below 0.3, the Scout is tunnel-visioning on one source type.

---

## The Alliance

**The Librarian (RAG):**  
The Librarian retrieves from known internal knowledge. The Scout searches unknown external territory. They are complementary: The Librarian for what you have, The Scout for what's out there. In a research system, The Scout runs first, then stores findings so The Librarian can retrieve them later.

**The Archivist (Memory):**  
After the Scout returns findings, The Archivist decides what's worth keeping in long-term memory. Not everything The Scout finds gets archived — only what's persistently useful. The Scout hunts; The Archivist curates.

**The Alchemist:**  
The Scout finds raw material. The Alchemist transforms it into structured knowledge — extracts entities, builds knowledge graphs, generates summaries. The Scout and Alchemist form a pipeline: discover → extract → structure.

**The Council (Supervisor-Worker):**  
The Council dispatches Scouts in parallel for multi-faceted research questions. "Research X from these 5 angles" → 5 Scouts running concurrently → Council synthesizes results.

---

## Grimoire — Framework Implementations

**Exa (Semantic Search):**  
`exa.search(query, type="neural")` — semantic search over the web. Best for conceptual questions. `exa.find_similar(url)` — find pages similar to a known good source.

**Perplexity (Synthesis Search):**  
`sonar` model: standard search with citations. `sonar-pro`: detailed, more sources. `sonar-deep-research`: multi-step iterative research. The Perplexity API IS The Scout for web research.

**Google Research MCP:**  
Our own stack: `google_scholar`, `arxiv_search`, `arxiv_paper`, `google_news`, `youtube_search`, `youtube_transcript`, `patents_search`, `wikipedia`. The Scout's full toolkit in one MCP server.

**Firecrawl:**  
`firecrawl_scrape(url)` — extract structured content from any webpage. `firecrawl_crawl(url)` — full site crawl. `firecrawl_search(query)` — search + scrape in one call. The Scout's deep excavation tool.

**NotebookLM Oracle:**  
For curated research domains, NotebookLM is The Scout operating over pre-indexed sources. 50+ sources → answer with 100+ citations. Faster and higher-quality than web search for known domains.

---

## Key Concepts

[[model-routing]] [[supervisor-worker-pattern]] [[three-layer-memory-stack]] [[google-mcp-ecosystem-2026]] [[ai-gmail-agents-knowledge-graph-2026]] [[agentic-coding]]

---

## Related Archetypes

- **The Librarian** — Internal knowledge retrieval complements The Scout's external search
- **The Archivist** — Preserves what The Scout finds worth keeping
- **The Alchemist** — Transforms The Scout's raw findings into structured knowledge
- **The Council** — Dispatches and coordinates multiple Scouts for parallel research
- **The Cartographer** — When The Scout finds a new codebase, The Cartographer maps it
