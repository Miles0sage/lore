---
backlinks: []
concepts:
- model-routing
- circuit-breaker-pattern-for-ai-agents
- dead-letter-queue-pattern-for-ai-agents
- runtime-observability
- dynamic-tool-routing
- ai-agent-reliability
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: tool-health-monitoring-for-ai-agents
sources:
- raw/2026-04-05-tool-health-monitoring.md
status: published
title: Tool Health Monitoring for AI Agents
updated: '2026-04-05'
---

# Tool Health Monitoring for AI Agents

## Overview
Tool Health Monitoring is a runtime observability pattern that tracks the reliability, latency, and error rates of every tool available to an AI agent. Rather than treating tool failures as unexpected events, this pattern makes tool health a first-class system metric, enabling dynamic routing, proactive circuit breaking, and capacity planning.

## Why It Matters
AI agents are only as reliable as their tools. An agent utilizing multiple external APIs will experience constant tool degradation, including GitHub rate limits, Stripe downtime, and Supabase connection pool exhaustion. Without health monitoring, the agent degrades silently by retrying failing tools, burning tokens, and returning incorrect answers. With health monitoring, the system adapts in real time.

## Core Metrics Per Tool
Every tool must be tracked against the following metrics:
- **Success rate**: Rolling window (e.g., last 100 calls). Serves as the primary health signal.
- **P50/P95/P99 latency**: Identifies slow tools before they become blocking calls.
- **Error rate by type**: Categorized by 429 (rate limit), 5xx (server error), timeout, and malformed response.
- **Circuit state**: Tracks CLOSED / OPEN / HALF_OPEN states derived from the circuit breaker pattern.
- **Call volume**: Requests per minute used to detect unusual traffic spikes.

## Implementation Architecture
The following Python class demonstrates a foundational implementation using `defaultdict` and `deque` for rolling metric windows:

```python
class ToolHealthMonitor:
    def __init__(self, window_size=100):
        self.metrics = defaultdict(lambda: {
            "calls": deque(maxlen=window_size),  # bool: success/fail
            "latencies": deque(maxlen=window_size),
            "errors": defaultdict(int),
            "circuit_state": "CLOSED"
        })
    
    async def call_with_tracking(self, tool_name, fn, *args, **kwargs):
        start = time.time()
        try:
            result = await fn(*args, **kwargs)
            self.record_success(tool_name, time.time() - start)
            return result
        except Exception as e:
            self.record_failure(tool_name, type(e).__name__, time.time() - start)
            raise
    
    def health_report(self) -> dict:
        return {
            tool: {
                "success_rate": sum(m["calls"]) / len(m["calls"]) if m["calls"] else 1.0,
                "p95_latency": percentile(m["latencies"], 95),
                "circuit": m["circuit_state"]
            }
            for tool, m in self.metrics.items()
        }
```

## Dynamic Routing Based on Health
Health scores drive intelligent routing decisions to maintain system stability:
- If `search_exa` success rate drops below 0.7, route search queries to `search_perplexity`.
- If `github_api` P95 latency exceeds 5s, activate an aggressive caching layer.
- If `openrouter_qwen` error rate spikes, escalate tasks to a more reliable model.

Tool health monitoring feeds directly into the model routing layer, enabling the agent system to self-heal.

## Health Dashboard
System health is exposed via a live endpoint for operational visibility:

```bash
GET /health/tools
{
  "github_api": {"success_rate": 0.97, "p95_ms": 340, "circuit": "CLOSED"},
  "openrouter_qwen": {"success_rate": 0.62, "p95_ms": 8200, "circuit": "OPEN"},
  "supabase": {"success_rate": 0.99, "p95_ms": 45, "circuit": "CLOSED"}
}
```

## Integration Points
- **Circuit Breaker**: The health monitor supplies the failure counter that triggers circuit state transitions.
- **Dead Letter Queue**: Health degradation predicts DLQ growth, enabling alerts before queues overflow.
- **Model Routing**: Automatically routes tasks away from degraded tools.
- **Alerting**: Pages on-call engineers when any tool drops below a 0.85 success rate for 5+ minutes.

## Production Implementations
- **LangSmith**: Provides built-in tool call tracing with latency and error tracking.
- **Langfuse**: Open-source, self-hostable alternative to LangSmith.
- **Prometheus + Grafana**: Standard observability stack for custom tool health metrics.
- **Custom middleware**: Many production agent systems wrap every tool invocation in a shared tracking layer before routing or retry logic.

## Key Concepts
[[runtime-observability]]
[[circuit-breaker-pattern-for-ai-agents]]
[[dead-letter-queue-pattern-for-ai-agents]]
[[model-routing]]
[[dynamic-tool-routing]]
[[ai-agent-reliability]]

## Sources
- `2026-04-05-tool-health-monitoring.md`
