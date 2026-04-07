# LORE SCAFFOLD: handoff_pattern (CrewAI variant)
"""
Handoff Pattern as a CrewAI Crew.

Agents hand off work in sequence — each agent's output becomes
the next agent's input. Clean stage boundaries.
"""

from __future__ import annotations

from crewai import Agent, Task, Crew, Process


def build_handoff_crew(initial_task: str) -> Crew:
    """Build a handoff pipeline crew."""

    planner = Agent(
        role="Planner",
        goal="Create a detailed implementation plan from requirements",
        backstory="Architect who breaks down complex tasks into clear steps",
        allow_delegation=False,
    )

    implementer = Agent(
        role="Implementer",
        goal="Execute the plan and produce working code",
        backstory="Senior developer who follows plans precisely",
        allow_delegation=False,
    )

    validator = Agent(
        role="Validator",
        goal="Verify the implementation matches the plan and requirements",
        backstory="QA engineer who validates correctness and completeness",
        allow_delegation=False,
    )

    plan_task = Task(
        description=f"Create implementation plan for: {initial_task}",
        expected_output="Step-by-step plan with acceptance criteria",
        agent=planner,
    )

    implement_task = Task(
        description="Implement according to the plan from the previous step",
        expected_output="Working implementation with tests",
        agent=implementer,
        context=[plan_task],
    )

    validate_task = Task(
        description="Validate the implementation against the plan",
        expected_output="Validation report: pass/fail with details",
        agent=validator,
        context=[plan_task, implement_task],
    )

    crew = Crew(
        agents=[planner, implementer, validator],
        tasks=[plan_task, implement_task, validate_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew
