# LORE SCAFFOLD: reflexion_loop
"""
Reflexion Loop — Attempt, Evaluate, Reflect, Retry.

The agent attempts a task, evaluates the result, reflects on what went wrong,
and retries with an improved strategy. Maintains a memory of past attempts
to avoid repeating mistakes.

Usage:
    agent = ReflexionAgent()
    result = agent.run("Write a function to sort a list without using built-in sort")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Attempt:
    """Immutable record of one attempt-evaluate-reflect cycle."""
    iteration: int
    output: str
    score: float
    evaluation: str
    reflection: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReflexionAgent:
    """Reflexion agent: attempt -> evaluate -> reflect -> retry."""

    max_attempts: int = 3
    acceptance_threshold: float = 0.8

    def __post_init__(self):
        self._attempts: list[Attempt] = []

    def attempt(self, task: str, past_reflections: list[str]) -> str:
        """Generate an attempt at the task, incorporating past reflections.

        Override with an LLM call in production.
        """
        context = ""
        if past_reflections:
            context = "\nPast reflections to incorporate:\n" + "\n".join(
                f"- {r}" for r in past_reflections
            )
        # Placeholder — replace with LLM generation
        return f"[Attempt for: {task}]{context}"

    def evaluate(self, task: str, output: str) -> tuple[float, str]:
        """Evaluate the quality of an attempt. Returns (score, evaluation_text).

        Override with an LLM evaluator or unit tests in production.
        """
        # Placeholder — replace with LLM evaluation or test harness
        score = min(0.5 + 0.2 * len(self._attempts), 1.0)
        evaluation = f"Score: {score:.2f}. Output length: {len(output)} chars."
        return score, evaluation

    def reflect(self, task: str, output: str, evaluation: str, score: float) -> str:
        """Reflect on what went wrong and how to improve.

        Override with an LLM reflection call in production.
        """
        # Placeholder — replace with LLM reflection
        return f"Score was {score:.2f}. Need to improve approach for: {task}"

    def run(self, task: str) -> dict[str, Any]:
        """Run the full reflexion loop."""
        self._attempts = []
        past_reflections: list[str] = []

        for i in range(1, self.max_attempts + 1):
            output = self.attempt(task, past_reflections)
            score, evaluation = self.evaluate(task, output)
            reflection = self.reflect(task, output, evaluation, score)

            attempt = Attempt(
                iteration=i,
                output=output,
                score=score,
                evaluation=evaluation,
                reflection=reflection,
            )
            self._attempts = [*self._attempts, attempt]
            past_reflections = [*past_reflections, reflection]

            if score >= self.acceptance_threshold:
                return {
                    "status": "accepted",
                    "result": output,
                    "score": score,
                    "iterations": i,
                    "attempts": [
                        {"score": a.score, "evaluation": a.evaluation, "reflection": a.reflection}
                        for a in self._attempts
                    ],
                }

        best = max(self._attempts, key=lambda a: a.score)
        return {
            "status": "best_effort",
            "result": best.output,
            "score": best.score,
            "iterations": self.max_attempts,
            "attempts": [
                {"score": a.score, "evaluation": a.evaluation, "reflection": a.reflection}
                for a in self._attempts
            ],
        }
