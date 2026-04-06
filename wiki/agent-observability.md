---
backlinks: []
concepts:
- tool-registry
- agent-observability
- tavily-api
- rag-triad-evaluation
- prompt-provider
- otel-collector
- open-telemetry
- chat-cli
- langfuse-integration
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: agent-observability
sources:
- raw/2026-04-05-opentelemetry-for-ai-agents-github.md
status: published
title: agent-observability
updated: '2026-04-05'
---

# agent-observability

## Overview
The `agent-observability` repository (https://github.com/carllapierre/agent-observability) provides a modular framework for instrumenting, evaluating, and monitoring AI agent systems. The project integrates OpenTelemetry for distributed tracing, implements RAG evaluation triads, and includes a CLI interface with structured user feedback mechanisms. The repository currently maintains 1 branch, 0 tags, 27 total commits, 3 stars, and 0 forks.

## Architecture & Components
The codebase is organized into discrete modules targeting specific observability and execution layers:
- `agent-cli`: Command-line interface for agent interaction. Implements a feedback mechanism with dedicated keywords and methods for submission and response tracking.
- `agent-core`: Shared runtime logic and foundational utilities supporting telemetry integration and agent execution.
- `agent-evals`: Evaluation framework focused on the RAG Triad. Refactored to clarify context relevance scoring by utilizing retriever input as the primary evaluation metric. Deprecated NLP and trajectory evaluators have been removed.
- `agent-telemetry`: OpenTelemetry integration layer. Manages Collector configuration for trace processing and routing, includes a transform processor for Langfuse observation types, and maintains a `ToolRegistry` supporting instance-based tool registration.
- `demo/manual-instrumented-agent`: Reference implementation demonstrating manual instrumentation patterns.
- `documentation/assets`: Static resources and visual assets for project documentation.

## Development History
Recent development activity (January 2026) focused on evaluation refinement, telemetry routing, and user feedback integration:
- **Jan 29, 2026** (`ac31f4c`): Fixed formatting for the RAG Triad evaluator command in the README.
- **Jan 22, 2026**: Added user feedback mechanisms to `ChatCLI` and updated settings across `agent-cli` and `agent-core`. Introduces feedback keywords and methods to handle user feedback submission, enhancing user interaction and response tracking.
- **Jan 21, 2026**: Refactored Triad evaluators in `agent-evals` to clarify context relevance evaluation using retriever input for scoring. Updated README to remove outdated NLP and trajectory evaluator sections.
- **Jan 19, 2026**: Refactored OpenTelemetry Collector configuration in `agent-telemetry` to enhance trace processing and routing. Introduced a new transform processor for Langfuse observation types, updated `ToolRegistry` for instance-based tool registration, removed deprecated tools, and integrated Tavily settings into the `DemoAgent`.
- **Jan 16, 2026**: Added new tools for card dealing and web searching, integrated the Tavily API, and updated demo agent configuration. Enhanced prompt handling by adding variable substitution support in `IPromptProvider` and its implementations, updated Docker Compose configuration to include external networks, and introduced a method to format registered tools as text for prompts in `ToolRegistry`.
- **Jan 5, 2026**: Added OTEL Collector configuration to `.gitignore`.

## Configuration & Infrastructure
Deployment and environment management are handled through standard configuration files:
- `docker-compose.yml`: Orchestrates the agent stack with external network support and prompt variable substitution.
- `env.template`: Defines required environment variables for local and production deployments.
- `.gitignore`: Excludes telemetry artifacts, OTEL Collector data, and local environment files.

## Key Concepts
[[agent-observability]]
[[open-telemetry]]
[[rag-triad-evaluation]]
[[langfuse-integration]]
[[tool-registry]]
[[otel-collector]]
[[prompt-provider]]
[[chat-cli]]
[[tavily-api]]

## Sources
- https://github.com/carllapierre/agent-observability
