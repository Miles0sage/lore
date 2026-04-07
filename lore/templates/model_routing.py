# LORE SCAFFOLD: model_routing
"""
Model Routing — The Router, Arbiter of Intelligence

Dynamic model selection based on task complexity. The Router decides which
mind handles each task — cheap models for boilerplate, expensive models for
architecture. Escalates when cheaper models fail.

Usage:
    router = ModelRouter()
    result = await router.route_and_dispatch("Write unit tests for auth module")
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class LLMClient(Protocol):
    """Protocol for LLM API clients."""
    async def complete(self, model: str, prompt: str) -> str: ...


@dataclass(frozen=True)
class ModelProfile:
    """Immutable profile for a model in the routing table."""
    name: str
    cost_per_1k_tokens: float
    max_context: int = 128_000
    strengths: tuple[str, ...] = ()
    tier: int = 1  # 1=cheap, 2=mid, 3=expensive


# Default routing table — override for your stack
DEFAULT_PROFILES: tuple[ModelProfile, ...] = (
    ModelProfile("qwen/qwen3.6-plus:free", 0.0, 32_000, ("boilerplate", "tests", "docs"), 1),
    ModelProfile("moonshotai/kimi-k2.5", 0.001, 128_000, ("features", "review", "bugs"), 2),
    ModelProfile("claude-sonnet-4-6", 0.003, 200_000, ("architecture", "security", "complex"), 3),
)

COMPLEXITY_KEYWORDS: dict[str, int] = {
    "test": 1, "crud": 1, "boilerplate": 1, "docs": 1, "comment": 1,
    "feature": 2, "bug": 2, "fix": 2, "review": 2, "refactor": 2,
    "architecture": 3, "security": 3, "design": 3, "migration": 3, "debug": 3,
}


def classify_task(task: str) -> int:
    """Classify task complexity: 1=simple, 2=medium, 3=complex."""
    lower = task.lower()
    scores = [tier for kw, tier in COMPLEXITY_KEYWORDS.items() if kw in lower]
    return max(scores) if scores else 2


def select_model(task: str, profiles: tuple[ModelProfile, ...] = DEFAULT_PROFILES) -> ModelProfile:
    """Select the cheapest model capable of handling the task."""
    tier = classify_task(task)
    candidates = [p for p in profiles if p.tier >= tier]
    if not candidates:
        return profiles[-1]  # fallback to most capable
    return min(candidates, key=lambda p: p.cost_per_1k_tokens)


class ModelRouter:
    def __init__(
        self,
        profiles: tuple[ModelProfile, ...] = DEFAULT_PROFILES,
        client: LLMClient | None = None,
    ):
        self.profiles = profiles
        self.client = client

    async def route_and_dispatch(self, task: str) -> dict:
        """Classify task, select model, and dispatch. Escalate on failure."""
        selected = select_model(task, self.profiles)

        for profile in sorted(self.profiles, key=lambda p: p.tier):
            if profile.tier < selected.tier:
                continue
            try:
                if self.client:
                    result = await self.client.complete(profile.name, task)
                else:
                    raise NotImplementedError("Provide an LLMClient implementation")
                return {"model": profile.name, "tier": profile.tier, "result": result, "escalated": profile != selected}
            except Exception:
                continue  # escalate to next tier

        return {"model": "none", "tier": 0, "result": None, "error": "All models failed"}
