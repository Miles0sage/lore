---
backlinks: []
concepts:
- non-deterministic execution
- otlp exporter
- opentelemetry
- span hierarchy
- token cost tracking
- llm instrumentation
- ai agent observability
- distributed tracing
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: how-to-monitor-ai-agents-in-production-with-opentelemetry
sources:
- raw/2026-04-05-opentelemetry-for-ai-agents-web.md
status: published
title: How to Monitor AI Agents in Production with OpenTelemetry
updated: '2026-04-05'
---

# How to Monitor AI Agents in Production with OpenTelemetry

## Overview
AI agents are deployed to production faster than teams can establish monitoring strategies. Autonomous systems execute unpredictable decision chains: an agent calls an LLM, the LLM invokes a tool, the tool hits an API, and the API may trigger another LLM. Traditional monitoring fails to track these non-linear workflows. OpenTelemetry (OTel) provides a vendor-neutral, single-instrumentation layer for structured traces, metrics, and logs, exportable to any OTLP-compatible backend.

**Source:** [How to Monitor AI Agents in Production with OpenTelemetry](https://oneuptime.com/blog/post/2026-03-14-how-to-monitor-ai-agents-in-production/view) by Jamie Mallers (@mallersjamie), published Mar 14, 2026.

## Limitations of Standard APM
Traditional Application Performance Monitoring (APM) is optimized for request-response HTTP services. It falls short for AI agents due to:
- **Non-deterministic execution paths:** Identical inputs can trigger entirely different tool call chains based on LLM decisions. Trace shapes cannot be predicted in advance.
- **Invisible token costs:** Standard APM tracks latency but not token consumption. An LLM call processing 50,000 tokens (e.g., embedding an entire database schema in context) incurs significant financial cost that standard metrics miss.
- **Deep, branching tool call traces:** Agents execute complex sequences (search, parse, code execution, failure, retry, alternate tool). Traditional span hierarchies become unmanageable.
- **Wild latency distributions:** LLM response times range from 200ms to 30 seconds depending on output length, model load, and provider stability. Percentile-based alerting requires adjusted thresholds.

## OpenTelemetry Instrumentation Model
The recommended mental model structures each reasoning step as a span, with the full agent execution as the root span.

```plaintext
Agent Run (root span)
  |-- LLM Call (child span)
  |     |-- attributes: model, tokens_in, tokens_out, temperature
  |-- Tool Call: search_database (child span)
  |     |-- attributes: tool_name, parameters, result_summary
  |-- LLM Call (child span)
  |     |-- attributes: model, tokens_in, tokens_out
  |-- Tool Call: send_email (child span)
  |     |-- attributes: tool_name, parameters, success
  |-- Final Response (child span)
```

## Implementation Guide

### Step 1: Install the OpenTelemetry SDK
**Python:**
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

**TypeScript/Node.js:**
```bash
npm install @opentelemetry/api @opentelemetry/sdk-node @opentelemetry/exporter-trace-otlp-http
```

### Step 2: Initialize the Tracer
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({
    "service.name": "my-ai-agent",
    "service.version": "1.0.0",
    "deployment.environment": "production"
})

provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint="https://your-otlp-endpoint/v1/traces")
)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("ai-agent")
```

### Step 3: Instrument the Agent Run
Wrap the entire execution loop in a root span to capture input, model, output length, and success state.
```python
def run_agent(user_input: str) -> str:
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("agent.input", user_input[:500])  # Truncate for safety
        span.set_attribute("agent.model", "gpt-4")

        result = agent_loop(user_input)

        span.set_attribute("agent.output_length", len(result))
        span.set_attribute("agent.success", True)
        return result
```

### Step 4: Instrument LLM Calls
Capture model, message count, input character count, and duration for every LLM invocation.
```python
def call_llm(messages: list, model: str = "gpt-4") -> str:
    with tracer.start_as_current_span("llm.call") as span:
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.message_count", len(messages))

        # Estimate input tokens (or use tiktoken for accuracy)
        input_text = " ".join(m["content"] for m in messages)
        span.set_attribute("llm.input_chars", len(input_text))

        start = time.time()
        response = openai.chat.completions.create(
            model=model,
            messages=messages
        )
        duration = time.time() - start

        # Token usage from the A
```

## Key Concepts
[[OpenTelemetry]]
[[AI Agent Observability]]
[[Distributed Tracing]]
[[Token Cost Tracking]]
[[Non-Deterministic Execution]]
[[OTLP Exporter]]
[[Span Hierarchy]]
[[LLM Instrumentation]]

## Sources
- Mallers, J. (2026-03-14). *How to Monitor AI Agents in Production with OpenTelemetry*. OneUptime Blog. Retrieved from https://oneuptime.com/blog/post/2026-03-14-how-to-monitor-ai-agents-in-production/view
