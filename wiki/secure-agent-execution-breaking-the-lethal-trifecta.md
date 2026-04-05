# Secure Agent Execution — Breaking the Lethal Trifecta

The lethal trifecta describes the three conditions that combine to make an AI agent catastrophically dangerous in production:

1. **Persistent side-effects** — the agent can write files, call APIs, send messages, modify state
2. **Ambient authority** — the agent inherits all the credentials and permissions of its host process
3. **Prompt injection surface** — the agent processes untrusted input that can hijack its goals

When all three are present simultaneously, a single malicious prompt can cause the agent to exfiltrate data, modify systems, or spend unlimited budget. Breaking any one of the three eliminates the catastrophic risk class.

## Pattern: Sandbox-First Execution

Every agent tool invocation should execute in an isolated environment:

- **No ambient credentials** — pass only the minimum scoped token needed for the specific task
- **Ephemeral filesystem** — write to a tmpfs or container overlay, not the host
- **Network egress filtering** — allowlist only the endpoints the agent legitimately needs
- **Resource caps** — CPU, memory, and wall-clock time limits enforced by the runtime

## Recommended Runtimes

| Runtime | Isolation | Startup | Use case |
|---|---|---|---|
| Docker (rootless) | Process + filesystem | ~200ms | General agent tasks |
| Firecracker microVM | Full VM | ~125ms | High-sensitivity tasks |
| gVisor (runsc) | Kernel syscall intercept | ~50ms | Balance of speed/safety |
| Wasm (WASI) | Capability-based | ~5ms | Pure compute, no I/O |

## Pattern: Least-Privilege Tool Injection

Never give an agent a swiss-army tool set. Give it exactly the tools needed for the current task and revoke them when done. The Warden archetype embodies this: it holds the keyring and issues keys per task, not per agent lifetime.

## Pattern: Input Validation Gate

All external content entering the agent context — web scrapes, emails, documents, API responses — must pass through a prompt injection filter before reaching the reasoning loop. The Sentinel archetype sits at this boundary.

## Related Archetypes

- The Warden (least-privilege enforcement)
- The Sentinel (input validation, injection detection)
- The Breaker (circuit breaker for uncontrolled retries)

## Sources

- OWASP Top 10 for LLM Applications (2025) — LLM08: Excessive Agency
- Simon Willison: "Prompt injection and the lethal trifecta" (2024)
- Anthropic: Claude's Constitution and tool-use safety guidelines
- LangChain security model documentation
