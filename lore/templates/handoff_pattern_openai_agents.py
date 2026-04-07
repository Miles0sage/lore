# LORE SCAFFOLD: handoff_pattern (OpenAI Agents SDK variant)
"""
Handoff Pattern using OpenAI Agents SDK.

Agents hand off to each other using the SDK's native handoff mechanism.
Each agent declares which agents it can hand off to.
"""

from __future__ import annotations

from agents import Agent, Runner, handoff


planner_agent = Agent(
    name="Planner",
    instructions="You are a planner. Create detailed implementation plans. When done, hand off to the Implementer.",
    handoffs=["implementer_agent"],
)

implementer_agent = Agent(
    name="Implementer",
    instructions="You are an implementer. Execute the plan from the Planner. When done, hand off to the Validator.",
    handoffs=["validator_agent"],
)

validator_agent = Agent(
    name="Validator",
    instructions="You are a validator. Check that the implementation matches the plan. Return the final result.",
    handoffs=[],  # Terminal agent
)


async def run_handoff_pipeline(task: str) -> str:
    """Run the handoff pipeline starting with the Planner."""
    result = await Runner.run(planner_agent, task)
    return result.final_output


# Usage:
# import asyncio
# output = asyncio.run(run_handoff_pipeline("Build a circuit breaker module"))
