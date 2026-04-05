#!/usr/bin/env python3
"""
LORE PreCompact Hook — Context Mining Before Compression

Before Claude's context is compressed, this hook:
1. Extracts concepts mentioned but not yet in the Codex
2. Writes them as raw sources for the nightly daemon to research
3. Logs the session's architectural decisions

Install in ~/.claude/settings.json:
{
  "hooks": {
    "PreCompact": [{
      "hooks": [{"type": "command", "command": "python3 /root/lore-mcp/hooks/lore_precompact.py"}]
    }]
  }
}
"""

import json
import os
import re
import sys
import time
from pathlib import Path

DEFAULT_WORKSPACE = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(os.environ.get("LORE_WIKI_DIR", str(DEFAULT_WORKSPACE))).expanduser()
if WORKSPACE_ROOT.name == "wiki":
    WORKSPACE_ROOT = WORKSPACE_ROOT.parent

WIKI_RAW_DIR = WORKSPACE_ROOT / "raw"
LOG_FILE = Path("/var/log/lore-precompact.log")

# Concepts the hook will watch for as potential wiki gaps
CONCEPT_PATTERNS = [
    r'\b(langfuse|agentops|helicone|langsmith|arize|braintrust)\b',
    r'\b(langgraph|crewai|autogen|dspy|llama.?index)\b',
    r'\b(mem0|langmem|claude.?mem|zep)\b',
    r'\b(kuzu|neo4j|neptune|graph.?rag)\b',
    r'\b(lora|fine.?tun|qlora|dpo|rlhf)\b',
    r'\b(speculative.?decoding|flash.?attention|kv.?cache)\b',
    r'\b(function.?calling|tool.?use|structured.?output)\b',
    r'\b(agentic.?rag|corrective.?rag|self.?rag|adaptive.?rag)\b',
]

# Load known wiki articles to detect gaps
def get_known_articles() -> set[str]:
    wiki_dir = WORKSPACE_ROOT / "wiki"
    if not wiki_dir.exists():
        return set()
    return {p.stem.lower().replace("-", " ") for p in wiki_dir.glob("*.md")}


def extract_concepts(text: str) -> list[str]:
    found = set()
    for pattern in CONCEPT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.update(m.lower() for m in matches)
    return list(found)


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Get context summary from the hook
    context = hook_input.get("summary", "") + " " + hook_input.get("messages", "")

    if not context.strip():
        sys.exit(0)

    known = get_known_articles()
    concepts = extract_concepts(context)

    # Find concepts not in the wiki
    gaps = [c for c in concepts if c not in known]

    if gaps:
        # Write as a raw source for the nightly daemon
        timestamp = time.strftime("%Y-%m-%d")
        slug = f"{timestamp}-precompact-gaps"
        raw_file = WIKI_RAW_DIR / f"{slug}.md"

        content = f"# Concepts from session context (PreCompact mining)\n\n"
        content += f"*Extracted: {time.strftime('%Y-%m-%d %H:%M')}*\n\n"
        content += "The following concepts were mentioned in this session but may not have full Codex coverage:\n\n"
        for gap in sorted(gaps):
            content += f"- {gap}\n"
        content += "\nResearch and compile articles for any of these that are not yet in the Codex.\n"

        try:
            WIKI_RAW_DIR.mkdir(parents=True, exist_ok=True)
            raw_file.write_text(content)

            log_entry = f"{time.strftime('%Y-%m-%d %H:%M')} PreCompact: {len(gaps)} gaps extracted: {', '.join(gaps[:5])}\n"
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a") as f:
                f.write(log_entry)
        except Exception:
            pass

    sys.exit(0)


if __name__ == "__main__":
    main()
