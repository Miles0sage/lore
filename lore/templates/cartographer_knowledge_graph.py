# LORE SCAFFOLD: cartographer_knowledge_graph
"""
Cartographer Knowledge Graph — The Cartographer, Builder of the Knowledge Graph

Knowledge graph builder for multi-hop reasoning. Where The Librarian
retrieves facts, The Cartographer understands relationships.

Usage:
    graph = KnowledgeGraph()
    graph.add_node(Node("circuit-breaker", "pattern", {"tier": "core"}))
    graph.add_node(Node("dead-letter-queue", "pattern", {"tier": "core"}))
    graph.add_edge(Edge("circuit-breaker", "dead-letter-queue", "feeds_failures_to"))
    path = graph.find_path("circuit-breaker", "dead-letter-queue")
    neighbors = graph.get_neighbors("circuit-breaker")
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    """Immutable node in the knowledge graph."""
    id: str
    type: str = "concept"
    properties: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """Immutable directed edge between two nodes."""
    source: str
    target: str
    relation: str = "related_to"
    weight: float = 1.0
    properties: dict = field(default_factory=dict)


class KnowledgeGraph:
    """In-memory knowledge graph with BFS path finding."""

    def __init__(self):
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        self._adjacency: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self._nodes = {**self._nodes, node.id: node}
        if node.id not in self._adjacency:
            self._adjacency = {**self._adjacency, node.id: []}

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge. Creates missing nodes automatically."""
        self._edges = [*self._edges, edge]
        if edge.source not in self._adjacency:
            self._adjacency = {**self._adjacency, edge.source: []}
        self._adjacency[edge.source] = [*self._adjacency[edge.source], edge]

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str, relation: str | None = None) -> list[tuple[Node, Edge]]:
        """Get all neighbors of a node, optionally filtered by relation type."""
        edges = self._adjacency.get(node_id, [])
        if relation:
            edges = [e for e in edges if e.relation == relation]
        return [
            (self._nodes[e.target], e)
            for e in edges
            if e.target in self._nodes
        ]

    def find_path(self, start: str, end: str, max_depth: int = 10) -> list[str] | None:
        """Find shortest path between two nodes using BFS."""
        if start not in self._adjacency or end not in self._nodes:
            return None

        visited: set[str] = {start}
        queue: deque[list[str]] = deque([[start]])

        while queue:
            path = queue.popleft()
            if len(path) > max_depth:
                return None

            current = path[-1]
            if current == end:
                return path

            for edge in self._adjacency.get(current, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append([*path, edge.target])

        return None

    def dangling_nodes(self) -> list[str]:
        """Find nodes referenced in edges but not added as nodes."""
        edge_targets = {e.target for e in self._edges}
        edge_sources = {e.source for e in self._edges}
        referenced = edge_targets | edge_sources
        return sorted(referenced - set(self._nodes.keys()))

    def stats(self) -> dict:
        """Return graph statistics."""
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "dangling": len(self.dangling_nodes()),
            "node_types": list({n.type for n in self._nodes.values()}),
            "relation_types": list({e.relation for e in self._edges}),
        }
