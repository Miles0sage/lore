#!/usr/bin/env python3
"""
LORE Research Daemon — Persistent autonomous wiki growth loop.

Runs forever, researching AI agent knowledge gaps every 30 minutes.
Uses parallel scouts (web + arxiv + github) and a two-stage quality gate:
  Stage 1: structural heuristics (fast, free)
  Stage 2: DeepSeek LLM judgment (cheap, ~$0.001/article, skipped if stage 1 fails)

Launch:
    nohup python3 /root/lore/scripts/lore_research_daemon.py \
        > /var/log/lore-daemon.log 2>&1 &
    echo $! > /tmp/lore-daemon.pid

Stop:
    kill $(cat /tmp/lore-daemon.pid)
"""

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

# ── Keys ─────────────────────────────────────────────────────────────────────
os.environ.setdefault("EXA_API_KEY", "d4013b25-0906-4722-9f87-1dd92a0243f0")
os.environ.setdefault("FIRECRAWL_API_KEY", "fc-aac4b5382aff41a080c103a2f1477701")

# Load API keys from ai-factory .env if not already set
def _load_factory_env():
    env_path = Path(os.environ.get("LORE_ENV_FILE", ".env"))
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

_load_factory_env()

# ── Config ────────────────────────────────────────────────────────────────────
LORE_ROOT     = Path(__file__).resolve().parents[1]
WIKI_DIR      = Path(os.environ.get("LORE_WIKI_DIR", str(LORE_ROOT)))
DWIKI         = os.environ.get("LORE_DWIKI_BIN", "dwiki")
LOG_FILE      = Path("/var/log/lore-daemon.log")
RESULTS       = Path("/var/log/lore-research-results.tsv")
TIPS_FILE     = LORE_ROOT / "scripts" / "research_tips.md"
PID_FILE      = Path("/tmp/lore-daemon.pid")
STATUS_FILE   = Path("/tmp/lore-daemon-status.json")

QUALITY_MIN        = float(os.environ.get("LORE_QUALITY_MIN", "0.60"))
DEEPSEEK_MIN       = float(os.environ.get("LORE_DEEPSEEK_MIN", "0.65"))
SLEEP_MINUTES      = int(os.environ.get("LORE_SLEEP_MINUTES", "30"))
RETRY_HOURS        = int(os.environ.get("LORE_RETRY_HOURS", "24"))
USE_DEEPSEEK_GATE  = os.environ.get("LORE_DEEPSEEK_GATE", "true").lower() != "false"

# ── Priority seeds ────────────────────────────────────────────────────────────
PRIORITY_SEEDS: list[tuple[str, str]] = [
    ("high", "secure agent execution sandboxing lethal trifecta 2025 2026"),
    ("high", "deployment patterns production AI agents isolation environments"),
    ("high", "meta-agents that rewrite their own execution harness at runtime"),
    ("high", "stale memory detection and invalidation in LLM agent vector stores"),
    ("high", "agent harness validation loops self-correction without human intervention"),
    ("high", "spec-first context engineering patterns production AI agents"),
    ("high", "LLM agent evaluation frameworks evals benchmarks 2025 2026"),
    ("high", "multi-agent negotiation coordination protocols beyond orchestration"),
    ("high", "agent tool use failure modes mitigations production"),
    ("high", "production AI agent reliability full stack observability"),
    ("medium", "cost-aware agent orchestration dynamic model routing"),
    ("medium", "compound knowledge flywheels self-improving AI systems"),
    ("medium", "agentic RAG versus traditional RAG knowledge grounded agents"),
]

# ── Globals ───────────────────────────────────────────────────────────────────
_shutdown = False
_stats = {
    "cycles": 0,
    "kept": 0,
    "discarded": 0,
    "errors": 0,
    "deepseek_calls": 0,
    "deepseek_passes": 0,
    "deepseek_rejects": 0,
    "started_at": datetime.now().isoformat(),
    "current_topic": None,
    "last_cycle_at": None,
}
_attempted: dict[str, datetime] = {}


def _handle_signal(signum, frame):
    global _shutdown
    log("INFO", f"Signal {signum} — finishing current cycle then exiting")
    _shutdown = True

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ── Logging ───────────────────────────────────────────────────────────────────
def log(level: str, msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def write_status(topic: str | None = None):
    _stats["current_topic"] = topic
    _stats["last_cycle_at"] = datetime.now().isoformat()
    try:
        STATUS_FILE.write_text(json.dumps({**_stats, "running": not _shutdown}, indent=2))
    except Exception:
        pass


def init_results():
    if not RESULTS.exists():
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        RESULTS.write_text("date\ttopic\tstatus\tscore\tdeepseek_score\tarticle\tnotes\n")


def log_result(topic: str, status: str, score: float, article: str, notes: str = "", deepseek_score: float = 0.0):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(RESULTS, "a") as f:
        f.write(f"{date}\t{topic}\t{status}\t{score:.2f}\t{deepseek_score:.2f}\t{article}\t{notes}\n")


def promote_tip(topic: str, sources: list[str], score: float, deepseek_score: float = 0.0):
    try:
        TIPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = (
            f"\n## {ts} — struct={score:.2f} deepseek={deepseek_score:.2f}\n"
            f"- **Topic**: {topic}\n"
            f"- **Sources**: {', '.join(sources)}\n"
        )
        with open(TIPS_FILE, "a") as f:
            f.write(entry)
    except Exception as e:
        log("WARN", f"  Could not write tip: {e}")


# ── DeepSeek quality gate ─────────────────────────────────────────────────────
_DEEPSEEK_SYSTEM = (
    "You are a quality gate for LORE — an AI agent pattern knowledge base. "
    "Your job is to score incoming articles for inclusion in a curated canon. "
    "Be strict. Only high-quality, actionable, technically accurate content passes."
)

_DEEPSEEK_PROMPT = """Rate this article for inclusion in an AI agent pattern knowledge base.

Topic hint: {topic}

Article (first 1200 chars):
---
{content}
---

Respond with JSON only, no explanation outside the JSON:
{{
  "score": <float 0.0-1.0>,
  "reason": "<one sentence>",
  "keep": <true if score >= 0.65>
}}

Score criteria:
- 0.9+: Novel, well-structured, actionable, technically accurate, cites real patterns
- 0.7-0.9: Solid, useful, some gaps but worth keeping
- 0.5-0.7: Borderline — vague, repetitive, or thin on specifics
- <0.5: Low quality — marketing fluff, wrong domain, duplicate noise"""


def deepseek_quality_gate(article_path: Path, topic: str) -> tuple[float, str, bool]:
    """Run DeepSeek quality assessment on an article. Returns (score, reason, keep)."""
    if not USE_DEEPSEEK_GATE:
        return 0.7, "deepseek gate disabled", True

    try:
        content = article_path.read_text(encoding="utf-8", errors="replace")[:1200]
    except Exception as e:
        return 0.5, f"read error: {e}", False

    # Import dispatch from the lore package
    sys.path.insert(0, str(LORE_ROOT))
    try:
        from lore.dispatch import dispatch_task
    except ImportError:
        log("WARN", "  DeepSeek gate: lore.dispatch not importable — skipping")
        return 0.7, "dispatch unavailable", True

    # Inject rejection history so DeepSeek avoids re-proposing known-bad content
    try:
        from lore.rejection_tracker import rejection_summary
        rejection_hint = "\n\n" + rejection_summary(limit=20) if rejection_summary(limit=20) else ""
    except Exception:
        rejection_hint = ""

    prompt = _DEEPSEEK_PROMPT.format(topic=topic, content=content) + rejection_hint
    result = dispatch_task(
        "triage",
        prompt,
        system=_DEEPSEEK_SYSTEM,
        description=f"quality gate: {article_path.name[:60]}",
        max_tokens=200,
    )

    _stats["deepseek_calls"] += 1

    if "error" in result:
        log("WARN", f"  DeepSeek gate error: {result['error'][:80]}")
        return 0.5, f"api error: {result['error'][:60]}", False

    # Parse JSON from content
    try:
        raw = result.get("content", "{}")
        # Strip markdown code fences if present
        raw = raw.strip().strip("```json").strip("```").strip()
        parsed = json.loads(raw)
        score = float(parsed.get("score", 0.5))
        reason = str(parsed.get("reason", ""))[:120]
        keep = bool(parsed.get("keep", score >= DEEPSEEK_MIN))
        if keep:
            _stats["deepseek_passes"] += 1
        else:
            _stats["deepseek_rejects"] += 1
        return score, reason, keep
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        log("WARN", f"  DeepSeek gate parse error: {e} — raw: {result.get('content','')[:80]}")
        return 0.5, "parse error", False


# ── dwiki wrappers ────────────────────────────────────────────────────────────
def run_dwiki(*args, timeout: int = 120):
    result = subprocess.run(
        [DWIKI, *args],
        cwd=str(WIKI_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ},
    )
    return result.returncode, result.stdout, result.stderr


def get_gaps() -> list[tuple[str, str]]:
    import re
    rc, out, err = run_dwiki("gaps", timeout=180)
    if rc != 0:
        log("WARN", f"dwiki gaps failed: {err[:200]}")
        return []
    gaps = []
    current_priority = "medium"
    for line in out.splitlines():
        line = line.strip()
        if "HIGH priority" in line:
            current_priority = "high"
        elif "MEDIUM priority" in line:
            current_priority = "medium"
        elif "LOW priority" in line:
            current_priority = "low"
        elif line.startswith("•"):
            topic = line.lstrip("•").strip()
            topic = re.split(r"\s+[-—]\s+", topic)[0].strip()
            if topic:
                gaps.append((current_priority, topic))
    return gaps


def _discover_one(topic: str, source: str) -> list[Path]:
    raw_before = set(WIKI_DIR.glob("raw/*.md"))
    try:
        run_dwiki("discover", topic, "--sources", source, "--max", "3", timeout=180)
    except subprocess.TimeoutExpired:
        log("WARN", f"    Scout {source} timed out: {topic}")
        return []
    raw_after = set(WIKI_DIR.glob("raw/*.md"))
    return list(raw_after - raw_before)


def discover_parallel(topic: str) -> list[Path]:
    all_files: list[Path] = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_discover_one, topic, s): s for s in ["web", "arxiv", "github"]}
        for fut in as_completed(futures, timeout=200):
            source = futures[fut]
            try:
                files = fut.result()
                all_files.extend(files)
                if files:
                    log("INFO", f"    Scout {source}: {len(files)} file(s)")
            except Exception as e:
                log("WARN", f"    Scout {source} error: {e}")
    return all_files


def compile_wiki() -> int:
    rc, out, err = run_dwiki("compile", timeout=600)
    return rc


def get_structural_score(article_path: Path) -> float:
    """Fast structural quality score — no API calls."""
    try:
        text = article_path.read_text(encoding="utf-8", errors="replace")
        body = text.split("---", 2)[2] if text.startswith("---") else text
        words = len(body.split())
        headers = sum(1 for l in body.splitlines() if l.startswith("## "))
        code_blocks = body.count("```")
        links = body.count("[[")
        has_overview = "## Overview" in body or "## Introduction" in body
        score = 0.0
        if words >= 400:        score += 0.30
        elif words >= 200:      score += 0.15
        if headers >= 3:        score += 0.20
        elif headers >= 2:      score += 0.10
        if code_blocks >= 2:    score += 0.20
        elif code_blocks >= 1:  score += 0.10
        if links >= 2:          score += 0.15
        elif links >= 1:        score += 0.08
        if has_overview:        score += 0.15
        return round(score, 2)
    except Exception:
        return 0.0


def get_article_scores(wiki_subdir: Path | None = None) -> dict[str, float]:
    wiki_dir = wiki_subdir or (WIKI_DIR / "wiki")
    scores: dict[str, float] = {}
    if not wiki_dir.exists():
        return scores
    for md_file in wiki_dir.glob("*.md"):
        scores[md_file.stem] = get_structural_score(md_file)
    return scores


def discard_raw_files(files: list[Path]):
    for f in files:
        try:
            Path(f).unlink()
        except Exception:
            pass


def git_commit(topic: str, count: int):
    try:
        subprocess.run(["git", "add", "wiki/", "raw/"], cwd=str(WIKI_DIR), capture_output=True)
        msg = f"research: auto-ingested '{topic}' ({count} article(s))"
        subprocess.run(["git", "commit", "-m", msg], cwd=str(WIKI_DIR), capture_output=True)
    except Exception as e:
        log("WARN", f"git commit failed: {e}")


# ── One research cycle ────────────────────────────────────────────────────────
def research_cycle():
    _stats["cycles"] += 1
    log("INFO", f"─── Cycle {_stats['cycles']} ───────────────────────────────")

    dwiki_gaps = get_gaps()
    gaps = PRIORITY_SEEDS + [g for g in dwiki_gaps if g[1] not in {s[1] for s in PRIORITY_SEEDS}]
    if not gaps:
        log("INFO", "No gaps found — wiki is complete for now")
        write_status(None)
        return

    priority_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda x: priority_order.get(x[0], 1))

    topic = None
    priority = "medium"
    now = datetime.now()
    for p, t in gaps:
        last = _attempted.get(t)
        if last is None or (now - last) > timedelta(hours=RETRY_HOURS):
            topic, priority = t, p
            break

    if topic is None:
        log("INFO", "All gaps attempted recently — sleeping until retry window opens")
        write_status(None)
        return

    _attempted[topic] = now
    log("INFO", f"Topic: '{topic}' ({priority})")
    write_status(topic)

    baseline = get_article_scores()

    log("INFO", "  Scouting (web + arxiv + github in parallel)...")
    try:
        new_raw = discover_parallel(topic)
    except Exception as e:
        log("WARN", f"  Scout error: {e}")
        log_result(topic, "error", 0.0, "", str(e))
        _stats["errors"] += 1
        return

    if not new_raw:
        log("INFO", "  No sources found")
        log_result(topic, "no_sources", 0.0, "")
        _stats["discarded"] += 1
        return

    log("INFO", f"  Found {len(new_raw)} raw file(s) — compiling...")
    try:
        compile_wiki()
    except Exception as e:
        log("WARN", f"  Compile error: {e}")
        discard_raw_files(new_raw)
        log_result(topic, "error", 0.0, "", str(e))
        _stats["errors"] += 1
        return

    # Stage 1: structural score
    new_scores = get_article_scores()
    new_articles = {k: v for k, v in new_scores.items() if k not in baseline}

    if not new_articles:
        log("INFO", "  Compile produced no new articles")
        discard_raw_files(new_raw)
        log_result(topic, "no_articles", 0.0, "")
        _stats["discarded"] += 1
        return

    wiki_dir = WIKI_DIR / "wiki"
    kept, failed = [], []
    kept_sources = []

    for article_id, struct_score in new_articles.items():
        article_path = wiki_dir / f"{article_id}.md"

        if struct_score < QUALITY_MIN:
            log("INFO", f"  DISCARD {article_id} — struct={struct_score:.2f} < {QUALITY_MIN}")
            failed.append(article_id)
            if article_path.exists():
                article_path.unlink()
            log_result(topic, "struct_fail", struct_score, article_id, f"struct<{QUALITY_MIN}")
            continue

        # Stage 2: DeepSeek LLM gate
        if article_path.exists():
            log("INFO", f"  DeepSeek gate: {article_id} (struct={struct_score:.2f})...")
            ds_score, ds_reason, ds_keep = deepseek_quality_gate(article_path, topic)
            log("INFO", f"    → score={ds_score:.2f} keep={ds_keep}: {ds_reason}")

            if not ds_keep:
                log("INFO", f"  DISCARD {article_id} — deepseek={ds_score:.2f}: {ds_reason}")
                failed.append(article_id)
                article_path.unlink()
                log_result(topic, "deepseek_fail", struct_score, article_id, ds_reason, ds_score)
                _stats["discarded"] += 1
                continue

            log("INFO", f"  KEEP {article_id} — struct={struct_score:.2f} deepseek={ds_score:.2f}")
            kept.append(article_id)
            kept_sources.append(article_id)
            log_result(topic, "kept", struct_score, article_id, ds_reason, ds_score)
            promote_tip(topic, [article_id], struct_score, ds_score)
            _stats["kept"] += 1
        else:
            log("WARN", f"  Article file missing after compile: {article_id}")
            failed.append(article_id)
            _stats["discarded"] += 1

    if kept:
        git_commit(topic, len(kept))
        log("INFO", f"  Committed {len(kept)} article(s): {', '.join(kept)}")
    else:
        log("INFO", f"  All {len(new_articles)} article(s) discarded — cleaning raw files")
        discard_raw_files(new_raw)
        _stats["discarded"] += len(failed)

    write_status(topic)


# ── Scheduled operator tasks ─────────────────────────────────────────────────
_last_morning_brief: datetime | None = None
_last_weekly_report: datetime | None = None


def maybe_run_morning_brief():
    """Run morning brief once per calendar day (first cycle after midnight)."""
    global _last_morning_brief
    now = datetime.now()
    if _last_morning_brief is None or _last_morning_brief.date() < now.date():
        try:
            sys.path.insert(0, str(LORE_ROOT))
            from lore import briefing, evolution, routing as lore_routing
            report = evolution.build_evolution_report()
            _, brief_text = briefing.build_and_format_morning_brief(
                evolution_report=report,
                proposal_summary=report.get("proposal_summary"),
            )
            brief_path = Path("/var/log/lore-morning-brief.txt")
            brief_path.write_text(f"[{now.strftime('%Y-%m-%d')}]\n\n{brief_text}\n")
            lore_routing.log_router_event(
                task_type="morning_brief",
                model="gpt-4.1",
                status="ok",
                description="Daemon daily morning brief",
                accepted=True,
            )
            log("INFO", f"Morning brief written → {brief_path}")
            _last_morning_brief = now
        except Exception as e:
            log("WARN", f"Morning brief failed: {e}")


def maybe_run_weekly_report():
    """Run weekly canon maintenance report once every 7 days."""
    global _last_weekly_report
    now = datetime.now()
    if _last_weekly_report is None or (now - _last_weekly_report).days >= 7:
        try:
            sys.path.insert(0, str(LORE_ROOT))
            from lore import maintenance, routing as lore_routing
            report = maintenance.build_weekly_report()
            text = maintenance.format_weekly_report(report)
            report_path = Path("/var/log/lore-weekly-report.txt")
            report_path.write_text(f"[{now.strftime('%Y-%m-%d')}]\n\n{text}\n")
            lore_routing.log_router_event(
                task_type="weekly_report",
                model="gpt-4.1",
                status="ok",
                description="Daemon weekly canon maintenance report",
                accepted=True,
            )
            log("INFO", f"Weekly report written → {report_path}")
            _last_weekly_report = now
        except Exception as e:
            log("WARN", f"Weekly report failed: {e}")


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    PID_FILE.write_text(str(os.getpid()))
    init_results()
    log("INFO", f"LORE Research Daemon starting — wiki={WIKI_DIR} sleep={SLEEP_MINUTES}m deepseek_gate={USE_DEEPSEEK_GATE}")

    while not _shutdown:
        # Scheduled operator tasks (non-blocking, run inline)
        maybe_run_morning_brief()
        maybe_run_weekly_report()

        try:
            research_cycle()
        except Exception as e:
            log("ERROR", f"Unhandled cycle error: {e}")
            _stats["errors"] += 1

        if _shutdown:
            break
        log("INFO", f"Sleeping {SLEEP_MINUTES}m — stats: {_stats}")
        for _ in range(SLEEP_MINUTES * 60):
            if _shutdown:
                break
            time.sleep(1)

    log("INFO", "Daemon shutting down cleanly")
    try:
        PID_FILE.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    main()
