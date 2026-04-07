# LORE SCAFFOLD: reviewer_loop (CrewAI variant)
"""
Reviewer Loop as a CrewAI Crew.

A generator agent produces output, a reviewer agent scores it.
Uses CrewAI's sequential process with feedback loop.
"""

from __future__ import annotations

from crewai import Agent, Task, Crew, Process


def build_reviewer_crew(prompt: str) -> Crew:
    """Build a reviewer loop crew."""

    generator = Agent(
        role="Content Generator",
        goal="Produce high-quality output that meets the acceptance criteria",
        backstory="Creative agent that iterates based on reviewer feedback",
        allow_delegation=False,
    )

    reviewer = Agent(
        role="Quality Reviewer",
        goal="Score output 0-1 and provide specific, actionable feedback",
        backstory="Strict quality gate that only accepts excellent work",
        allow_delegation=False,
    )

    generate_task = Task(
        description=f"Generate output for: {prompt}",
        expected_output="Complete, high-quality output",
        agent=generator,
    )

    review_task = Task(
        description="Review the output. Score 0.0-1.0. If < 0.8, provide feedback for revision.",
        expected_output="JSON with score and feedback: {score: float, feedback: string}",
        agent=reviewer,
    )

    crew = Crew(
        agents=[generator, reviewer],
        tasks=[generate_task, review_task],
        process=Process.sequential,
        verbose=True,
    )

    return crew
