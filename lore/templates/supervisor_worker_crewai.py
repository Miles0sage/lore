# LORE SCAFFOLD: supervisor_worker (CrewAI variant)
"""
Supervisor-Worker as a CrewAI Crew.

The supervisor is a manager agent, workers are specialist agents.
Tasks flow through a hierarchical process.
"""

from __future__ import annotations

from crewai import Agent, Task, Crew, Process


def build_supervisor_crew(task_description: str) -> Crew:
    """Build a supervisor-worker crew for a given task."""

    supervisor = Agent(
        role="Technical Lead",
        goal="Decompose tasks and ensure quality of worker outputs",
        backstory="Senior engineer who coordinates specialist workers",
        allow_delegation=True,
        verbose=True,
    )

    coder = Agent(
        role="Software Engineer",
        goal="Write clean, production-ready code",
        backstory="Expert programmer focused on correctness and readability",
        allow_delegation=False,
    )

    reviewer = Agent(
        role="Code Reviewer",
        goal="Find bugs, security issues, and style problems",
        backstory="Meticulous reviewer who catches what others miss",
        allow_delegation=False,
    )

    implement_task = Task(
        description=f"Implement the following: {task_description}",
        expected_output="Production-ready code with comments",
        agent=coder,
    )

    review_task = Task(
        description="Review the implementation for bugs, security issues, and style",
        expected_output="Review report with severity ratings",
        agent=reviewer,
    )

    crew = Crew(
        agents=[supervisor, coder, reviewer],
        tasks=[implement_task, review_task],
        process=Process.hierarchical,
        manager_agent=supervisor,
        verbose=True,
    )

    return crew


# Usage:
# crew = build_supervisor_crew("Build a user authentication module")
# result = crew.kickoff()
