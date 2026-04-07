"""Tests for deployment scaffolds and reasoning loop patterns."""

import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
CLI = [PYTHON, "-m", "lore.cli"]
REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*CLI, *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
        check=check,
    )


# ── Deploy template existence tests ─────────────────────────────────────────


def test_docker_compose_template_exists():
    from lore.scaffold import DEPLOY_TEMPLATES
    assert "docker_compose" in DEPLOY_TEMPLATES
    assert len(DEPLOY_TEMPLATES["docker_compose"]) > 0


def test_kubernetes_template_exists():
    from lore.scaffold import DEPLOY_TEMPLATES
    assert "kubernetes" in DEPLOY_TEMPLATES
    assert len(DEPLOY_TEMPLATES["kubernetes"]) > 0


def test_cloudflare_worker_template_exists():
    from lore.scaffold import DEPLOY_TEMPLATES
    assert "cloudflare_worker" in DEPLOY_TEMPLATES
    assert len(DEPLOY_TEMPLATES["cloudflare_worker"]) > 0


def test_dockerfile_template_exists():
    from lore.scaffold import DEPLOY_TEMPLATES
    assert "dockerfile" in DEPLOY_TEMPLATES
    assert len(DEPLOY_TEMPLATES["dockerfile"]) > 0


# ── Deploy template content tests ────────────────────────────────────────────


def test_docker_compose_has_services():
    from lore.scaffold import DEPLOY_TEMPLATES
    t = DEPLOY_TEMPLATES["docker_compose"]
    assert "supervisor:" in t
    assert "worker:" in t
    assert "redis:" in t
    assert "postgres:" in t
    assert "replicas: 3" in t
    assert "healthcheck:" in t


def test_kubernetes_has_statefulset():
    from lore.scaffold import DEPLOY_TEMPLATES
    t = DEPLOY_TEMPLATES["kubernetes"]
    assert "StatefulSet" in t
    assert "ConfigMap" in t
    assert "CronJob" in t
    assert "Service" in t
    assert "resources:" in t


def test_cloudflare_worker_has_durable_object():
    from lore.scaffold import DEPLOY_TEMPLATES
    t = DEPLOY_TEMPLATES["cloudflare_worker"]
    assert "AgentSession" in t
    assert "Durable Object" in t or "durable_objects" in t.lower() or "AGENT_SESSION" in t
    assert "SHARED_STATE" in t


def test_dockerfile_has_multistage():
    from lore.scaffold import DEPLOY_TEMPLATES
    t = DEPLOY_TEMPLATES["dockerfile"]
    assert "FROM python:3.12-slim AS builder" in t
    assert "USER agent" in t
    assert "HEALTHCHECK" in t
    assert "EXPOSE 8000" in t


# ── Deploy template headers ──────────────────────────────────────────────────


def test_deploy_templates_have_headers():
    from lore.scaffold import DEPLOY_TEMPLATES
    for name, template in DEPLOY_TEMPLATES.items():
        stripped = template.strip()
        assert "LORE DEPLOY:" in stripped, f"{name} missing LORE DEPLOY header"


# ── list_deploy_templates ────────────────────────────────────────────────────


def test_list_deploy_templates_returns_4():
    from lore.scaffold import list_deploy_templates
    templates = list_deploy_templates()
    assert len(templates) == 4
    names = {t["name"] for t in templates}
    assert names == {"docker_compose", "kubernetes", "cloudflare_worker", "dockerfile"}


# ── get_deploy_template ──────────────────────────────────────────────────────


def test_get_deploy_template_returns_content():
    from lore.scaffold import get_deploy_template
    t = get_deploy_template("docker_compose")
    assert t is not None
    assert "services:" in t


def test_get_deploy_template_returns_none_for_unknown():
    from lore.scaffold import get_deploy_template
    assert get_deploy_template("nonexistent") is None


# ── get_template with deploy key ─────────────────────────────────────────────


def test_get_template_finds_deploy_by_key():
    from lore.scaffold import get_template
    t = get_template("docker_compose")
    assert t is not None
    assert "services:" in t


def test_get_template_finds_deploy_with_framework_deploy():
    from lore.scaffold import get_template
    t = get_template("kubernetes", framework="deploy")
    assert t is not None
    assert "StatefulSet" in t


# ── CLI deploy subcommand ────────────────────────────────────────────────────


def test_cli_deploy_list():
    result = _run("deploy", "--list")
    assert result.returncode == 0
    assert "docker_compose" in result.stdout
    assert "kubernetes" in result.stdout
    assert "cloudflare_worker" in result.stdout
    assert "dockerfile" in result.stdout
    assert "4 deploy templates" in result.stdout


def test_cli_deploy_docker_compose():
    result = _run("deploy", "docker_compose")
    assert result.returncode == 0
    assert "services:" in result.stdout
    assert "supervisor:" in result.stdout


def test_cli_deploy_unknown_template():
    result = _run("deploy", "nonexistent", check=False)
    assert result.returncode != 0
    assert "no deploy template" in result.stderr.lower() or "error" in result.stderr.lower()


def test_cli_deploy_no_args():
    result = _run("deploy", check=False)
    assert result.returncode != 0


# ── CLI deploy output to file ────────────────────────────────────────────────


def test_cli_deploy_output_to_dir(tmp_path):
    result = _run("deploy", "dockerfile", "-o", str(tmp_path))
    assert result.returncode == 0
    assert "Wrote" in result.stdout
    written = (tmp_path / "Dockerfile").read_text()
    assert "FROM python:3.12-slim" in written


# ── Reasoning loop pattern existence ─────────────────────────────────────────


def test_react_loop_template_exists():
    from lore.scaffold import TEMPLATES
    assert "react_loop" in TEMPLATES
    assert len(TEMPLATES["react_loop"]) > 0


def test_reflexion_loop_template_exists():
    from lore.scaffold import TEMPLATES
    assert "reflexion_loop" in TEMPLATES
    assert len(TEMPLATES["reflexion_loop"]) > 0


def test_plan_execute_template_exists():
    from lore.scaffold import TEMPLATES
    assert "plan_execute" in TEMPLATES
    assert len(TEMPLATES["plan_execute"]) > 0


# ── Reasoning loop content checks ────────────────────────────────────────────


def test_react_loop_has_think_act_observe():
    from lore.scaffold import TEMPLATES
    t = TEMPLATES["react_loop"]
    assert "def think(" in t
    assert "def act(" in t
    assert "def run(" in t
    assert "ReActAgent" in t


def test_reflexion_loop_has_attempt_evaluate_reflect():
    from lore.scaffold import TEMPLATES
    t = TEMPLATES["reflexion_loop"]
    assert "def attempt(" in t
    assert "def evaluate(" in t
    assert "def reflect(" in t
    assert "ReflexionAgent" in t


def test_plan_execute_has_plan_execute_verify():
    from lore.scaffold import TEMPLATES
    t = TEMPLATES["plan_execute"]
    assert "def plan(" in t
    assert "def execute_step(" in t
    assert "def verify(" in t
    assert "PlanExecuteAgent" in t


# ── Reasoning patterns have LORE SCAFFOLD headers ────────────────────────────


def test_reasoning_patterns_have_headers():
    from lore.scaffold import TEMPLATES
    for name in ("react_loop", "reflexion_loop", "plan_execute"):
        assert "LORE SCAFFOLD:" in TEMPLATES[name], f"{name} missing LORE SCAFFOLD header"


# ── Reasoning patterns compile as valid Python ───────────────────────────────


def test_react_loop_compiles():
    from lore.scaffold import TEMPLATES
    compile(TEMPLATES["react_loop"], "<react_loop>", "exec")


def test_reflexion_loop_compiles():
    from lore.scaffold import TEMPLATES
    compile(TEMPLATES["reflexion_loop"], "<reflexion_loop>", "exec")


def test_plan_execute_compiles():
    from lore.scaffold import TEMPLATES
    compile(TEMPLATES["plan_execute"], "<plan_execute>", "exec")


# ── Reasoning patterns in list_patterns ──────────────────────────────────────


def test_list_patterns_includes_reasoning():
    from lore.scaffold import list_patterns
    patterns = list_patterns()
    names = {p["pattern"] for p in patterns}
    assert "react_loop" in names
    assert "reflexion_loop" in names
    assert "plan_execute" in names


# ── CLI scaffold --list includes reasoning patterns ──────────────────────────


def test_cli_scaffold_list_includes_reasoning():
    result = _run("scaffold", "--list")
    assert result.returncode == 0
    assert "react_loop" in result.stdout
    assert "reflexion_loop" in result.stdout
    assert "plan_execute" in result.stdout
    # Now 19 patterns (15 original + 3 reasoning + 1 cost_guard)
    assert "19 patterns available" in result.stdout
