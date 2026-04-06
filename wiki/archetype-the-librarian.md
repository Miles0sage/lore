# The Librarian

**"The one who finds the right knowledge at exactly the right moment."**

---

## The Identity

**Archetype:** The Librarian  
**Domain:** Retrieval-Augmented Generation, Knowledge Access, Context Injection  
**Formal Pattern:** RAG (Retrieval-Augmented Generation)  
**Allied Archetypes:** The Archivist (Memory Stack), The Stack (Three-Layer Memory), The Cartographer (Codebase Navigation), The Sentinel (Observability)

---

## The Lore

Every agent has a context window. It is finite. It fills. And yet the world it must reason about is vast — millions of documents, thousands of past conversations, entire codebases, research papers, legal filings, customer records.

Without The Librarian, agents either hallucinate what they don't know or drown in everything they've been given. The Librarian solves this. Not by remembering everything — that's The Archivist's job. The Librarian's art is *retrieval*: finding the three most relevant paragraphs from a corpus of a million, injecting them precisely before the LLM speaks, and disappearing before the context gets crowded.

The Librarian does not know everything. The Librarian knows where everything is.

---

## The Pattern

**Formal Name:** Retrieval-Augmented Generation (RAG)  
**Core Philosophy:** Instead of fine-tuning a model on your data (expensive, stale) or stuffing everything into context (wasteful, overwhelming), retrieve only the most relevant chunks of external knowledge at query time and inject them into the LLM's prompt. The model reasons over current, targeted information — not stale training weights.

RAG was the answer to: "How does an agent know about your company's internal docs, last week's incident report, or the email from 3 months ago?" The answer is: it doesn't store them. It finds them.

---

## The Mechanism

RAG operates in three phases: **index**, **retrieve**, **generate**.

### Phase 1 — Index (Build The Library)

Documents are chunked into segments, embedded into vectors, and stored in a vector database alongside metadata.

**Chunking strategies:**

```python
# Fixed-size chunks (simple, fast)
def chunk_fixed(text, size=512, overlap=50):
    chunks = []
    for i in range(0, len(text), size - overlap):
        chunks.append(text[i:i + size])
    return chunks

# Semantic chunks (split on paragraph/section boundaries)
def chunk_semantic(text):
    return [p.strip() for p in text.split('\n\n') if len(p.strip()) > 100]

# Recursive character splitting (LangChain default, best general purpose)
from langchain.text_splitter import RecursiveCharacterTextSplitter
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_text(document)
```

**Embedding and storing:**

```python
import chromadb
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
client = chromadb.PersistentClient(path="./library")
collection = client.get_or_create_collection("knowledge_base")

for i, chunk in enumerate(chunks):
    embedding = model.encode(chunk).tolist()
    collection.add(
        ids=[f"doc_{doc_id}_chunk_{i}"],
        embeddings=[embedding],
        documents=[chunk],
        metadatas=[{"source": doc_name, "date": doc_date, "type": doc_type}]
    )
```

### Phase 2 — Retrieve (Find The Right Pages)

At query time, embed the user's question and find the closest chunks by cosine similarity.

**Pure vector search:**
```python
query_embedding = model.encode(user_query).tolist()
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"type": "policy"}  # optional metadata filter
)
retrieved_chunks = results['documents'][0]
```

**Hybrid search (BM25 + vector) — stronger than either alone:**
```python
from rank_bm25 import BM25Okapi

# BM25 keyword search
tokenized_corpus = [chunk.split() for chunk in all_chunks]
bm25 = BM25Okapi(tokenized_corpus)
bm25_scores = bm25.get_scores(user_query.split())
bm25_top = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:10]

# Vector search top-K
vector_top = [idx for idx in vector_search_results]

# Merge (Reciprocal Rank Fusion)
def rrf(rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

merged = rrf([bm25_top, vector_top])
```

**Reranking — the quality multiplier:**

After retrieval, a reranker model re-scores results for relevance. Retrieval is fast and approximate; reranking is slow and precise. Run reranking only on the top-K retrieved candidates.

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

pairs = [(user_query, chunk) for chunk in retrieved_chunks]
scores = reranker.predict(pairs)
reranked = [chunk for _, chunk in sorted(zip(scores, retrieved_chunks), reverse=True)]
top_chunks = reranked[:3]  # take only the best after reranking
```

### Phase 3 — Generate (Inject + Prompt)

Assemble retrieved chunks into the LLM prompt as context:

```python
context = "\n\n---\n\n".join(top_chunks)

prompt = f"""You are an assistant with access to the following retrieved knowledge:

<context>
{context}
</context>

Based only on the context above, answer the following question. If the answer is not in the context, say "I don't have that information."

Question: {user_query}
Answer:"""

response = llm.generate(prompt)
```

---

## The RAG Triad — Evaluation

Three dimensions for measuring RAG quality (from Chroma/Truera research):

| Dimension | Question | Metric |
|-----------|----------|--------|
| **Context Relevance** | Is the retrieved context relevant to the query? | Relevance score (LLM-as-judge) |
| **Groundedness** | Is the answer grounded in the context? | Faithfulness score |
| **Answer Relevance** | Does the answer address the question? | Answer relevance score |

A system scoring poorly on Context Relevance means retrieval is broken. Poor Groundedness means the LLM is hallucinating beyond its context. Poor Answer Relevance means the prompt is wrong.

---

## Critical Use Cases — When to Summon The Librarian

1. **Agent knowledge bases** — Internal docs, policies, wikis, historical decisions. The agent can't be fine-tuned on your company's internal data weekly. The Librarian retrieves on demand.

2. **Long-running agents with memory** — The Three-Layer Memory Stack's Layer 2 (External Retrieval) IS The Librarian. Every session start triggers a retrieval call to preload relevant historical context.

3. **Code agents navigating large repos** — Codebases exceed context windows. The Librarian retrieves relevant files, functions, and documentation before the agent writes code.

4. **Email and document AI** — The Gmail knowledge graph pattern uses The Librarian to answer "what decisions did we make with Acme Corp?" — vector search over embedded email history.

5. **lore_ask** — The wiki's own NotebookLM oracle IS The Librarian. 59 articles, 51 sources, indexed. Ask a question → retrieve relevant articles → answer with citations.

---

## Advanced Patterns

**Hypothetical Document Embeddings (HyDE):**  
Generate a fake answer to the query, embed that fake answer, then search for real documents similar to it. Works better than embedding the raw question for some domains.

```python
fake_answer = llm.generate(f"Write a short answer to: {query}")
query_embedding = embed(fake_answer)  # embed the fake answer, not the query
results = vector_search(query_embedding)
```

**Multi-query retrieval:**  
Generate 3-5 variant queries, retrieve for each, deduplicate. Covers more of the semantic space.

**Parent-child chunking:**  
Index small chunks (child) for precise retrieval, but inject their full parent section into context. Precision in retrieval, completeness in generation.

---

## The Alliance

**The Archivist (Three-Layer Memory Stack):**  
The Archivist manages the three layers. The Librarian IS Layer 2 — the retrieval mechanism that makes episodic memory work. They are the same system viewed from different angles: Archivist is the architecture, Librarian is the action.

**The Cartographer (Codebase Navigation):**  
For code agents, The Librarian retrieves relevant code. The Cartographer maps the codebase structure. Together they give the code agent both semantic search (Librarian) and structural awareness (Cartographer).

**The Sentinel (Observability):**  
The Sentinel monitors The Librarian via the RAG Triad metrics. Low context relevance triggers an alert — retrieval pipeline needs retuning.

**The Council (Supervisor-Worker):**  
Before routing a task to a specialist worker, the Council calls The Librarian to retrieve relevant context and inject it into the worker's prompt. Workers don't search — they receive pre-retrieved knowledge.

---

## Grimoire — Framework Implementations

**LangChain RAG:**  
`RetrievalQA`, `ConversationalRetrievalChain` — standard RAG chains with memory. `MultiQueryRetriever` for variant query generation.

**LlamaIndex:**  
`VectorStoreIndex`, `SummaryIndex`, `KnowledgeGraphIndex`. Best framework specifically for RAG. Native parent-child chunking, HyDE, reranking.

**Supabase pgvector:**  
`CREATE EXTENSION vector;` — Postgres native vector storage. Hybrid search via combining `<=>` cosine similarity with `tsvector` full-text search. Used in the Three-Layer Memory Stack Layer 2.

**ChromaDB:**  
Local-first vector DB. `PersistentClient` for sessions that survive restarts. Best for development and single-server deployments.

**Pinecone:**  
Managed vector DB at scale. Serverless tier for small collections. Use when corpus exceeds 1M chunks or requires multi-tenant isolation.

---

## Key Concepts

[[three-layer-memory-stack]] [[agent-observability]] [[agentic-coding]] [[defeating-context-rot-mastering-the-flow-of-ai-sessions]] [[ai-gmail-agents-knowledge-graph-2026]]

---

## Related Archetypes

- **The Archivist** — Manages all three memory layers; The Librarian is the Layer 2 mechanism
- **The Cartographer** — Structural navigation complements The Librarian's semantic retrieval
- **The Sentinel** — Monitors retrieval quality via the RAG Triad
- **The Alchemist** — Transforms raw documents into indexed, embeddable chunks before The Librarian can use them
