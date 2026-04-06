---
backlinks: []
concepts:
- retrieval-augmented-generation
- three-layer-memory-stack
- bm25
- reranking
- hybrid-search
- chunking
- graph-memory
- fine-tuning
- semantic-search
confidence: high
created: '2026-04-05'
domain: ai-agents
id: librarian-retrieval-pattern
sources:
- raw/2026-04-05-librarian-retrieval-proposal.md
status: published
title: 'The Librarian: Retrieval Patterns for Production AI Agents'
updated: '2026-04-06'
---

# The Librarian: Retrieval Patterns for Production AI Agents

## Overview

The Librarian governs retrieval for long-running agent systems. Its job is not merely to fetch documents — it decides **what** to retrieve, **when** retrieval is worth the cost, and **when** a cheaper strategy is better. The Librarian is the operational form of retrieval-augmented generation (RAG) for agents that need continuity across sessions.

Naive RAG is a solved problem. Production RAG is not. This article covers the decisions that separate working retrieval from retrieval that actually holds up under load.

## The Retrieval Decision Tree

Before reaching for a vector database, work through this decision:

```
Is the corpus small and stable? (<500 docs, rarely changes)
  → BM25 or direct read. No embeddings needed.

Is the corpus medium with overlapping topics? (500–50K docs)
  → Semantic search + reranker. Embed on ingest, rerank at query time.

Is the problem relational? (dependencies, lineage, cross-references)
  → Graph memory. Similarity search will miss structural relationships.

Is the same knowledge recalled on every request?
  → Fine-tune or adapter. Stop paying retrieval cost every call.

Is the corpus enormous and domain-specific? (>50K docs)
  → Hierarchical retrieval: route to sub-corpus first, then retrieve within it.
```

The point is not "always use RAG." The point is to use the **cheapest strategy that preserves answer quality**.

## Placement in the Memory Stack

The Librarian primarily governs Layer 2 of the [[three-layer-memory-stack]]: external retrieval. It sits between transient context (Layer 1) and long-lived procedural memory (Layer 3), deciding what evidence belongs in the current reasoning window.

```
Layer 1: In-context (fast, expensive per token)
           ↑ Librarian decides what to inject
Layer 2: External retrieval (BM25, vector, graph)
           ↑ Librarian manages indexes and strategies
Layer 3: Procedural memory (fine-tunes, adapters, distilled rules)
```

## Chunking Strategy

Chunking is the most underrated retrieval decision. Wrong chunk size kills recall before a query is even issued.

### Chunk size heuristics

| Corpus type | Chunk size | Overlap | Why |
|---|---|---|---|
| Technical docs, code | 256–512 tokens | 10% | Precise, self-contained units |
| Research papers | 512–1024 tokens | 15% | Argument spans multiple sentences |
| Conversational logs | 128–256 tokens | 20% | Context shifts fast |
| Legal / compliance | 1024–2048 tokens | 5% | Paragraph integrity matters |

### Semantic chunking (preferred over fixed-size)

Split on meaning boundaries rather than token counts. Use sentence embeddings to detect when the topic shifts:

```python
def semantic_chunk(text: str, threshold: float = 0.3) -> list[str]:
    """Split text where embedding similarity drops below threshold."""
    sentences = sent_tokenize(text)
    embeddings = embed(sentences)
    chunks, current = [], [sentences[0]]
    for i in range(1, len(sentences)):
        sim = cosine_similarity(embeddings[i-1], embeddings[i])
        if sim < threshold:
            chunks.append(" ".join(current))
            current = []
        current.append(sentences[i])
    if current:
        chunks.append(" ".join(current))
    return chunks
```

### Hierarchical chunking (for long documents)

Store both full documents and chunks. Retrieve chunks, but return their parent document section for context:

```
index: chunks (256 tokens, for precision)
store: sections (1024 tokens, for context window)
query → retrieve chunk → return parent section
```

## Hybrid Search: BM25 + Semantic

Neither BM25 nor semantic search alone is best. Hybrid search beats both on most production corpora.

```python
def hybrid_search(
    query: str,
    bm25_index,
    vector_index,
    top_k: int = 10,
    alpha: float = 0.6,   # weight for semantic score
) -> list[Document]:
    """Combine BM25 and semantic scores with reciprocal rank fusion."""
    bm25_results = bm25_index.search(query, top_k=top_k * 2)
    semantic_results = vector_index.search(query, top_k=top_k * 2)

    # Reciprocal Rank Fusion
    scores: dict[str, float] = {}
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] = scores.get(doc.id, 0) + (1 - alpha) / (rank + 60)
    for rank, doc in enumerate(semantic_results):
        scores[doc.id] = scores.get(doc.id, 0) + alpha / (rank + 60)

    all_docs = {d.id: d for d in bm25_results + semantic_results}
    return sorted(
        [all_docs[id] for id in scores],
        key=lambda d: scores[d.id],
        reverse=True,
    )[:top_k]
```

`alpha=0.6` gives slight preference to semantic. Tune based on your query patterns:
- More keyword queries → lower alpha (more BM25)
- More conceptual queries → higher alpha (more semantic)

## Reranking

Rerankers are valuable when the initial candidate set is noisy. They run a cross-encoder (slower but more accurate) over the top-K results from the first-pass retrieval.

```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, candidates: list[Document], top_n: int = 5) -> list[Document]:
    pairs = [(query, doc.content) for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:top_n]]
```

**When reranking helps:**
- Many articles partially match a concept
- Queries are ambiguous (same words, different intents)
- Initial retrieval returns near-duplicates

**When to skip reranking:**
- Corpus is small and well-curated (BM25 already precise)
- Latency is critical (cross-encoder adds 50–200ms)
- You're running in a cost-constrained environment

## Graph Memory

Graph memory becomes important when the problem is **relational rather than lexical**:
- which patterns depend on one another
- which frameworks share the same trade-off
- which articles reference concepts that still lack canon coverage

The Librarian works with [[archetype-the-cartographer]] for graph-based retrieval. The Cartographer maps entity relationships; the Librarian decides whether to traverse the graph or do a similarity search.

```python
# Graph retrieval: find articles that reference a concept
def graph_context(concept: str, graph: KnowledgeGraph, depth: int = 2) -> list[str]:
    nodes = graph.find_nodes(concept)
    for _ in range(depth - 1):
        neighbors = []
        for node in nodes:
            neighbors.extend(graph.neighbors(node))
        nodes = list(set(nodes + neighbors))
    return [graph.get_article(node) for node in nodes]
```

## When Fine-Tuning Beats Retrieval

Retrieval is not always the best answer. Fine-tuning or adapters become attractive when:

| Condition | Why |
|---|---|
| Same facts recalled on every request | Retrieval cost accumulates faster than fine-tune cost |
| Corpus has stabilized | No need to update embeddings |
| Consistent style/formatting required | Retrieval injects noise from varied source writing |
| Decision boundaries need to be sharp | Fine-tuned models generalize better than retrieved examples |

The Librarian should know when retrieval has become too expensive or too noisy — and hand off to The Alchemist (fine-tuning) or The Archivist (distilled rules).

## Index Maintenance

Stale indexes are silent failures. Build maintenance into the ingestion pipeline:

```python
class IndexMaintainer:
    def __init__(self, index, ttl_days: int = 30):
        self.index = index
        self.ttl = timedelta(days=ttl_days)

    def prune_stale(self) -> int:
        cutoff = datetime.utcnow() - self.ttl
        stale = [d for d in self.index.all() if d.updated_at < cutoff]
        for doc in stale:
            self.index.delete(doc.id)
        return len(stale)

    def reindex_changed(self, changed_paths: list[Path]) -> int:
        for path in changed_paths:
            doc = parse_document(path)
            self.index.upsert(doc)
        return len(changed_paths)
```

Run `prune_stale` weekly. Run `reindex_changed` on every wiki publish.

## Query Expansion

When queries are short or ambiguous, expand them before retrieval:

```python
def expand_query(query: str, model: str = "deepseek-chat") -> list[str]:
    """Generate semantic variants of the query for broader retrieval."""
    prompt = f"""Generate 3 alternative phrasings of this search query.
Return only the phrasings, one per line.
Query: {query}"""
    response = llm(prompt, model=model)
    variants = [query] + [line.strip() for line in response.splitlines() if line.strip()]
    return variants[:4]
```

Then retrieve against all variants and merge results with deduplication.

## Production Retrieval Runbook

| Symptom | Probable cause | Fix |
|---|---|---|
| Results are near-duplicates | No diversity enforcement | Add MMR (maximal marginal relevance) |
| Relevant doc never returned | Chunking cut across key concept | Increase chunk overlap or use semantic chunks |
| Old content returned | Stale index | Run `reindex_changed` on recent wiki updates |
| Retrieval too slow | Cross-encoder on all candidates | Rerank only top 20, not all results |
| Wrong context injected | Similarity threshold too low | Add minimum score cutoff |
| High cost per query | Embedding every query from scratch | Cache embeddings for common queries |

## Failure Modes

Retrieval fails when:

- **Similarity search returns near-duplicates** with no curation — the corpus needs editorial quality before retrieval quality matters
- **Stale documents stay indexed** long after canon changed — build TTL maintenance into the pipeline
- **Operators treat retrieval as a substitute for editorial quality** — garbage in, garbage out
- **Everything becomes "RAG"** even when a direct read or structured graph query is faster and cheaper

Good retrieval begins with a good canon.

## Key Concepts

[[retrieval-augmented-generation]]
[[three-layer-memory-stack]]
[[bm25]]
[[hybrid-search]]
[[reranking]]
[[graph-memory]]
[[semantic-search]]
[[fine-tuning]]
[[archetype-the-cartographer]]
[[archetype-the-librarian]]

## Sources

- `2026-04-05-librarian-retrieval-proposal.md`
- `2026-04-05-three-layer-memory-stack-for-ai-agents.md`
- LORE production RAG implementation (lore/search.py)
