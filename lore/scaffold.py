"""
LORE Scaffold — Production-ready code templates for AI agent patterns.

Template bodies live under ``lore/templates`` so contributors can edit them as
normal files instead of diffing a 3,000-line string table.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).with_name("templates")
DEPLOY_TEMPLATES_DIR = TEMPLATES_DIR / "deploy"

_PATTERN_FRAMEWORKS: dict[str, list[str]] = {'circuit_breaker': ['langgraph'], 'supervisor_worker': ['langgraph', 'crewai', 'openai_agents'], 'reviewer_loop': ['langgraph', 'crewai'], 'handoff_pattern': ['crewai', 'openai_agents'], 'model_routing': ['openai_agents']}

_PATTERN_ARCHETYPES: dict[str, str] = {'circuit_breaker': 'The Breaker', 'dead_letter_queue': 'The Archivist', 'reviewer_loop': 'The Council', 'supervisor_worker': 'The Commander', 'tool_health_monitor': 'The Warden', 'handoff_pattern': 'The Weaver', 'model_routing': 'The Router', 'three_layer_memory': 'The Stack', 'sentinel_observability': 'The Sentinel', 'librarian_retrieval': 'The Librarian', 'scout_discovery': 'The Scout', 'cartographer_knowledge_graph': 'The Cartographer', 'timekeeper_scheduling': 'The Timekeeper', 'architect_system_design': 'The Architect', 'alchemist_prompt_routing': 'The Alchemist', 'react_loop': '', 'reflexion_loop': '', 'plan_execute': '', 'cost_guard': 'The Timekeeper'}

_FRAMEWORK_KEYS = ['circuit_breaker_langgraph', 'handoff_pattern_crewai', 'handoff_pattern_openai_agents', 'model_routing_openai_agents', 'reviewer_loop_crewai', 'reviewer_loop_langgraph', 'supervisor_worker_crewai', 'supervisor_worker_langgraph', 'supervisor_worker_openai_agents']

_DEPLOY_FILENAMES: dict[str, str] = {
    "docker_compose": "docker_compose.yml",
    "kubernetes": "kubernetes.yml",
    "cloudflare_worker": "cloudflare_worker.js",
    "dockerfile": "dockerfile",
}


def _read_templates(paths: list[Path]) -> dict[str, str]:
    templates: dict[str, str] = {}
    for path in paths:
        templates[path.stem] = path.read_text()
    return templates


def _read_framework_templates() -> dict[str, str]:
    return _read_templates([TEMPLATES_DIR / f"{key}.py" for key in _FRAMEWORK_KEYS])


def _read_base_templates() -> dict[str, str]:
    return _read_templates(
        sorted(
            path
            for path in TEMPLATES_DIR.glob("*.py")
            if path.stem not in set(_FRAMEWORK_KEYS)
        )
    )


def _read_deploy_templates() -> dict[str, str]:
    return {
        name: (DEPLOY_TEMPLATES_DIR / filename).read_text()
        for name, filename in _DEPLOY_FILENAMES.items()
    }


FRAMEWORK_TEMPLATES: dict[str, str] = _read_framework_templates()
TEMPLATES: dict[str, str] = _read_base_templates()
DEPLOY_TEMPLATES: dict[str, str] = _read_deploy_templates()


def get_template(pattern: str, framework: str = "python") -> str | None:
    """Get scaffold template by pattern name and optional framework.

    Falls back to pure Python if the framework variant doesn't exist.
    Also checks DEPLOY_TEMPLATES if framework=="deploy" or pattern is a deploy key.
    """
    if framework == "deploy" or pattern in DEPLOY_TEMPLATES:
        return DEPLOY_TEMPLATES.get(pattern)
    if framework and framework != "python":
        key = f"{pattern}_{framework}"
        if key in FRAMEWORK_TEMPLATES:
            return FRAMEWORK_TEMPLATES[key]
    return TEMPLATES.get(pattern)


def get_deploy_template(name: str) -> str | None:
    """Return a deployment template by name, or None if not found."""
    return DEPLOY_TEMPLATES.get(name)


def list_deploy_templates() -> list[dict]:
    """List all available deployment scaffold templates."""
    return [
        {
            "name": name,
            "lines": template.count("\n"),
            "preview": template.strip().split("\n")[0],
        }
        for name, template in DEPLOY_TEMPLATES.items()
    ]


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
