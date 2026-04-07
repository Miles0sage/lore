---
id: react-loop-pattern
title: ReAct Loop Pattern for AI Agents
tags:
  - react
  - reasoning
  - tool-use
  - agent-loop
  - production
---

# ReAct Loop Pattern for AI Agents

## What It Is

ReAct (Reasoning + Acting) is the foundational loop for tool-using AI agents. The agent alternates between reasoning about what to do and executing actions (tool calls), updating its context with observations after each step.

```
Thought → Action → Observation → Thought → Action → Observation → ... → Final Answer
```

This is the architecture behind most modern agent frameworks. Understanding it directly lets you implement agents without framework overhead and debug them when they misbehave.

## Implementation

```bash
lore scaffold react_loop
```

The core loop:

```python
agent = ReActAgent(tools=[search_tool, calculator_tool, file_tool])
result = await agent.run("What is the population of Tokyo divided by 1000?")
```

Internally:

```
Thought: I need to find Tokyo's population, then divide by 1000.
Action: search("Tokyo population 2024")
Observation: Tokyo population is approximately 13.96 million.
Thought: Now I divide 13,960,000 by 1000.
Action: calculator("13960000 / 1000")
Observation: 13960.0
Thought: I have the answer.
Final Answer: 13,960
```

## Production Considerations

A bare ReAct loop has several failure modes in production:

**Infinite loops**: The agent can get stuck reasoning in circles. Add a `max_steps` hard stop.

**Hallucinated tool calls**: The model may call tools that don't exist or with wrong parameters. Add input validation at the tool boundary.

**No cost guard**: Each thought-action cycle burns tokens. Wire a `CostGuard` around the loop.

**No circuit breaker**: If a tool fails repeatedly, the loop will keep calling it. Wrap tool calls with a `CircuitBreaker`.

**No observability**: Without structured logs per step, debugging a failed run is nearly impossible. Log each Thought/Action/Observation triple.

## Reliability Additions

```python
agent = ReActAgent(
    tools=[search_tool, calculator_tool],
    max_steps=15,                          # hard stop
    cost_guard=CostGuard(50_000),          # token budget
    circuit_breaker=CircuitBreaker("tools") # tool failure isolation
)
```

## When to Use It

- Single-agent tasks requiring tool use
- Research, calculation, data retrieval pipelines
- Anywhere you want transparent reasoning traces

For multi-agent coordination, see `supervisor_worker`. For quality gates on outputs, see `reviewer_loop`.
