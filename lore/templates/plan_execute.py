# LORE SCAFFOLD: plan_execute
"""
Plan-Execute Loop — Plan steps, execute each, verify, replan if needed.

The agent generates a plan of steps, executes them one by one, verifies
each result, and replans if a step fails or produces unexpected output.

Usage:
    agent = PlanExecuteAgent()
    result = agent.run("Build a REST API with authentication and rate limiting")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Step:
    """Immutable plan step."""
    index: int
    description: str
    status: str = "pending"  # pending | running | completed | failed
    result: Any = None


@dataclass(frozen=True)
class PlanState:
    """Immutable snapshot of the plan execution state."""
    task: str
    steps: tuple[Step, ...]
    current_index: int = 0
    completed: bool = False
    replans: int = 0


@dataclass
class PlanExecuteAgent:
    """Plan-Execute-Verify loop agent."""

    max_replans: int = 2
    max_steps: int = 10

    def plan(self, task: str, context: str = "") -> list[str]:
        """Generate a list of step descriptions for the task.

        Override with an LLM planner in production.
        """
        # Placeholder — replace with LLM planning
        return [
            f"Step 1: Analyze requirements for {task}",
            f"Step 2: Implement core logic",
            f"Step 3: Add error handling",
            f"Step 4: Write tests",
            f"Step 5: Verify and finalize",
        ]

    def execute_step(self, step: Step, context: str = "") -> Any:
        """Execute a single step. Returns the result.

        Override with an LLM executor or tool calls in production.
        """
        # Placeholder — replace with actual execution
        return f"Completed: {step.description}"

    def verify(self, step: Step, result: Any) -> tuple[bool, str]:
        """Verify that a step produced the expected result.

        Returns (success, feedback). Override with LLM verifier in production.
        """
        # Placeholder — replace with LLM verification
        return True, "Step verified successfully."

    def replan(self, task: str, completed_steps: list[Step], failed_step: Step, feedback: str) -> list[str]:
        """Generate new steps after a failure.

        Override with an LLM replanner in production.
        """
        # Placeholder — replace with LLM replanning
        remaining = max(1, self.max_steps - len(completed_steps))
        return [f"Revised step {i+1}: retry {failed_step.description}" for i in range(remaining)]

    def run(self, task: str) -> dict[str, Any]:
        """Run the full plan-execute-verify loop."""
        step_descriptions = self.plan(task)
        steps = tuple(
            Step(index=i, description=desc)
            for i, desc in enumerate(step_descriptions[:self.max_steps])
        )
        state = PlanState(task=task, steps=steps)
        completed: list[Step] = []
        replans = 0

        for step in state.steps:
            result = self.execute_step(step, context=str(completed))
            success, feedback = self.verify(step, result)

            if success:
                done_step = Step(index=step.index, description=step.description, status="completed", result=result)
                completed = [*completed, done_step]
            else:
                failed_step = Step(index=step.index, description=step.description, status="failed", result=feedback)
                if replans < self.max_replans:
                    replans += 1
                    new_descriptions = self.replan(task, completed, failed_step, feedback)
                    new_steps = tuple(
                        Step(index=len(completed) + i, description=desc)
                        for i, desc in enumerate(new_descriptions[:self.max_steps - len(completed)])
                    )
                    state = PlanState(
                        task=task, steps=new_steps,
                        current_index=0, replans=replans,
                    )
                    # Continue with new plan
                    for new_step in state.steps:
                        r = self.execute_step(new_step, context=str(completed))
                        s, f = self.verify(new_step, r)
                        done = Step(index=new_step.index, description=new_step.description,
                                    status="completed" if s else "failed", result=r)
                        completed = [*completed, done]
                    break
                else:
                    completed = [*completed, failed_step]
                    return {
                        "status": "failed",
                        "completed_steps": len([s for s in completed if s.status == "completed"]),
                        "total_steps": len(completed),
                        "replans": replans,
                        "steps": [{"description": s.description, "status": s.status} for s in completed],
                    }

        return {
            "status": "completed",
            "completed_steps": len([s for s in completed if s.status == "completed"]),
            "total_steps": len(completed),
            "replans": replans,
            "steps": [{"description": s.description, "status": s.status} for s in completed],
        }
