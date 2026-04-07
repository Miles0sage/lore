# LORE SCAFFOLD: reviewer_loop (LangGraph variant)
"""
Reviewer Loop as a LangGraph state machine.

Generator node produces output, reviewer node scores it.
Conditional edge loops back to generator if score < threshold.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, END


class ReviewState(TypedDict):
    prompt: str
    draft: str
    score: float
    feedback: str
    iteration: int
    max_iterations: int
    threshold: float


def generator_node(state: ReviewState) -> ReviewState:
    """Generate or revise a draft."""
    # Replace with actual LLM call
    draft = f"Draft v{state['iteration'] + 1} for: {state['prompt']}"
    if state["feedback"]:
        draft += f" (revised based on: {state['feedback']})"
    return {**state, "draft": draft, "iteration": state["iteration"] + 1}


def reviewer_node(state: ReviewState) -> ReviewState:
    """Review and score the draft."""
    # Replace with actual LLM review call
    score = min(0.5 + state["iteration"] * 0.2, 1.0)  # Simulated improvement
    feedback = "Needs more detail" if score < state["threshold"] else "Approved"
    return {**state, "score": score, "feedback": feedback}


def should_continue(state: ReviewState) -> str:
    if state["score"] >= state["threshold"]:
        return "accepted"
    if state["iteration"] >= state["max_iterations"]:
        return "escalate"
    return "revise"


def build_reviewer_graph() -> StateGraph:
    graph = StateGraph(ReviewState)
    graph.add_node("generator", generator_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("generator")
    graph.add_edge("generator", "reviewer")
    graph.add_conditional_edges("reviewer", should_continue, {
        "revise": "generator", "accepted": END, "escalate": END,
    })

    return graph
