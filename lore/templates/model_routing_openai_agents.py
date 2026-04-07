# LORE SCAFFOLD: model_routing (OpenAI Agents SDK variant)
"""
Model Routing using OpenAI Agents SDK.

A triage agent classifies tasks and hands off to the appropriate
specialist agent, each configured with a different model.
"""

from __future__ import annotations

from agents import Agent, Runner, handoff


simple_agent = Agent(
    name="SimpleWorker",
    instructions="You handle simple tasks: boilerplate, CRUD, tests, docs. Be concise and fast.",
    model="gpt-4o-mini",
)

standard_agent = Agent(
    name="StandardWorker",
    instructions="You handle medium-complexity tasks: features, bug fixes, refactoring. Be thorough.",
    model="gpt-4o",
)

complex_agent = Agent(
    name="ComplexWorker",
    instructions="You handle complex tasks: architecture, security, system design. Think deeply.",
    model="o3",
)

triage_agent = Agent(
    name="Triage",
    instructions=(
        "You are a task router. Classify the user's task:\n"
        "- Simple (tests, docs, boilerplate) -> hand off to SimpleWorker\n"
        "- Standard (features, bugs, refactoring) -> hand off to StandardWorker\n"
        "- Complex (architecture, security, design) -> hand off to ComplexWorker"
    ),
    handoffs=[
        handoff(agent=simple_agent),
        handoff(agent=standard_agent),
        handoff(agent=complex_agent),
    ],
)


async def route_task(task: str) -> str:
    """Route a task through the triage agent."""
    result = await Runner.run(triage_agent, task)
    return result.final_output
