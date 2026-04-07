# LORE SCAFFOLD: circuit_breaker (LangGraph variant)
"""
Circuit Breaker as a LangGraph state machine.

States: CLOSED → OPEN → HALF_OPEN → CLOSED
Each state is a node. Edges are conditional on success/failure counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END


class CircuitState(TypedDict):
    name: str
    state: str  # CLOSED | OPEN | HALF_OPEN
    consecutive_failures: int
    failure_threshold: int
    result: Any
    error: str


def closed_node(state: CircuitState) -> CircuitState:
    """CLOSED state: attempt the call."""
    # Replace with actual tool/API call
    try:
        result = "success"  # Replace: await tool_call()
        return {**state, "result": result, "consecutive_failures": 0, "error": ""}
    except Exception as e:
        failures = state["consecutive_failures"] + 1
        new_state = "OPEN" if failures >= state["failure_threshold"] else "CLOSED"
        return {**state, "consecutive_failures": failures, "state": new_state, "error": str(e)}


def open_node(state: CircuitState) -> CircuitState:
    """OPEN state: return fallback, transition to HALF_OPEN after wait."""
    return {**state, "state": "HALF_OPEN", "result": None}


def half_open_node(state: CircuitState) -> CircuitState:
    """HALF_OPEN state: probe with single request."""
    try:
        result = "probe_success"  # Replace: await tool_call()
        return {**state, "state": "CLOSED", "consecutive_failures": 0, "result": result, "error": ""}
    except Exception as e:
        return {**state, "state": "OPEN", "error": str(e)}


def route_by_state(state: CircuitState) -> str:
    """Route to the correct node based on circuit state."""
    return state["state"].lower()


def build_circuit_breaker_graph() -> StateGraph:
    """Build a LangGraph circuit breaker state machine."""
    graph = StateGraph(CircuitState)
    graph.add_node("closed", closed_node)
    graph.add_node("open", open_node)
    graph.add_node("half_open", half_open_node)

    graph.set_entry_point("closed")
    graph.add_conditional_edges("closed", route_by_state, {"closed": END, "open": "open"})
    graph.add_edge("open", "half_open")
    graph.add_conditional_edges("half_open", route_by_state, {"closed": END, "open": "open"})

    return graph


# Usage:
# graph = build_circuit_breaker_graph()
# app = graph.compile()
# result = app.invoke({"name": "api", "state": "CLOSED", "consecutive_failures": 0, "failure_threshold": 3, "result": None, "error": ""})
