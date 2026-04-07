"""
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
