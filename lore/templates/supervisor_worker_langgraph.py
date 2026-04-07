# LORE SCAFFOLD: supervisor_worker (LangGraph variant)
"""
Supervisor-Worker as a LangGraph state machine.

The supervisor node classifies tasks and routes to specialist worker nodes.
Workers return results that the supervisor synthesizes.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import StateGraph, END


class WorkflowState(TypedDict):
    task: str
    task_type: str
    worker_output: str
    final_result: str
    error: str


def supervisor_node(state: WorkflowState) -> WorkflowState:
    """Supervisor classifies the task and determines routing."""
    task = state["task"].lower()
    if any(kw in task for kw in ("test", "spec", "coverage")):
        task_type = "tester"
    elif any(kw in task for kw in ("security", "auth", "vulnerability")):
        task_type = "security"
    else:
        task_type = "coder"
    return {**state, "task_type": task_type}


def tester_node(state: WorkflowState) -> WorkflowState:
    """Test writing worker."""
    return {**state, "worker_output": f"Tests for: {state['task']}"}


def coder_node(state: WorkflowState) -> WorkflowState:
    """Code writing worker."""
    return {**state, "worker_output": f"Implementation for: {state['task']}"}


def security_node(state: WorkflowState) -> WorkflowState:
    """Security review worker."""
    return {**state, "worker_output": f"Security review for: {state['task']}"}


def synthesize_node(state: WorkflowState) -> WorkflowState:
    """Supervisor synthesizes worker output into final result."""
    return {**state, "final_result": f"[{state['task_type']}] {state['worker_output']}"}


def route_to_worker(state: WorkflowState) -> str:
    return state["task_type"]


def build_supervisor_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("tester", tester_node)
    graph.add_node("coder", coder_node)
    graph.add_node("security", security_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", route_to_worker, {
        "tester": "tester", "coder": "coder", "security": "security",
    })
    graph.add_edge("tester", "synthesize")
    graph.add_edge("coder", "synthesize")
    graph.add_edge("security", "synthesize")
    graph.add_edge("synthesize", END)

    return graph
