# LORE SCAFFOLD: handoff_pattern
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
