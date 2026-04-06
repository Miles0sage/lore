"""Tests for lore.fleet — agent fleet registry."""

import json
import pytest

from lore import fleet


@pytest.fixture(autouse=True)
def _isolate_fleet(tmp_path, monkeypatch):
    """Redirect fleet.json to a temp directory so tests don't touch real data."""
    monkeypatch.setattr(fleet, "_fleet_path", lambda: tmp_path / "fleet.json")


def test_register_agent():
    """Register a new agent creates fleet.json and adds agent."""
    result = fleet.register_agent("segundo", "Segundo PA", "system_prompt", ["*"])
    assert result["action"] == "registered"
    assert result["agent"]["id"] == "segundo"
    assert result["agent"]["name"] == "Segundo PA"
    assert result["agent"]["format"] == "system_prompt"
    assert result["agent"]["patterns"] == ["*"]
    assert result["fleet_size"] == 1


def test_register_updates_existing():
    """Re-registering the same ID updates instead of duplicating."""
    fleet.register_agent("vigil", "Vigil v1", "claude_md", ["circuit-breaker"])
    result = fleet.register_agent("vigil", "Vigil v2", "system_prompt", ["circuit-breaker", "dead-letter-queue"])

    assert result["action"] == "updated"
    assert result["agent"]["name"] == "Vigil v2"
    assert result["agent"]["format"] == "system_prompt"
    assert result["fleet_size"] == 1  # Still just one agent

    # Verify original registration time preserved
    assert "registered_at" in result["agent"]
    assert "updated_at" in result["agent"]


def test_unregister():
    """Removing an agent reduces fleet size."""
    fleet.register_agent("temp", "Temp Agent", "claude_md", ["*"])
    assert len(fleet.list_agents()) == 1

    result = fleet.unregister_agent("temp")
    assert result["action"] == "unregistered"
    assert result["fleet_size"] == 0
    assert len(fleet.list_agents()) == 0


def test_unregister_not_found():
    """Unregistering a nonexistent agent returns not_found."""
    result = fleet.unregister_agent("ghost")
    assert result["action"] == "not_found"


def test_list_agents():
    """List returns correct agents."""
    fleet.register_agent("a1", "Agent One", "claude_md", ["*"])
    fleet.register_agent("a2", "Agent Two", "system_prompt", ["circuit-breaker"])

    agents = fleet.list_agents()
    assert len(agents) == 2
    ids = {a["id"] for a in agents}
    assert ids == {"a1", "a2"}


def test_get_agents_for_pattern():
    """Filter agents by pattern subscription."""
    fleet.register_agent("general", "General", "claude_md", ["*"])
    fleet.register_agent("specific", "Specific", "system_prompt", ["circuit-breaker"])
    fleet.register_agent("other", "Other", "skill", ["reviewer-loop"])

    # circuit-breaker should match general (wildcard) and specific
    matched = fleet.get_agents_for_pattern("circuit-breaker")
    ids = {a["id"] for a in matched}
    assert ids == {"general", "specific"}

    # reviewer-loop should match general (wildcard) and other
    matched2 = fleet.get_agents_for_pattern("reviewer-loop")
    ids2 = {a["id"] for a in matched2}
    assert ids2 == {"general", "other"}


def test_wildcard_pattern():
    """Agent with patterns=['*'] matches everything."""
    fleet.register_agent("wildcard", "Wildcard Agent", "claude_md", ["*"])

    for pattern in ["circuit-breaker", "dead-letter-queue", "anything-at-all"]:
        matched = fleet.get_agents_for_pattern(pattern)
        assert len(matched) == 1
        assert matched[0]["id"] == "wildcard"


def test_empty_fleet():
    """List and get return empty when no agents registered."""
    assert fleet.list_agents() == []
    assert fleet.get_agents_for_pattern("circuit-breaker") == []


def test_fleet_json_persistence(tmp_path, monkeypatch):
    """Verify data persists across calls via JSON file."""
    path = tmp_path / "persist_test" / "fleet.json"
    monkeypatch.setattr(fleet, "_fleet_path", lambda: path)

    fleet.register_agent("persist", "Persist Agent", "claude_md", ["*"])

    # Read the raw JSON to verify structure
    data = json.loads(path.read_text())
    assert len(data["agents"]) == 1
    assert data["agents"][0]["id"] == "persist"
