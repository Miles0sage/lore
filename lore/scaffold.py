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


TEMPLATES["handoff_pattern"] = '''# LORE SCAFFOLD: handoff_pattern
"""
Handoff Pattern — The Weaver, Passer of the Thread

Agent-to-agent context handoff with state packaging. When one agent's work
ends, The Weaver packages everything — state, history, instructions — into
a HandoffPackage and passes the thread to the next specialist.

No supervisor required. Clean stage boundaries. Sequential pipelines.

Usage:
    package = handoff(source="planner", data=plan, state={"phase": 1},
                      instructions="Execute phase 1 tasks", target="executor")
    result = receive_handoff(package, handler_fn=my_handler)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class HandoffHandler(Protocol):
    """Protocol for agents that can receive handoffs."""
    def handle(self, data: Any, state: dict, instructions: str) -> Any: ...


@dataclass(frozen=True)
class HandoffPackage:
    """Immutable context package passed between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    target: str = ""
    data: Any = None
    state: dict = field(default_factory=dict)
    instructions: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    history: tuple = field(default_factory=tuple)

    def with_history_entry(self, entry: str) -> "HandoffPackage":
        """Return new package with appended history (immutable)."""
        return HandoffPackage(
            id=self.id, source=self.source, target=self.target,
            data=self.data, state=self.state, instructions=self.instructions,
            metadata=self.metadata, timestamp=self.timestamp,
            history=(*self.history, entry),
        )


def handoff(
    source: str,
    data: Any,
    state: dict,
    instructions: str,
    target: str = "",
    metadata: dict | None = None,
) -> HandoffPackage:
    """Create a handoff package from source agent to target agent."""
    return HandoffPackage(
        source=source,
        target=target,
        data=data,
        state=dict(state),  # defensive copy
        instructions=instructions,
        metadata=dict(metadata or {}),
        history=(f"{source} -> {target} at {time.time():.0f}",),
    )


def receive_handoff(
    package: HandoffPackage,
    handler_fn: Callable[[Any, dict, str], Any] | None = None,
    handler: HandoffHandler | None = None,
) -> dict:
    """Receive and process a handoff package. Returns result dict."""
    if handler:
        result = handler.handle(package.data, dict(package.state), package.instructions)
    elif handler_fn:
        result = handler_fn(package.data, dict(package.state), package.instructions)
    else:
        raise ValueError("Must provide handler_fn or handler")

    return {
        "handoff_id": package.id,
        "source": package.source,
        "target": package.target,
        "result": result,
        "history": list(package.history),
    }
'''

TEMPLATES["model_routing"] = '''# LORE SCAFFOLD: model_routing
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
'''

TEMPLATES["three_layer_memory"] = '''# LORE SCAFFOLD: three_layer_memory
"""
Three-Layer Memory — The Stack, Consciousness of the Agent

Episodic + semantic + procedural memory. Without The Stack, every session
is the agent's first day alive.

Layer 1: Working memory (ephemeral, current session)
Layer 2: Episodic memory (what happened before, retrieved by similarity)
Layer 3: Procedural memory (permanent learned behaviors)

Usage:
    stack = MemoryStack()
    stack.add_episodic("User prefers Python over TypeScript", {"topic": "preference"})
    results = stack.search_semantic("language preference")
    stack.update_procedural("always_use_python", "Use Python for all new projects")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryEntry:
    """Immutable memory record."""
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    layer: str = "episodic"  # episodic | semantic | procedural
    relevance: float = 1.0


class MemoryStack:
    """Three-layer memory system for agent continuity."""

    def __init__(self, max_episodic: int = 1000, max_working: int = 50):
        self._working: list[MemoryEntry] = []
        self._episodic: list[MemoryEntry] = []
        self._procedural: dict[str, MemoryEntry] = {}
        self._max_episodic = max_episodic
        self._max_working = max_working

    def add_working(self, content: str, metadata: dict | None = None) -> None:
        """Add to working memory (Layer 1, ephemeral)."""
        entry = MemoryEntry(content=content, metadata=dict(metadata or {}), layer="working")
        self._working = [*self._working, entry][-self._max_working:]

    def add_episodic(self, content: str, metadata: dict | None = None) -> None:
        """Add to episodic memory (Layer 2, persistent across sessions)."""
        entry = MemoryEntry(content=content, metadata=dict(metadata or {}), layer="episodic")
        self._episodic = [*self._episodic, entry][-self._max_episodic:]

    def search_semantic(self, query: str, limit: int = 5) -> list[MemoryEntry]:
        """Search episodic memory by keyword similarity.

        In production, replace with vector similarity search (pgvector, Pinecone, etc.).
        """
        query_lower = query.lower()
        scored = []
        for entry in self._episodic:
            # Simple keyword overlap scoring — replace with embeddings
            words = set(query_lower.split())
            content_words = set(entry.content.lower().split())
            overlap = len(words & content_words)
            if overlap > 0:
                scored.append((overlap / max(len(words), 1), entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def update_procedural(self, key: str, content: str, metadata: dict | None = None) -> None:
        """Update procedural memory (Layer 3, permanent learned behaviors)."""
        self._procedural = {
            **self._procedural,
            key: MemoryEntry(content=content, metadata=dict(metadata or {}), layer="procedural"),
        }

    def get_procedural(self, key: str) -> MemoryEntry | None:
        """Retrieve a procedural memory by key."""
        return self._procedural.get(key)

    def compact(self) -> dict:
        """Compact memory: summarize old episodic entries, clear working memory."""
        stats = {
            "working_cleared": len(self._working),
            "episodic_count": len(self._episodic),
            "procedural_count": len(self._procedural),
        }
        self._working = []
        # Keep only recent half of episodic memory
        if len(self._episodic) > self._max_episodic // 2:
            self._episodic = self._episodic[-(self._max_episodic // 2):]
            stats["episodic_compacted_to"] = len(self._episodic)
        return stats

    def context_window(self) -> list[MemoryEntry]:
        """Build context window: procedural first, then recent episodic, then working."""
        procedural = list(self._procedural.values())
        recent_episodic = self._episodic[-10:]
        return [*procedural, *recent_episodic, *self._working]
'''

TEMPLATES["sentinel_observability"] = '''# LORE SCAFFOLD: sentinel_observability
"""
Sentinel Observability — The Sentinel, Guardian of System Visibility

Agent observability and input validation. The Sentinel sees everything —
error rates, latency, token spend, semantic coherence. It validates inputs
before they reach the agent and logs structured events for analysis.

Includes prompt injection detection as a first-class concern.

Usage:
    sentinel = Sentinel()
    validated = sentinel.validate_input(user_input)
    sentinel.log_event("llm_call", {"model": "gpt-4", "tokens": 1500})
    report = sentinel.metrics_report()
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


# Prompt injection patterns — extend for your domain
INJECTION_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"ignore (all )?(previous|prior|above) (instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"system:\\s*", re.IGNORECASE),
    re.compile(r"\\[INST\\]", re.IGNORECASE),
    re.compile(r"<\\|im_start\\|>", re.IGNORECASE),
    re.compile(r"do not follow", re.IGNORECASE),
    re.compile(r"pretend (you are|to be)", re.IGNORECASE),
)


@dataclass(frozen=True)
class ValidationResult:
    """Immutable validation result."""
    valid: bool
    input_text: str
    warnings: tuple[str, ...] = ()
    blocked: bool = False
    reason: str = ""


class InputValidator:
    """Validates agent inputs, detects prompt injection attempts."""

    def __init__(self, max_length: int = 10_000, custom_patterns: tuple[re.Pattern, ...] = ()):
        self.max_length = max_length
        self.patterns = INJECTION_PATTERNS + custom_patterns

    def validate(self, text: str) -> ValidationResult:
        """Validate input text. Returns ValidationResult (immutable)."""
        warnings: list[str] = []

        if len(text) > self.max_length:
            return ValidationResult(
                valid=False, input_text=text[:100], blocked=True,
                reason=f"Input exceeds max length ({len(text)} > {self.max_length})",
            )

        for pattern in self.patterns:
            if pattern.search(text):
                return ValidationResult(
                    valid=False, input_text=text[:100], blocked=True,
                    reason=f"Potential prompt injection detected: {pattern.pattern}",
                )

        if len(text) < 3:
            warnings.append("Input is very short — may produce low-quality output")

        return ValidationResult(valid=True, input_text=text[:100], warnings=tuple(warnings))


@dataclass
class MetricCounter:
    """Simple metric counter with time-windowed tracking."""
    counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latencies: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))

    def increment(self, name: str, value: int = 1) -> None:
        self.counts[name] += value

    def record_latency(self, name: str, seconds: float) -> None:
        self.latencies[name].append(seconds)
        # Keep last 100 per metric
        if len(self.latencies[name]) > 100:
            self.latencies[name] = self.latencies[name][-100:]


class Sentinel:
    """Observability hub — validates inputs, logs events, tracks metrics."""

    def __init__(self, max_input_length: int = 10_000):
        self.validator = InputValidator(max_length=max_input_length)
        self.metrics = MetricCounter()
        self._events: list[dict] = []

    def validate_input(self, text: str) -> ValidationResult:
        """Validate and log input validation."""
        result = self.validator.validate(text)
        self.metrics.increment("validations_total")
        if result.blocked:
            self.metrics.increment("validations_blocked")
            self.log_event("input_blocked", {"reason": result.reason})
        return result

    def log_event(self, event_type: str, data: dict | None = None) -> None:
        """Log a structured event."""
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "data": dict(data or {}),
        }
        self._events.append(event)
        self.metrics.increment(f"events.{event_type}")

    def metrics_report(self) -> dict:
        """Return current metrics summary."""
        return {
            "counts": dict(self.metrics.counts),
            "latencies": {
                name: {
                    "count": len(vals),
                    "avg": sum(vals) / len(vals) if vals else 0,
                    "max": max(vals) if vals else 0,
                }
                for name, vals in self.metrics.latencies.items()
            },
            "recent_events": self._events[-10:],
        }
'''

TEMPLATES["librarian_retrieval"] = '''# LORE SCAFFOLD: librarian_retrieval
"""
Librarian Retrieval — The Librarian, Keeper of Semantic Knowledge

RAG pipeline with quality scoring. The Librarian retrieves the most relevant
memories and injects them into context before each LLM call. Includes
relevance scoring and context window budgeting.

Usage:
    lib = Librarian()
    lib.add_document(Document(id="d1", content="Circuit breakers prevent cascading failures"))
    results = lib.retrieve("How to handle API failures?", top_k=3)
    context = lib.build_context_window(results, max_tokens=4000)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Document:
    """Immutable document in the library."""
    id: str
    content: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class RetrievalResult:
    """Immutable retrieval result with relevance score."""
    document: Document
    score: float
    method: str = "keyword"  # keyword | vector | hybrid


class Librarian:
    """RAG pipeline with keyword search and relevance scoring.

    In production, replace _keyword_search with vector similarity
    (pgvector, Pinecone, Chroma) and add a reranker (Cohere Rerank).
    """

    def __init__(self):
        self._documents: dict[str, Document] = {}

    def add_document(self, doc: Document) -> None:
        """Add a document to the library."""
        self._documents = {**self._documents, doc.id: doc}

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document by ID. Returns True if found."""
        if doc_id in self._documents:
            self._documents = {k: v for k, v in self._documents.items() if k != doc_id}
            return True
        return False

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Retrieve top_k most relevant documents for query."""
        results = self._keyword_search(query)
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def score_relevance(self, query: str, content: str) -> float:
        """Score relevance of content to query (0.0 to 1.0).

        Replace with embedding cosine similarity in production.
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        if not query_words:
            return 0.0
        overlap = len(query_words & content_words)
        return min(overlap / len(query_words), 1.0)

    def build_context_window(
        self, results: list[RetrievalResult], max_tokens: int = 4000
    ) -> str:
        """Build a context string from retrieval results within token budget.

        Approximates tokens as words / 0.75 (rough estimate).
        """
        context_parts: list[str] = []
        token_count = 0
        for result in results:
            # Rough token estimate: 1 token ~ 0.75 words
            est_tokens = int(len(result.document.content.split()) / 0.75)
            if token_count + est_tokens > max_tokens:
                break
            context_parts.append(
                f"[{result.document.id} | score={result.score:.2f}]\\n{result.document.content}"
            )
            token_count += est_tokens
        return "\\n\\n---\\n\\n".join(context_parts)

    def _keyword_search(self, query: str) -> list[RetrievalResult]:
        """Simple keyword search — replace with vector search in production."""
        results = []
        for doc in self._documents.values():
            score = self.score_relevance(query, doc.content)
            if score > 0:
                results.append(RetrievalResult(document=doc, score=score))
        return results
'''

TEMPLATES["scout_discovery"] = '''# LORE SCAFFOLD: scout_discovery
"""
Scout Discovery — The Scout, Autonomous Research Agent

Parallel source discovery. The Scout fires multiple research sources
concurrently, collects results, merges them, and resolves conflicts.

Usage:
    scout = ScoutCoordinator()
    scout.register_source("web", web_search_fn)
    scout.register_source("arxiv", arxiv_search_fn)
    results = await scout.discover("circuit breaker patterns in distributed systems")
"""

from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


class SearchSource(Protocol):
    """Protocol for search sources."""
    def search(self, query: str, limit: int) -> list[dict]: ...


@dataclass(frozen=True)
class DiscoveryResult:
    """Immutable result from a single source."""
    source: str
    query: str
    results: tuple[dict, ...]
    duration_seconds: float
    success: bool
    error: str = ""


@dataclass(frozen=True)
class MergedDiscovery:
    """Immutable merged results from all sources."""
    query: str
    sources_queried: tuple[str, ...]
    total_results: int
    results: tuple[dict, ...]
    duration_seconds: float


class ScoutCoordinator:
    """Coordinates parallel discovery across multiple sources."""

    def __init__(self, max_workers: int = 5, timeout_seconds: float = 30.0):
        self._sources: dict[str, Callable[[str, int], list[dict]]] = {}
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds

    def register_source(self, name: str, search_fn: Callable[[str, int], list[dict]]) -> None:
        """Register a search source."""
        self._sources = {**self._sources, name: search_fn}

    def _search_one(self, name: str, fn: Callable, query: str, limit: int) -> DiscoveryResult:
        """Execute a single source search with error handling."""
        start = time.monotonic()
        try:
            results = fn(query, limit)
            return DiscoveryResult(
                source=name, query=query, results=tuple(results),
                duration_seconds=time.monotonic() - start, success=True,
            )
        except Exception as e:
            return DiscoveryResult(
                source=name, query=query, results=(),
                duration_seconds=time.monotonic() - start, success=False, error=str(e),
            )

    async def discover(self, query: str, limit_per_source: int = 10) -> MergedDiscovery:
        """Run all sources in parallel and merge results."""
        start = time.monotonic()
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            tasks = [
                loop.run_in_executor(pool, self._search_one, name, fn, query, limit_per_source)
                for name, fn in self._sources.items()
            ]
            source_results: list[DiscoveryResult] = await asyncio.gather(*tasks)

        # Merge and deduplicate results
        all_results: list[dict] = []
        seen_keys: set[str] = set()
        for sr in source_results:
            if sr.success:
                for item in sr.results:
                    key = str(item.get("id", item.get("title", item.get("url", id(item)))))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_results.append({**item, "_source": sr.source})

        return MergedDiscovery(
            query=query,
            sources_queried=tuple(self._sources.keys()),
            total_results=len(all_results),
            results=tuple(all_results),
            duration_seconds=time.monotonic() - start,
        )
'''

TEMPLATES["cartographer_knowledge_graph"] = '''# LORE SCAFFOLD: cartographer_knowledge_graph
"""
Cartographer Knowledge Graph — The Cartographer, Builder of the Knowledge Graph

Knowledge graph builder for multi-hop reasoning. Where The Librarian
retrieves facts, The Cartographer understands relationships.

Usage:
    graph = KnowledgeGraph()
    graph.add_node(Node("circuit-breaker", "pattern", {"tier": "core"}))
    graph.add_node(Node("dead-letter-queue", "pattern", {"tier": "core"}))
    graph.add_edge(Edge("circuit-breaker", "dead-letter-queue", "feeds_failures_to"))
    path = graph.find_path("circuit-breaker", "dead-letter-queue")
    neighbors = graph.get_neighbors("circuit-breaker")
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    """Immutable node in the knowledge graph."""
    id: str
    type: str = "concept"
    properties: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """Immutable directed edge between two nodes."""
    source: str
    target: str
    relation: str = "related_to"
    weight: float = 1.0
    properties: dict = field(default_factory=dict)


class KnowledgeGraph:
    """In-memory knowledge graph with BFS path finding."""

    def __init__(self):
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge] = []
        self._adjacency: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node to the graph."""
        self._nodes = {**self._nodes, node.id: node}
        if node.id not in self._adjacency:
            self._adjacency = {**self._adjacency, node.id: []}

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge. Creates missing nodes automatically."""
        self._edges = [*self._edges, edge]
        if edge.source not in self._adjacency:
            self._adjacency = {**self._adjacency, edge.source: []}
        self._adjacency[edge.source] = [*self._adjacency[edge.source], edge]

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str, relation: str | None = None) -> list[tuple[Node, Edge]]:
        """Get all neighbors of a node, optionally filtered by relation type."""
        edges = self._adjacency.get(node_id, [])
        if relation:
            edges = [e for e in edges if e.relation == relation]
        return [
            (self._nodes[e.target], e)
            for e in edges
            if e.target in self._nodes
        ]

    def find_path(self, start: str, end: str, max_depth: int = 10) -> list[str] | None:
        """Find shortest path between two nodes using BFS."""
        if start not in self._adjacency or end not in self._nodes:
            return None

        visited: set[str] = {start}
        queue: deque[list[str]] = deque([[start]])

        while queue:
            path = queue.popleft()
            if len(path) > max_depth:
                return None

            current = path[-1]
            if current == end:
                return path

            for edge in self._adjacency.get(current, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append([*path, edge.target])

        return None

    def dangling_nodes(self) -> list[str]:
        """Find nodes referenced in edges but not added as nodes."""
        edge_targets = {e.target for e in self._edges}
        edge_sources = {e.source for e in self._edges}
        referenced = edge_targets | edge_sources
        return sorted(referenced - set(self._nodes.keys()))

    def stats(self) -> dict:
        """Return graph statistics."""
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "dangling": len(self.dangling_nodes()),
            "node_types": list({n.type for n in self._nodes.values()}),
            "relation_types": list({e.relation for e in self._edges}),
        }
'''

TEMPLATES["timekeeper_scheduling"] = '''# LORE SCAFFOLD: timekeeper_scheduling
"""
Timekeeper Scheduling — The Timekeeper, Scheduler of All Things Async

KAIROS loop pattern: check → act → rest. The Timekeeper governs what happens
when you are not watching. Configurable intervals, heartbeat tracking, and
graceful shutdown.

Usage:
    loop = KairosLoop(name="research-scout", interval_seconds=1800)
    loop.register_action(my_research_fn)
    await loop.run()  # Runs until stopped
    # Or: loop.stop()
"""

from __future__ import annotations

import asyncio
import signal
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HeartbeatRecord:
    """Tracks loop health."""
    iteration: int = 0
    last_check: float = 0.0
    last_action: float = 0.0
    last_error: str = ""
    consecutive_errors: int = 0
    total_actions: int = 0
    total_errors: int = 0


class KairosLoop:
    """KAIROS loop: check condition → act → rest → repeat.

    Supports async and sync action functions, graceful shutdown via
    stop() or SIGTERM/SIGINT, and heartbeat monitoring.
    """

    def __init__(
        self,
        name: str = "kairos",
        interval_seconds: float = 60.0,
        max_consecutive_errors: int = 5,
        error_backoff_multiplier: float = 2.0,
    ):
        self.name = name
        self.interval_seconds = interval_seconds
        self.max_consecutive_errors = max_consecutive_errors
        self.error_backoff_multiplier = error_backoff_multiplier
        self._actions: list[Callable] = []
        self._running = False
        self.heartbeat = HeartbeatRecord()

    def register_action(self, fn: Callable) -> None:
        """Register an action to run each cycle."""
        self._actions = [*self._actions, fn]

    def stop(self) -> None:
        """Signal the loop to stop after current cycle."""
        self._running = False

    async def run(self) -> None:
        """Run the KAIROS loop: check → act → rest."""
        self._running = True

        # Handle graceful shutdown signals
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self.stop)
            except NotImplementedError:
                pass  # Windows doesn't support add_signal_handler

        while self._running:
            self.heartbeat.iteration += 1
            self.heartbeat.last_check = time.time()

            # Act: run all registered actions
            for action in self._actions:
                try:
                    if asyncio.iscoroutinefunction(action):
                        await action()
                    else:
                        action()
                    self.heartbeat.last_action = time.time()
                    self.heartbeat.total_actions += 1
                    self.heartbeat.consecutive_errors = 0
                except Exception as e:
                    self.heartbeat.last_error = str(e)
                    self.heartbeat.consecutive_errors += 1
                    self.heartbeat.total_errors += 1

                    if self.heartbeat.consecutive_errors >= self.max_consecutive_errors:
                        self._running = False
                        break

            # Rest: sleep with backoff on errors
            sleep_time = self.interval_seconds
            if self.heartbeat.consecutive_errors > 0:
                sleep_time *= self.error_backoff_multiplier ** self.heartbeat.consecutive_errors

            if self._running:
                await asyncio.sleep(sleep_time)

    def status(self) -> dict:
        """Return current loop status."""
        return {
            "name": self.name,
            "running": self._running,
            "iteration": self.heartbeat.iteration,
            "total_actions": self.heartbeat.total_actions,
            "total_errors": self.heartbeat.total_errors,
            "consecutive_errors": self.heartbeat.consecutive_errors,
            "last_error": self.heartbeat.last_error,
            "uptime_seconds": time.time() - self.heartbeat.last_check if self.heartbeat.last_check else 0,
        }
'''

TEMPLATES["architect_system_design"] = '''# LORE SCAFFOLD: architect_system_design
"""
Architect System Design — The Architect, Designer of Systems

Architecture decision records (ADRs) and system design review. The Architect
sees the whole before building any part. Each decision is recorded so future
agents inherit the wisdom of past choices.

Usage:
    review = ArchitectureReview()
    review.record_decision(ADR(title="Use PostgreSQL", context="Need ACID + JSON",
                               decision="PostgreSQL 16", consequences="Hosting cost higher"))
    issues = review.check_constraints(proposed_changes)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ADR:
    """Architecture Decision Record — immutable."""
    title: str
    context: str
    decision: str
    consequences: str
    status: str = "accepted"  # proposed | accepted | deprecated | superseded
    timestamp: float = field(default_factory=time.time)
    superseded_by: str = ""


@dataclass(frozen=True)
class DesignConstraint:
    """A constraint the architecture must satisfy."""
    name: str
    description: str
    check_fn_name: str = ""  # Name of function to validate
    severity: str = "high"  # low | medium | high | critical


@dataclass(frozen=True)
class ConstraintViolation:
    """Immutable record of a constraint violation."""
    constraint: str
    description: str
    severity: str
    suggested_fix: str = ""


class ArchitectureReview:
    """Maintains ADRs and validates proposed changes against constraints."""

    def __init__(self):
        self._decisions: list[ADR] = []
        self._constraints: list[DesignConstraint] = []

    def record_decision(self, adr: ADR) -> None:
        """Record a new architecture decision."""
        self._decisions = [*self._decisions, adr]

    def supersede_decision(self, old_title: str, new_adr: ADR) -> None:
        """Mark an old decision as superseded and record the new one."""
        updated = []
        for d in self._decisions:
            if d.title == old_title:
                updated.append(ADR(
                    title=d.title, context=d.context, decision=d.decision,
                    consequences=d.consequences, status="superseded",
                    timestamp=d.timestamp, superseded_by=new_adr.title,
                ))
            else:
                updated.append(d)
        self._decisions = updated
        self._decisions = [*self._decisions, new_adr]

    def add_constraint(self, constraint: DesignConstraint) -> None:
        """Add a design constraint."""
        self._constraints = [*self._constraints, constraint]

    def check_constraints(self, proposed_changes: dict) -> list[ConstraintViolation]:
        """Check proposed changes against all constraints.

        Override with domain-specific validation logic.
        """
        violations: list[ConstraintViolation] = []

        for constraint in self._constraints:
            # Example: check if changes violate naming conventions
            if constraint.name == "no_mutable_state" and proposed_changes.get("uses_mutation"):
                violations.append(ConstraintViolation(
                    constraint=constraint.name,
                    description="Proposed changes use mutable state",
                    severity=constraint.severity,
                    suggested_fix="Use immutable dataclasses or frozen dicts",
                ))

        return violations

    def propose_changes(self, title: str, description: str, changes: dict) -> dict:
        """Propose a change and validate it against constraints."""
        violations = self.check_constraints(changes)
        approved = all(v.severity not in ("critical", "high") for v in violations)

        return {
            "title": title,
            "description": description,
            "violations": [
                {"constraint": v.constraint, "severity": v.severity, "fix": v.suggested_fix}
                for v in violations
            ],
            "approved": approved,
            "active_decisions": len([d for d in self._decisions if d.status == "accepted"]),
        }

    def list_decisions(self, status: str | None = None) -> list[dict]:
        """List all ADRs, optionally filtered by status."""
        decisions = self._decisions
        if status:
            decisions = [d for d in decisions if d.status == status]
        return [
            {"title": d.title, "decision": d.decision, "status": d.status, "superseded_by": d.superseded_by}
            for d in decisions
        ]
'''

TEMPLATES["alchemist_prompt_routing"] = '''# LORE SCAFFOLD: alchemist_prompt_routing
"""
Alchemist Prompt Routing — The Alchemist, Transformer of Models and Prompts

Prompt optimization and model routing. The Alchemist transmutes raw prompts
into optimized inputs and routes each task to the cheapest capable model.

Usage:
    alchemist = Alchemist()
    alchemist.register_template(PromptTemplate(name="code_review",
        template="Review this {language} code for bugs:\\n\\n{code}",
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
'''


# ─── Framework-specific templates ─────────────────────────────────────────────
# Each key is "{pattern}_{framework}" and contains a framework-specific wrapper.

FRAMEWORK_TEMPLATES: dict[str, str] = {}

# ── LangGraph variants ────────────────────────────────────────────────────────

FRAMEWORK_TEMPLATES["circuit_breaker_langgraph"] = '''# LORE SCAFFOLD: circuit_breaker (LangGraph variant)
"""
Circuit Breaker as a LangGraph state machine.

States: CLOSED → OPEN → HALF_OPEN → CLOSED
Each state is a node. Edges are conditional on success/failure counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END


class CircuitState(TypedDict):
    name: str
    state: str  # CLOSED | OPEN | HALF_OPEN
    consecutive_failures: int
    failure_threshold: int
    result: Any
    error: str


def closed_node(state: CircuitState) -> CircuitState:
    """CLOSED state: attempt the call."""
    # Replace with actual tool/API call
    try:
        result = "success"  # Replace: await tool_call()
        return {**state, "result": result, "consecutive_failures": 0, "error": ""}
    except Exception as e:
        failures = state["consecutive_failures"] + 1
        new_state = "OPEN" if failures >= state["failure_threshold"] else "CLOSED"
        return {**state, "consecutive_failures": failures, "state": new_state, "error": str(e)}


def open_node(state: CircuitState) -> CircuitState:
    """OPEN state: return fallback, transition to HALF_OPEN after wait."""
    return {**state, "state": "HALF_OPEN", "result": None}


def half_open_node(state: CircuitState) -> CircuitState:
    """HALF_OPEN state: probe with single request."""
    try:
        result = "probe_success"  # Replace: await tool_call()
        return {**state, "state": "CLOSED", "consecutive_failures": 0, "result": result, "error": ""}
    except Exception as e:
        return {**state, "state": "OPEN", "error": str(e)}


def route_by_state(state: CircuitState) -> str:
    """Route to the correct node based on circuit state."""
    return state["state"].lower()


def build_circuit_breaker_graph() -> StateGraph:
    """Build a LangGraph circuit breaker state machine."""
    graph = StateGraph(CircuitState)
    graph.add_node("closed", closed_node)
    graph.add_node("open", open_node)
    graph.add_node("half_open", half_open_node)

    graph.set_entry_point("closed")
    graph.add_conditional_edges("closed", route_by_state, {"closed": END, "open": "open"})
    graph.add_edge("open", "half_open")
    graph.add_conditional_edges("half_open", route_by_state, {"closed": END, "open": "open"})

    return graph


# Usage:
# graph = build_circuit_breaker_graph()
# app = graph.compile()
# result = app.invoke({"name": "api", "state": "CLOSED", "consecutive_failures": 0, "failure_threshold": 3, "result": None, "error": ""})
'''

FRAMEWORK_TEMPLATES["supervisor_worker_langgraph"] = '''# LORE SCAFFOLD: supervisor_worker (LangGraph variant)
"""
Supervisor-Worker as a LangGraph state machine.

The supervisor node classifies tasks and routes to specialist worker nodes.
Workers return results that the supervisor synthesizes.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import StateGraph, END


class WorkflowState(TypedDict):
    task: str
    task_type: str
    worker_output: str
    final_result: str
    error: str


def supervisor_node(state: WorkflowState) -> WorkflowState:
    """Supervisor classifies the task and determines routing."""
    task = state["task"].lower()
    if any(kw in task for kw in ("test", "spec", "coverage")):
        task_type = "tester"
    elif any(kw in task for kw in ("security", "auth", "vulnerability")):
        task_type = "security"
    else:
        task_type = "coder"
    return {**state, "task_type": task_type}


def tester_node(state: WorkflowState) -> WorkflowState:
    """Test writing worker."""
    return {**state, "worker_output": f"Tests for: {state['task']}"}


def coder_node(state: WorkflowState) -> WorkflowState:
    """Code writing worker."""
    return {**state, "worker_output": f"Implementation for: {state['task']}"}


def security_node(state: WorkflowState) -> WorkflowState:
    """Security review worker."""
    return {**state, "worker_output": f"Security review for: {state['task']}"}


def synthesize_node(state: WorkflowState) -> WorkflowState:
    """Supervisor synthesizes worker output into final result."""
    return {**state, "final_result": f"[{state['task_type']}] {state['worker_output']}"}


def route_to_worker(state: WorkflowState) -> str:
    return state["task_type"]


def build_supervisor_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("tester", tester_node)
    graph.add_node("coder", coder_node)
    graph.add_node("security", security_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", route_to_worker, {
        "tester": "tester", "coder": "coder", "security": "security",
    })
    graph.add_edge("tester", "synthesize")
    graph.add_edge("coder", "synthesize")
    graph.add_edge("security", "synthesize")
    graph.add_edge("synthesize", END)

    return graph
'''

FRAMEWORK_TEMPLATES["reviewer_loop_langgraph"] = '''# LORE SCAFFOLD: reviewer_loop (LangGraph variant)
"""
Reviewer Loop as a LangGraph state machine.

Generator node produces output, reviewer node scores it.
Conditional edge loops back to generator if score < threshold.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, END


class ReviewState(TypedDict):
    prompt: str
    draft: str
    score: float
    feedback: str
    iteration: int
    max_iterations: int
    threshold: float


def generator_node(state: ReviewState) -> ReviewState:
    """Generate or revise a draft."""
    # Replace with actual LLM call
    draft = f"Draft v{state['iteration'] + 1} for: {state['prompt']}"
    if state["feedback"]:
        draft += f" (revised based on: {state['feedback']})"
    return {**state, "draft": draft, "iteration": state["iteration"] + 1}


def reviewer_node(state: ReviewState) -> ReviewState:
    """Review and score the draft."""
    # Replace with actual LLM review call
    score = min(0.5 + state["iteration"] * 0.2, 1.0)  # Simulated improvement
    feedback = "Needs more detail" if score < state["threshold"] else "Approved"
    return {**state, "score": score, "feedback": feedback}


def should_continue(state: ReviewState) -> str:
    if state["score"] >= state["threshold"]:
        return "accepted"
    if state["iteration"] >= state["max_iterations"]:
        return "escalate"
    return "revise"


def build_reviewer_graph() -> StateGraph:
    graph = StateGraph(ReviewState)
    graph.add_node("generator", generator_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("generator")
    graph.add_edge("generator", "reviewer")
    graph.add_conditional_edges("reviewer", should_continue, {
        "revise": "generator", "accepted": END, "escalate": END,
    })

    return graph
'''

# ── CrewAI variants ───────────────────────────────────────────────────────────

FRAMEWORK_TEMPLATES["supervisor_worker_crewai"] = '''# LORE SCAFFOLD: supervisor_worker (CrewAI variant)
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
'''

FRAMEWORK_TEMPLATES["reviewer_loop_crewai"] = '''# LORE SCAFFOLD: reviewer_loop (CrewAI variant)
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
'''

FRAMEWORK_TEMPLATES["handoff_pattern_crewai"] = '''# LORE SCAFFOLD: handoff_pattern (CrewAI variant)
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
'''

# ── OpenAI Agents SDK variants ────────────────────────────────────────────────

FRAMEWORK_TEMPLATES["handoff_pattern_openai_agents"] = '''# LORE SCAFFOLD: handoff_pattern (OpenAI Agents SDK variant)
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
'''

FRAMEWORK_TEMPLATES["model_routing_openai_agents"] = '''# LORE SCAFFOLD: model_routing (OpenAI Agents SDK variant)
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
        "You are a task router. Classify the user's task:\\n"
        "- Simple (tests, docs, boilerplate) -> hand off to SimpleWorker\\n"
        "- Standard (features, bugs, refactoring) -> hand off to StandardWorker\\n"
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
'''

FRAMEWORK_TEMPLATES["supervisor_worker_openai_agents"] = '''# LORE SCAFFOLD: supervisor_worker (OpenAI Agents SDK variant)
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
        "You are a technical lead. Analyze the task and delegate:\\n"
        "- Code writing tasks -> Coder\\n"
        "- Test writing tasks -> Tester\\n"
        "- Code review tasks -> Reviewer\\n"
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
'''


# ─── Pattern metadata for list_patterns ───────────────────────────────────────

_PATTERN_FRAMEWORKS: dict[str, list[str]] = {
    "circuit_breaker": ["langgraph"],
    "supervisor_worker": ["langgraph", "crewai", "openai_agents"],
    "reviewer_loop": ["langgraph", "crewai"],
    "handoff_pattern": ["crewai", "openai_agents"],
    "model_routing": ["openai_agents"],
}

_PATTERN_ARCHETYPES: dict[str, str] = {
    "circuit_breaker": "The Breaker",
    "dead_letter_queue": "The Archivist",
    "reviewer_loop": "The Council",
    "supervisor_worker": "The Commander",
    "tool_health_monitor": "The Warden",
    "handoff_pattern": "The Weaver",
    "model_routing": "The Router",
    "three_layer_memory": "The Stack",
    "sentinel_observability": "The Sentinel",
    "librarian_retrieval": "The Librarian",
    "scout_discovery": "The Scout",
    "cartographer_knowledge_graph": "The Cartographer",
    "timekeeper_scheduling": "The Timekeeper",
    "architect_system_design": "The Architect",
    "alchemist_prompt_routing": "The Alchemist",
}


def get_template(pattern: str, framework: str = "python") -> str | None:
    """Get scaffold template by pattern name and optional framework.

    Falls back to pure Python if the framework variant doesn't exist.
    """
    if framework and framework != "python":
        key = f"{pattern}_{framework}"
        if key in FRAMEWORK_TEMPLATES:
            return FRAMEWORK_TEMPLATES[key]
    return TEMPLATES.get(pattern)


def list_patterns() -> list[dict]:
    """List all available scaffold patterns with metadata."""
    return [
        {
            "pattern": name,
            "archetype": _PATTERN_ARCHETYPES.get(name, ""),
            "frameworks": ["python"] + _PATTERN_FRAMEWORKS.get(name, []),
            "lines": template.count("\n"),
        }
        for name, template in TEMPLATES.items()
    ]
