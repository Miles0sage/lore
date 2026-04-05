"""
LORE Scaffold — Production-ready code templates for AI agent patterns.

Each template is a complete, runnable Python file that implements
the pattern described by the corresponding Codex archetype.

Usage via MCP: lore_scaffold circuit_breaker --output-dir ./src
Usage directly: from lore.scaffold import get_template; print(get_template("circuit_breaker"))
"""

TEMPLATES: dict[str, str] = {}

TEMPLATES["circuit_breaker"] = '''"""
Circuit Breaker Pattern — The Breaker, Guardian of the Gate

Prevents cascading failures by monitoring request success rates and
interrupting traffic to failing components. Three states: CLOSED (normal),
OPEN (gate sealed), HALF_OPEN (single probe to test recovery).

Systems without circuit breakers experience 76% failure rates in production.

Usage:
    breaker = CircuitBreaker(name="openrouter_api")
    result = await breaker.call(my_api_function, arg1, arg2)
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class CircuitState(Enum):
    CLOSED = "CLOSED"       # Normal operation, requests flow freely
    OPEN = "OPEN"           # Gate sealed, returns fallback immediately
    HALF_OPEN = "HALF_OPEN" # Single probe allowed to test recovery


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5          # Failures before opening
    recovery_wait_seconds: float = 30.0  # Wait before HALF_OPEN probe
    success_threshold: int = 1          # Successes in HALF_OPEN to close

    # Internal state
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    consecutive_failures: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    half_open_successes: int = field(default=0, init=False)

    def _should_attempt_reset(self) -> bool:
        return (
            self.state == CircuitState.OPEN
            and time.monotonic() - self.last_failure_time >= self.recovery_wait_seconds
        )

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            if self.half_open_successes >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.consecutive_failures = 0
                self.half_open_successes = 0
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
        self.half_open_successes = 0
        if (
            self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
            and self.consecutive_failures >= self.failure_threshold
        ):
            self.state = CircuitState.OPEN

    async def call(self, fn: Callable, *args: Any, fallback: Any = None, **kwargs: Any) -> Any:
        """Call fn with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                return fallback  # Gate sealed, return fallback immediately

        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "seconds_until_probe": max(
                0,
                self.recovery_wait_seconds - (time.monotonic() - self.last_failure_time)
            ) if self.state == CircuitState.OPEN else 0,
        }


# Global registry for multi-tool agent systems
_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(name: str, **kwargs: Any) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _breakers[name]


async def call_with_breaker(tool_name: str, fn: Callable, *args: Any, fallback: Any = None, **kwargs: Any) -> Any:
    """Convenience wrapper — get or create breaker and call fn."""
    breaker = get_breaker(tool_name)
    return await breaker.call(fn, *args, fallback=fallback, **kwargs)


def health_report() -> list[dict]:
    """Return status of all registered circuit breakers."""
    return [b.status() for b in _breakers.values()]
'''

TEMPLATES["dead_letter_queue"] = '''"""
Dead Letter Queue Pattern — The Archivist, Keeper of Lost Messages

Error-isolation pattern where tasks that fail beyond retry threshold
are routed to a separate queue for inspection, replay, or discard.
Nothing is destroyed. Everything waits to be understood.

Usage:
    result = await process_with_dlq("my_task_id", my_task_data, my_handler_fn)
"""

import asyncio
import json
import time
import traceback
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable


class FailureClass(Enum):
    TRANSIENT = "transient"   # Safe to replay (network timeout, 429)
    PERMANENT = "permanent"   # Cannot succeed without modification
    AMBIGUOUS = "ambiguous"   # Replay once with modified prompt


TRANSIENT_ERRORS = {"TimeoutError", "ConnectionError", "RateLimitError", "429"}
PERMANENT_ERRORS = {"ValidationError", "SchemaError", "ContextLengthError", "MalformedInputError"}


@dataclass
class ErrorEnvelope:
    task_id: str
    original_task: Any
    error_type: str
    error_message: str
    stack_trace: str
    attempt_count: int
    worker_id: str
    timestamp: float = field(default_factory=time.time)
    status: str = "dlq"  # dlq | replayed | resolved | discarded

    def to_dict(self) -> dict:
        d = asdict(self)
        d["original_task"] = json.dumps(self.original_task) if not isinstance(self.original_task, str) else self.original_task
        return d


class DLQConsumer:
    def classify_failure(self, envelope: ErrorEnvelope) -> FailureClass:
        error_type = envelope.error_type
        if any(t in error_type for t in TRANSIENT_ERRORS):
            return FailureClass.TRANSIENT
        if any(t in error_type for t in PERMANENT_ERRORS):
            return FailureClass.PERMANENT
        return FailureClass.AMBIGUOUS

    async def handle(self, envelope: ErrorEnvelope, fn: Callable) -> dict:
        failure_class = self.classify_failure(envelope)
        if failure_class == FailureClass.TRANSIENT:
            # Safe to replay after backoff
            await asyncio.sleep(2 ** envelope.attempt_count)
            return {"action": "replay", "envelope": envelope.to_dict()}
        elif failure_class == FailureClass.PERMANENT:
            # Route to human review
            return {"action": "human_review", "envelope": envelope.to_dict()}
        else:
            # Ambiguous — replay once with note
            return {"action": "replay_once", "envelope": envelope.to_dict()}


# In-memory DLQ (replace with Postgres in production)
class InMemoryDLQ:
    def __init__(self):
        self._queue: list[ErrorEnvelope] = []

    async def push(self, envelope: ErrorEnvelope) -> None:
        self._queue.append(envelope)

    async def pop_all(self) -> list[ErrorEnvelope]:
        items = list(self._queue)
        self._queue.clear()
        return items

    def depth(self) -> int:
        return len(self._queue)


_dlq = InMemoryDLQ()
_consumer = DLQConsumer()


async def process_with_dlq(
    task_id: str,
    task: Any,
    fn: Callable,
    max_retries: int = 3,
    worker_id: str = "default",
) -> Any:
    """Process task with DLQ protection. Failed tasks beyond max_retries go to archive."""
    for attempt in range(max_retries + 1):
        try:
            return await fn(task) if asyncio.iscoroutinefunction(fn) else fn(task)
        except Exception as e:
            if attempt >= max_retries:
                envelope = ErrorEnvelope(
                    task_id=task_id,
                    original_task=task,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    stack_trace=traceback.format_exc(),
                    attempt_count=attempt + 1,
                    worker_id=worker_id,
                )
                await _dlq.push(envelope)
                return None  # Task archived, not lost
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    return None
'''

TEMPLATES["reviewer_loop"] = '''"""
Reviewer Loop Pattern — The Council, Judges of All Output

Quality gate where a generator produces output and a separate reviewer
scores it before acceptance. Iterates up to max_iterations, then
escalates to human if threshold not met.

Cost: 2-3x tokens vs single pass. Worth it for high-stakes output.

Usage:
    loop = ReviewerLoop(generator_model="qwen/qwen3.6-plus:free",
                        reviewer_model="moonshotai/kimi-k2.5")
    result = await loop.run("Write a circuit breaker implementation")
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ReviewResult:
    score: float          # 0.0 to 1.0
    accepted: bool
    feedback: str
    iteration: int
    escalated: bool = False


class ReviewerLoop:
    def __init__(
        self,
        generator_model: str = "moonshotai/kimi-k2.5",
        reviewer_model: str = "moonshotai/kimi-k2.5",
        acceptance_threshold: float = 0.80,
        max_iterations: int = 3,
        escalate_callback: Optional[Callable] = None,
    ):
        self.generator_model = generator_model
        self.reviewer_model = reviewer_model
        self.acceptance_threshold = acceptance_threshold
        self.max_iterations = max_iterations
        self.escalate_callback = escalate_callback

    async def _generate(self, prompt: str, feedback: str = "") -> str:
        """Call generator model. Replace with your LLM client."""
        full_prompt = prompt
        if feedback:
            full_prompt = f"{prompt}\\n\\nPrevious attempt was rejected. Reviewer feedback:\\n{feedback}\\n\\nPlease revise."

        # Replace with actual LLM call:
        # from openai import AsyncOpenAI
        # client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
        # response = await client.chat.completions.create(model=self.generator_model, messages=[{"role": "user", "content": full_prompt}])
        # return response.choices[0].message.content
        raise NotImplementedError("Replace with actual LLM call via OpenRouter or Anthropic SDK")

    async def _review(self, prompt: str, draft: str) -> tuple[float, str]:
        """Score draft 0-1 and return (score, feedback). Replace with your LLM client."""
        review_prompt = (
            f"You are a strict reviewer. Score this output from 0.0 to 1.0 and give specific feedback.\\n\\n"
            f"Original task: {prompt}\\n\\nDraft output:\\n{draft}\\n\\n"
            f"Respond with JSON: {{\\\"score\\\": 0.0-1.0, \\\"feedback\\\": \\\"...\\\"}}"
        )
        # Replace with actual LLM call
        raise NotImplementedError("Replace with actual LLM call")

    async def run(self, prompt: str) -> ReviewResult:
        """Run the full reviewer loop."""
        feedback = ""
        for iteration in range(1, self.max_iterations + 1):
            draft = await self._generate(prompt, feedback)
            score, feedback = await self._review(prompt, draft)

            if score >= self.acceptance_threshold:
                return ReviewResult(
                    score=score,
                    accepted=True,
                    feedback=feedback,
                    iteration=iteration,
                )

        # Max iterations reached — escalate
        if self.escalate_callback:
            await self.escalate_callback(prompt, draft, feedback)

        return ReviewResult(
            score=score,
            accepted=False,
            feedback=feedback,
            iteration=self.max_iterations,
            escalated=True,
        )
'''

TEMPLATES["supervisor_worker"] = '''"""
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
'''

TEMPLATES["tool_health_monitor"] = '''"""
Tool Health Monitor — The Warden, Keeper of the Gates

Tracks per-tool success rates, latency, and error classification.
Feeds signals to circuit breakers and model router.

Usage:
    monitor = ToolHealthMonitor()
    result = await monitor.call("github_api", my_github_fn, arg1)
    print(monitor.health_report())
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolMetrics:
    calls: deque = field(default_factory=lambda: deque(maxlen=100))   # bool: success/fail
    latencies: deque = field(default_factory=lambda: deque(maxlen=100))  # float: seconds
    errors: dict = field(default_factory=lambda: defaultdict(int))
    circuit_state: str = "CLOSED"

    def success_rate(self) -> float:
        if not self.calls:
            return 1.0
        return sum(self.calls) / len(self.calls)

    def p95_latency(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def is_healthy(self, threshold: float = 0.85) -> bool:
        return self.success_rate() >= threshold


class ToolHealthMonitor:
    def __init__(self, alert_threshold: float = 0.85):
        self.metrics: dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self.alert_threshold = alert_threshold

    async def call(self, tool_name: str, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Call fn and track health metrics."""
        start = time.monotonic()
        try:
            result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            self._record(tool_name, success=True, latency=time.monotonic() - start)
            return result
        except Exception as e:
            self._record(tool_name, success=False, latency=time.monotonic() - start, error=type(e).__name__)
            raise

    def _record(self, tool_name: str, success: bool, latency: float, error: str = "") -> None:
        m = self.metrics[tool_name]
        m.calls.append(success)
        m.latencies.append(latency)
        if error:
            m.errors[error] += 1

    def health_report(self) -> list[dict]:
        return [
            {
                "tool": name,
                "success_rate": round(m.success_rate(), 3),
                "p95_latency_ms": round(m.p95_latency() * 1000, 1),
                "circuit_state": m.circuit_state,
                "healthy": m.is_healthy(self.alert_threshold),
                "top_errors": dict(list(m.errors.items())[:3]),
            }
            for name, m in self.metrics.items()
        ]

    def degraded_tools(self) -> list[str]:
        return [name for name, m in self.metrics.items() if not m.is_healthy(self.alert_threshold)]
'''


def get_template(pattern: str) -> str | None:
    """Get scaffold template by pattern name."""
    return TEMPLATES.get(pattern)


def list_patterns() -> list[str]:
    """List all available scaffold patterns."""
    return list(TEMPLATES.keys())
