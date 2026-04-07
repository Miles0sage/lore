# LORE SCAFFOLD: librarian_retrieval
"""
Librarian Retrieval — The Librarian, Keeper of Semantic Knowledge

RAG pipeline with quality scoring. The Librarian retrieves the most relevant
memories and injects them into context before each LLM call. Includes
relevance scoring and context window budgeting.

Usage:
    lib = Librarian()
    lib.add_document(Document(id="d1", content="Circuit breakers prevent cascading failures"))
    results = lib.retrieve("How to handle API failures?", top_k=3)
    context = lib.build_context_window(results, max_tokens=4000)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    """Immutable document in the library."""
    id: str
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class RetrievalResult:
    """Immutable retrieval result with relevance score."""
    document: Document
    score: float
    method: str = "keyword"  # keyword | vector | hybrid


class Librarian:
    """RAG pipeline with keyword search and relevance scoring.

    In production, replace _keyword_search with vector similarity
    (pgvector, Pinecone, Chroma) and add a reranker (Cohere Rerank).
    """

    def __init__(self):
        self._documents: dict[str, Document] = {}

    def add_document(self, doc: Document) -> None:
        """Add a document to the library."""
        self._documents = {**self._documents, doc.id: doc}

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document by ID. Returns True if found."""
        if doc_id in self._documents:
            self._documents = {k: v for k, v in self._documents.items() if k != doc_id}
            return True
        return False

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Retrieve top_k most relevant documents for query."""
        results = self._keyword_search(query)
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def score_relevance(self, query: str, content: str) -> float:
        """Score relevance of content to query (0.0 to 1.0).

        Replace with embedding cosine similarity in production.
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words:
            return 0.0
        overlap = len(query_words & content_words)
        return min(overlap / len(query_words), 1.0)

    def build_context_window(
        self, results: list[RetrievalResult], max_tokens: int = 4000
    ) -> str:
        """Build a context string from retrieval results within token budget.

        Approximates tokens as words / 0.75 (rough estimate).
        """
        context_parts: list[str] = []
        token_count = 0
        for result in results:
            # Rough token estimate: 1 token ~ 0.75 words
            est_tokens = int(len(result.document.content.split()) / 0.75)
            if token_count + est_tokens > max_tokens:
                break
            context_parts.append(
                f"[{result.document.id} | score={result.score:.2f}]\n{result.document.content}"
            )
            token_count += est_tokens
        return "\n\n---\n\n".join(context_parts)

    def _keyword_search(self, query: str) -> list[RetrievalResult]:
        """Simple keyword search — replace with vector search in production."""
        results = []
        for doc in self._documents.values():
            score = self.score_relevance(query, doc.content)
            if score > 0:
                results.append(RetrievalResult(document=doc, score=score))
        return results
