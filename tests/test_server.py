"""Tests for lore.server lazy module loading."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from lore import server


def test_unrelated_tool_still_runs_when_optional_module_import_fails(monkeypatch):
    search_mod = SimpleNamespace(
        list_articles=lambda: [{"id": "alpha", "title": "Alpha"}],
    )

    def fake_module(name: str):
        if name == "search":
            return search_mod
        if name == "proposals":
            raise RuntimeError("broken optional module")
        raise AssertionError(f"unexpected module request: {name}")

    monkeypatch.setattr(server, "_module", fake_module)

    result = asyncio.run(server._dispatch("lore_list", {}))

    assert result == {
        "entries": [{"id": "alpha", "title": "Alpha"}],
        "count": 1,
    }


def test_failing_tool_returns_error_without_blocking_server(monkeypatch):
    def fake_module(name: str):
        if name == "proposals":
            raise RuntimeError("broken optional module")
        raise AssertionError(f"unexpected module request: {name}")

    monkeypatch.setattr(server, "_module", fake_module)

    response = asyncio.run(server.call_tool("lore_proposal_list", {}))

    assert len(response) == 1
    assert "broken optional module" in response[0].text
    assert "lore_proposal_list" in response[0].text


def test_audit_dispatch_uses_audit_module(monkeypatch):
    audit_mod = SimpleNamespace(
        DEFAULT_AUDIT_QUESTION="default q",
        run_audit=lambda path, question, model, max_files, max_chars: {
            "path": path,
            "question": question,
            "model": model,
            "max_files": max_files,
            "max_chars": max_chars,
        },
    )

    def fake_module(name: str):
        if name == "audit":
            return audit_mod
        raise AssertionError(f"unexpected module request: {name}")

    monkeypatch.setattr(server, "_module", fake_module)

    result = asyncio.run(server._dispatch("lore_audit", {"path": ".", "model": "gemini-test"}))

    assert result["question"] == "default q"
    assert result["model"] == "gemini-test"
