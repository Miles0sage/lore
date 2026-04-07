"""Large-context Lore audit using Gemini as an on-demand analysis backend."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from .config import get_audit_dir

DEFAULT_AUDIT_QUESTION = (
    "Audit this codebase for missing Lore patterns, operational risks, weak verification, "
    "and the highest-value fixes to make it safer and more production-ready."
)

_INCLUDED_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".js", ".ts", ".tsx", ".jsx",
    ".sh", ".sql", ".ini", ".cfg",
}
_EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "index",
}

_ACTION_RULES = [
    ("circuit", "circuit_breaker"),
    ("dead letter", "dead_letter_queue"),
    ("dlq", "dead_letter_queue"),
    ("review", "reviewer_loop"),
    ("verification", "reviewer_loop"),
    ("memory", "three_layer_memory"),
    ("resume", "three_layer_memory"),
    ("routing", "model_routing"),
    ("observability", "sentinel_observability"),
    ("telemetry", "sentinel_observability"),
    ("health", "tool_health_monitor"),
    ("cost", "cost_guard"),
    ("budget", "cost_guard"),
    ("token limit", "cost_guard"),
    ("spend", "cost_guard"),
]


def _score_path(path: Path) -> tuple[int, str]:
    rel = str(path).replace("\\", "/")
    priority = 100
    if rel in {"README.md", "CLAUDE.md", "pyproject.toml"}:
        priority = 0
    elif rel.startswith("lore/"):
        priority = 10
    elif rel.startswith("tests/"):
        priority = 20
    elif rel.startswith("docs/"):
        priority = 30
    return (priority, rel)


def collect_audit_files(
    root: Path,
    *,
    max_files: int = 120,
    max_file_bytes: int = 120_000,
) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix and path.suffix.lower() not in _INCLUDED_SUFFIXES:
            continue
        try:
            if path.stat().st_size > max_file_bytes:
                continue
        except OSError:
            continue
        files.append(path)
    files.sort(key=lambda item: _score_path(item.relative_to(root)))
    return files[:max_files]


def build_audit_bundle(
    root: Path,
    *,
    max_files: int = 120,
    max_chars: int = 400_000,
) -> dict[str, object]:
    selected = collect_audit_files(root, max_files=max_files)
    parts: list[str] = []
    included: list[str] = []
    skipped: list[str] = []
    total_chars = 0

    for path in selected:
        rel = str(path.relative_to(root))
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skipped.append(rel)
            continue

        block = f"\n--- FILE: {rel} ---\n{text}\n"
        if total_chars + len(block) > max_chars:
            skipped.append(rel)
            continue
        parts.append(block)
        included.append(rel)
        total_chars += len(block)

    return {
        "root": str(root),
        "files": included,
        "skipped": skipped,
        "bundle": "".join(parts).strip(),
        "chars": total_chars,
    }


def build_audit_prompt(question: str, bundle: dict[str, object]) -> str:
    file_list = "\n".join(f"- {path}" for path in bundle["files"])
    repo_text = bundle["bundle"]
    return f"""You are LORE Audit.

Goal:
- {question}

Audit lens:
- circuit breakers and failure isolation
- dead letter queue and replay paths
- verification loops and tests
- observability, telemetry, and cost visibility
- permission gates and dangerous execution paths
- memory/resume/session continuity
- routing/escalation logic
- install/bootstrap surfaces that increase adoption

Repository root:
{bundle["root"]}

Files included:
{file_list}

Return strict JSON only with this shape:
{{
  "summary": "short paragraph",
  "product_direction": "one sentence",
  "top_findings": [
    {{
      "severity": "critical|high|medium|low",
      "title": "short title",
      "files": ["path"],
      "why": "why this matters",
      "fix": "what to do"
    }}
  ],
  "missing_capabilities": ["..."],
  "reusable_assets": [
    {{
      "source": "repo or module",
      "asset": "thing to reuse",
      "value": "why it helps Lore now"
    }}
  ],
  "next_builds": ["ranked next steps"]
}}

Repository bundle:
{repo_text}
"""


def _extract_json_object(raw: str) -> dict[str, object]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in audit output")
    return json.loads(text[start : end + 1])


def _run_gemini_cli(prompt: str, *, cwd: Path, model: str) -> str:
    gemini_bin = shutil.which("gemini")
    if not gemini_bin:
        raise RuntimeError("Gemini CLI not found in PATH")

    # Run from /tmp to avoid IDE context picking up binary/image files from the
    # repo directory, which causes "Provided image is not valid" API errors.
    # Pass the full prompt via stdin only (no -p flag) — combining -p and stdin
    # causes the CLI to hang waiting for interactive input.
    proc = subprocess.run(
        [
            gemini_bin,
            "-m",
            model,
            "--output-format",
            "text",
        ],
        input=prompt,
        text=True,
        capture_output=True,
        cwd="/tmp",
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"gemini exited {proc.returncode}")
    return proc.stdout.strip()


def _write_report(question: str, report: dict[str, object]) -> Path:
    audit_dir = get_audit_dir()
    audit_dir.mkdir(parents=True, exist_ok=True)
    slug = "-".join(question.lower().split()[:6]) or "audit"
    slug = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in slug).strip("-") or "audit"
    path = audit_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def suggest_lore_actions(parsed: dict[str, object]) -> list[dict[str, str]]:
    corpus_parts = [str(parsed.get("summary", ""))]
    corpus_parts.extend(str(item) for item in parsed.get("missing_capabilities", []))
    for finding in parsed.get("top_findings", []):
        if isinstance(finding, dict):
            corpus_parts.append(str(finding.get("title", "")))
            corpus_parts.append(str(finding.get("fix", "")))
    corpus = " ".join(corpus_parts).lower()

    patterns: list[str] = []
    for keyword, pattern in _ACTION_RULES:
        if keyword in corpus and pattern not in patterns:
            patterns.append(pattern)

    actions: list[dict[str, str]] = []
    for pattern in patterns[:4]:
        actions.append(
            {
                "type": "scaffold",
                "pattern": pattern,
                "command": f"lore scaffold {pattern}",
                "why": f"Generate a reference implementation for {pattern}.",
            }
        )
    hookable = [pattern for pattern in patterns if pattern in {"circuit_breaker", "dead_letter_queue", "reviewer_loop", "sentinel_observability"}]
    if hookable:
        pattern_arg = ",".join(hookable)
        actions.append(
            {
                "type": "install",
                "pattern": pattern_arg,
                "command": f"lore install --patterns {pattern_arg}",
                "why": "Inject hooks and skills for the most relevant reliability patterns.",
            }
        )
    return actions


def run_audit(
    path: str | Path = ".",
    *,
    question: str = DEFAULT_AUDIT_QUESTION,
    model: str = "gemini-2.5-pro",
    max_files: int = 120,
    max_chars: int = 400_000,
    runner: Callable[..., str] | None = None,
) -> dict[str, object]:
    root = Path(path).expanduser().resolve()
    if not root.exists():
        return {"error": f"Path does not exist: {root}"}
    if root.is_file():
        root = root.parent

    bundle = build_audit_bundle(root, max_files=max_files, max_chars=max_chars)
    prompt = build_audit_prompt(question, bundle)
    raw = (runner or _run_gemini_cli)(prompt, cwd=root, model=model)
    parsed = _extract_json_object(raw)

    report = {
        "root": str(root),
        "question": question,
        "model": model,
        "backend": "gemini_cli",
        "files_scanned": bundle["files"],
        "files_skipped": bundle["skipped"],
        "bundle_chars": bundle["chars"],
        "report": parsed,
        "lore_actions": suggest_lore_actions(parsed),
    }
    report_path = _write_report(question, report)
    report["report_path"] = str(report_path)
    return report
