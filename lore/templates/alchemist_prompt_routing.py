# LORE SCAFFOLD: alchemist_prompt_routing
"""
Alchemist Prompt Routing — The Alchemist, Transformer of Models and Prompts

Prompt optimization and model routing. The Alchemist transmutes raw prompts
into optimized inputs and routes each task to the cheapest capable model.

Usage:
    alchemist = Alchemist()
    alchemist.register_template(PromptTemplate(name="code_review",
        template="Review this {language} code for bugs:\n\n{code}",
        best_models=("claude-sonnet-4-6", "moonshotai/kimi-k2.5")))
    result = alchemist.optimize_prompt("review my python code", {"language": "Python", "code": code})
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PromptTemplate:
    """Immutable prompt template with model affinity."""
    name: str
    template: str
    best_models: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    max_tokens: int = 4000
    temperature: float = 0.7


@dataclass(frozen=True)
class OptimizedPrompt:
    """Immutable result of prompt optimization."""
    original: str
    optimized: str
    template_used: str
    recommended_model: str
    estimated_tokens: int
    variables_filled: dict = field(default_factory=dict)


# Default cost table (per 1K tokens)
MODEL_COSTS: dict[str, float] = {
    "qwen/qwen3.6-plus:free": 0.0,
    "moonshotai/kimi-k2.5": 0.001,
    "claude-sonnet-4-6": 0.003,
    "claude-opus-4-5": 0.015,
}


class Alchemist:
    """Prompt optimizer and model router."""

    def __init__(self):
        self._templates: dict[str, PromptTemplate] = {}

    def register_template(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        self._templates = {**self._templates, template.name: template}

    def _match_template(self, prompt: str) -> PromptTemplate | None:
        """Find best matching template for a prompt."""
        lower = prompt.lower()
        best_match: PromptTemplate | None = None
        best_score = 0

        for tmpl in self._templates.values():
            score = sum(1 for kw in tmpl.keywords if kw in lower)
            if score > best_score:
                best_score = score
                best_match = tmpl

        return best_match

    def optimize_prompt(self, prompt: str, variables: dict | None = None) -> OptimizedPrompt:
        """Optimize a prompt: match template, fill variables, select model."""
        template = self._match_template(prompt)
        filled_vars = dict(variables or {})

        if template:
            optimized = template.template
            for key, value in filled_vars.items():
                optimized = optimized.replace(f"{{{key}}}", str(value))
            model = template.best_models[0] if template.best_models else "moonshotai/kimi-k2.5"
        else:
            optimized = prompt
            model = self.select_model_for_prompt(prompt)

        est_tokens = int(len(optimized.split()) / 0.75)

        return OptimizedPrompt(
            original=prompt,
            optimized=optimized,
            template_used=template.name if template else "none",
            recommended_model=model,
            estimated_tokens=est_tokens,
            variables_filled=filled_vars,
        )

    def select_model_for_prompt(self, prompt: str) -> str:
        """Select cheapest capable model based on prompt complexity."""
        lower = prompt.lower()
        complex_indicators = ("architect", "security", "design", "complex", "critical")
        medium_indicators = ("feature", "review", "bug", "refactor", "implement")

        if any(ind in lower for ind in complex_indicators):
            return "claude-sonnet-4-6"
        if any(ind in lower for ind in medium_indicators):
            return "moonshotai/kimi-k2.5"
        return "qwen/qwen3.6-plus:free"

    def estimate_cost(self, prompt: str, model: str) -> float:
        """Estimate cost for a prompt with given model."""
        tokens = len(prompt.split()) / 0.75
        cost_per_1k = MODEL_COSTS.get(model, 0.003)
        return (tokens / 1000) * cost_per_1k
