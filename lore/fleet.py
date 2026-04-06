"""
LORE Fleet — Registry of agents that subscribe to Lore pattern updates.

Simple JSON-backed registry. No database, just atomic read/write to
.lore/fleet.json inside the workspace.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .config import get_telemetry_dir


def _fleet_path() -> Path:
    """Path to the fleet registry JSON file."""
    return get_telemetry_dir() / "fleet.json"


def _read_registry() -> dict:
    """Read the fleet registry, returning empty structure if absent."""
    path = _fleet_path()
    if not path.exists():
        return {"agents": []}
    try:
        data = json.loads(path.read_text())
        if "agents" not in data:
            data["agents"] = []
        return data
    except (json.JSONDecodeError, OSError):
        return {"agents": []}


def _write_registry(data: dict) -> None:
    """Atomically write the fleet registry."""
    path = _fleet_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(path)


def register_agent(agent_id: str, name: str, format: str, patterns: list[str]) -> dict:
    """Add or update an agent in the fleet registry.

    Args:
        agent_id: Unique agent identifier.
        name: Human-readable agent name.
        format: Preferred lesson format (claude_md, system_prompt, skill, mcp_description).
        patterns: List of pattern IDs to subscribe to, or ["*"] for all.

    Returns:
        Dict confirming registration with agent details.
    """
    registry = _read_registry()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Check for existing agent
    existing_idx = None
    for i, agent in enumerate(registry["agents"]):
        if agent.get("id") == agent_id:
            existing_idx = i
            break

    entry = {
        "id": agent_id,
        "name": name,
        "format": format,
        "patterns": patterns,
        "registered_at": now,
    }

    if existing_idx is not None:
        # Preserve original registration time, update the rest
        entry["registered_at"] = registry["agents"][existing_idx].get("registered_at", now)
        entry["updated_at"] = now
        registry["agents"][existing_idx] = entry
        action = "updated"
    else:
        registry["agents"].append(entry)
        action = "registered"

    _write_registry(registry)

    return {
        "action": action,
        "agent": entry,
        "fleet_size": len(registry["agents"]),
    }


def unregister_agent(agent_id: str) -> dict:
    """Remove an agent from the fleet registry.

    Returns:
        Dict confirming removal or indicating agent was not found.
    """
    registry = _read_registry()
    original_count = len(registry["agents"])
    registry["agents"] = [a for a in registry["agents"] if a.get("id") != agent_id]
    new_count = len(registry["agents"])

    if new_count == original_count:
        return {"action": "not_found", "agent_id": agent_id}

    _write_registry(registry)
    return {
        "action": "unregistered",
        "agent_id": agent_id,
        "fleet_size": new_count,
    }


def list_agents() -> list[dict]:
    """List all registered agents."""
    registry = _read_registry()
    return registry["agents"]


def get_agents_for_pattern(pattern_id: str) -> list[dict]:
    """Return agents subscribed to a specific pattern.

    Agents with patterns=["*"] match everything.
    """
    registry = _read_registry()
    matched = []
    for agent in registry["agents"]:
        agent_patterns = agent.get("patterns", [])
        if "*" in agent_patterns or pattern_id in agent_patterns:
            matched.append(agent)
    return matched
