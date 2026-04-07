"""
Supervisor-Worker Pattern — The Commander, Orchestrator of Armies

Central supervisor dispatches tasks to specialist workers, monitors
outputs, handles failures, and synthesizes results.

Single point of failure — when The Commander falls, the army is leaderless.
Use for complex multi-stream workflows requiring synthesis.

Usage:
    orchestrator = SupervisorOrchestrator()
    result = await orchestrator.run("Write tests for my auth module")
"""

import asyncio
from dataclasses import dataclass
from typing import Any


# Model routing table — cheapest capable model per task type
ROUTING_TABLE: dict[str, str] = {
    "test_writing":  "qwen/qwen3.6-plus:free",
    "boilerplate":   "qwen/qwen3.6-plus:free",
    "docs":          "qwen/qwen3.6-plus:free",
    "review":        "moonshotai/kimi-k2.5",
    "bug_fix":       "moonshotai/kimi-k2.5",
    "feature":       "moonshotai/kimi-k2.5",
    "research":      "moonshotai/kimi-k2.5",
    "architecture":  "claude-sonnet-4-6",
    "security":      "claude-sonnet-4-6",
    "refactor":      "moonshotai/kimi-k2.5",
}

TASK_KEYWORDS: dict[str, list[str]] = {
    "test_writing":  ["test", "pytest", "spec", "coverage"],
    "boilerplate":   ["crud", "scaffold", "boilerplate", "generate"],
    "docs":          ["docstring", "readme", "comment", "documentation"],
    "security":      ["security", "auth", "vulnerability", "injection"],
    "architecture":  ["architecture", "design", "system", "migration"],
    "bug_fix":       ["bug", "fix", "error", "broken", "failing"],
    "review":        ["review", "check", "audit", "inspect"],
    "research":      ["research", "find", "search", "what is"],
}


@dataclass
class WorkerResult:
    task_type: str
    model: str
    output: str
    success: bool
    error: str = ""


class SupervisorOrchestrator:
    def __init__(self, supervisor_model: str = "claude-sonnet-4-6"):
        self.supervisor_model = supervisor_model

    def classify_task(self, task: str) -> str:
        """Supervisor classifies task to determine which worker handles it."""
        t = task.lower()
        for task_type, keywords in TASK_KEYWORDS.items():
            if any(kw in t for kw in keywords):
                return task_type
        return "feature"

    async def _call_worker(self, model: str, task: str, task_type: str) -> WorkerResult:
        """Dispatch to worker model via OpenRouter. Replace with actual LLM call."""
        # Replace with actual call:
        # from openai import AsyncOpenAI
        # client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
        # response = await client.chat.completions.create(
        #     model=model,
        #     messages=[
        #         {"role": "system", "content": f"You are an expert at {task_type}. Be precise and production-ready."},
        #         {"role": "user", "content": task}
        #     ]
        # )
        # return WorkerResult(task_type=task_type, model=model, output=response.choices[0].message.content, success=True)
        raise NotImplementedError("Replace with actual OpenRouter/Anthropic call")

    async def run(self, task: str, task_type: str | None = None) -> WorkerResult:
        """Run task through supervisor → worker pipeline."""
        resolved_type = task_type or self.classify_task(task)
        model = ROUTING_TABLE.get(resolved_type, "moonshotai/kimi-k2.5")

        try:
            result = await self._call_worker(model, task, resolved_type)
            return result
        except Exception as e:
            # Escalate to supervisor model on worker failure
            if model != self.supervisor_model:
                return await self._call_worker(self.supervisor_model, task, resolved_type)
            return WorkerResult(task_type=resolved_type, model=model, output="", success=False, error=str(e))
