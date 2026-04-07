# LORE SCAFFOLD: supervisor_worker (OpenAI Agents SDK variant)
"""
Supervisor-Worker using OpenAI Agents SDK.

A supervisor agent dispatches to specialist workers and synthesizes results.
"""

from __future__ import annotations

from agents import Agent, Runner, handoff


coder_agent = Agent(
    name="Coder",
    instructions="You are a software engineer. Write clean, production-ready code. Return only code.",
)

tester_agent = Agent(
    name="Tester",
    instructions="You are a test engineer. Write comprehensive tests with edge cases.",
)

reviewer_agent = Agent(
    name="Reviewer",
    instructions="You are a code reviewer. Find bugs, security issues, and suggest improvements.",
)

supervisor_agent = Agent(
    name="Supervisor",
    instructions=(
        "You are a technical lead. Analyze the task and delegate:\n"
        "- Code writing tasks -> Coder\n"
        "- Test writing tasks -> Tester\n"
        "- Code review tasks -> Reviewer\n"
        "Synthesize the worker's output into a final response."
    ),
    handoffs=[
        handoff(agent=coder_agent),
        handoff(agent=tester_agent),
        handoff(agent=reviewer_agent),
    ],
)


async def run_supervised(task: str) -> str:
    """Run a task through the supervisor-worker pipeline."""
    result = await Runner.run(supervisor_agent, task)
    return result.final_output
