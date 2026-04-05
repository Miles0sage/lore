#!/usr/bin/env python3
"""
LORE PreToolUse Hook — Architectural Guardian

Intercepts Claude Code tool calls and warns when dangerous patterns
are being built without the required reliability scaffolding.

Install in ~/.claude/settings.json:
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash",
      "hooks": [{"type": "command", "command": "python3 /root/lore-mcp/hooks/lore_pretooluse.py"}]
    }]
  }
}

Exit codes:
  0 = proceed
  1 = warn (Claude sees message, can continue)
  2 = block (Claude must fix before proceeding)
"""

import json
import re
import sys

# Patterns that require circuit breakers
NEEDS_CIRCUIT_BREAKER = [
    r"while True.*retry",
    r"for.*retry.*range",
    r"requests\.get|requests\.post|httpx\.get|httpx\.post",
    r"aiohttp\.ClientSession",
    r"openai\..*\.create",
    r"anthropic\..*\.create",
]

# Patterns that need DLQ when doing batch processing
NEEDS_DLQ = [
    r"for.*task.*in.*tasks",
    r"asyncio\.gather.*tasks",
    r"ThreadPoolExecutor|ProcessPoolExecutor",
]

# Infinite loop risks
INFINITE_LOOP_RISK = [
    r"while True",
    r"while not done",
    r"while.*running",
]

# Circuit breaker presence indicators
HAS_CIRCUIT_BREAKER = [
    r"CircuitBreaker|circuit_breaker",
    r"failure_threshold",
    r"CLOSED.*OPEN.*HALF_OPEN",
    r"max_retries\s*=\s*[1-9]",
]

HAS_DLQ = [
    r"dead_letter|dlq|DeadLetter",
    r"ErrorEnvelope",
    r"max_retries.*[3-9]",
]


def check_code(code: str) -> list[dict]:
    """Check code for missing reliability patterns."""
    warnings = []

    has_breaker = any(re.search(p, code, re.IGNORECASE) for p in HAS_CIRCUIT_BREAKER)
    has_dlq = any(re.search(p, code, re.IGNORECASE) for p in HAS_DLQ)
    has_infinite = any(re.search(p, code, re.IGNORECASE) for p in INFINITE_LOOP_RISK)
    needs_breaker = any(re.search(p, code, re.IGNORECASE) for p in NEEDS_CIRCUIT_BREAKER)
    needs_dlq = any(re.search(p, code, re.IGNORECASE) for p in NEEDS_DLQ)

    if needs_breaker and not has_breaker:
        warnings.append({
            "level": "warn",
            "pattern": "circuit_breaker",
            "character": "The Breaker",
            "message": (
                "LORE: External API calls detected without a circuit breaker. "
                "Systems without The Breaker experience 76% failure rates in production. "
                "Run: lore_scaffold circuit_breaker"
            )
        })

    if has_infinite and not has_breaker:
        warnings.append({
            "level": "warn",
            "pattern": "circuit_breaker",
            "character": "The Breaker",
            "message": (
                "LORE: Infinite loop detected without failure threshold. "
                "Add max_retries or CircuitBreaker to prevent runaway token spend. "
                "Run: lore_scaffold circuit_breaker"
            )
        })

    if needs_dlq and not has_dlq:
        warnings.append({
            "level": "warn",
            "pattern": "dead_letter_queue",
            "character": "The Archivist",
            "message": (
                "LORE: Batch task processing without a dead letter queue. "
                "Failed tasks will be silently dropped. "
                "Run: lore_scaffold dead_letter_queue"
            )
        })

    return warnings


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only check Bash and Write tool calls that contain code
    if tool_name not in ("Bash", "Write", "Edit"):
        sys.exit(0)

    # Extract code content
    code = ""
    if tool_name == "Bash":
        code = tool_input.get("command", "")
    elif tool_name in ("Write", "Edit"):
        code = tool_input.get("content", "") + tool_input.get("new_string", "")

    # Only check Python files
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        if not file_path.endswith(".py"):
            sys.exit(0)

    if not code or len(code) < 100:
        sys.exit(0)

    warnings = check_code(code)

    if warnings:
        messages = [w["message"] for w in warnings]
        print("\n".join(messages), file=sys.stderr)
        sys.exit(1)  # Warn but don't block

    sys.exit(0)


if __name__ == "__main__":
    main()
