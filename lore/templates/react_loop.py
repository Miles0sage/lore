# LORE SCAFFOLD: react_loop
"""
ReAct Loop — Reason + Act cycle for tool-using agents.

The agent THINKs about the current state, ACTs by calling a tool,
then OBSERVEs the result. Repeats until the task is complete or
max_iterations is reached. Structured logging of every step.

Usage:
    agent = ReActAgent(tools={"search": my_search_fn, "calculate": my_calc_fn})
    result = agent.run("What is the population of France times 2?")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ReActStep:
    """Immutable record of one think-act-observe cycle."""
    iteration: int
    thought: str
    action: str
    action_input: Any
    observation: Any
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReActAgent:
    """ReAct (Reason + Act) loop agent with tool registry."""

    tools: dict[str, Callable[..., Any]] = field(default_factory=dict)
    max_iterations: int = 10
    verbose: bool = True

    def __post_init__(self):
        self._history: list[ReActStep] = []

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a tool the agent can use during reasoning."""
        self.tools = {**self.tools, name: fn}

    def think(self, task: str, history: list[ReActStep]) -> tuple[str, str, Any]:
        """Decide the next action based on task and history.

        Returns (thought, action_name, action_input).
        Override this with an LLM call in production.
        """
        # Placeholder — replace with LLM reasoning
        if not history:
            available = ", ".join(self.tools.keys()) or "none"
            return (
                f"I need to solve: {task}. Available tools: {available}.",
                "finish" if not self.tools else list(self.tools.keys())[0],
                task,
            )
        last = history[-1]
        return (
            f"Previous observation: {last.observation}. Deciding next step.",
            "finish",
            last.observation,
        )

    def act(self, action: str, action_input: Any) -> Any:
        """Execute a tool action. Returns observation."""
        if action == "finish":
            return action_input
        fn = self.tools.get(action)
        if fn is None:
            return f"Error: unknown tool '{action}'. Available: {list(self.tools.keys())}"
        try:
            return fn(action_input)
        except Exception as e:
            return f"Error calling {action}: {e}"

    def run(self, task: str) -> dict[str, Any]:
        """Run the full ReAct loop until completion or max iterations."""
        self._history = []

        for i in range(1, self.max_iterations + 1):
            thought, action, action_input = self.think(task, self._history)
            observation = self.act(action, action_input)

            step = ReActStep(
                iteration=i,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
            )
            self._history = [*self._history, step]

            if self.verbose:
                print(f"[Step {i}] Think: {thought}")
                print(f"[Step {i}] Act: {action}({action_input})")
                print(f"[Step {i}] Observe: {observation}")

            if action == "finish":
                return {
                    "status": "completed",
                    "result": observation,
                    "iterations": i,
                    "history": [
                        {"thought": s.thought, "action": s.action, "observation": s.observation}
                        for s in self._history
                    ],
                }

        return {
            "status": "max_iterations_reached",
            "result": self._history[-1].observation if self._history else None,
            "iterations": self.max_iterations,
            "history": [
                {"thought": s.thought, "action": s.action, "observation": s.observation}
                for s in self._history
            ],
        }
