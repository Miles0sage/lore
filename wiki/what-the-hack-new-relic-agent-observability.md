---
backlinks: []
concepts:
- multi-agent orchestration
- custom telemetry spans
- ai quality assurance
- opentelemetry
- microsoft agent framework
- new relic
- ai agent observability
- prompt injection detection
- ci/cd quality gates
- microsoft foundry guardrails
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: what-the-hack-new-relic-agent-observability
sources:
- raw/2026-04-05-agent-observability-github.md
status: published
title: What The Hack - New Relic Agent Observability
updated: '2026-04-05'
---

# What The Hack - New Relic Agent Observability

## Introduction
This technical workshop details the development of AI agents using the Microsoft Agent Framework, instrumented with OpenTelemetry for full-stack observability powered by New Relic. The curriculum guides engineers from initial prototyping to deploying production-ready AI systems, emphasizing real-time tracing, performance monitoring, and automated quality evaluation.

## Scenario Architecture
Participants assume the role of CTO for WanderAI, a travel planning startup. The objective is to architect an AI-powered travel planning assistant that generates personalized itineraries from customer preference inputs. The system requires comprehensive visibility to satisfy operational and investor requirements across four dimensions:
- Recommendation accuracy and output quality
- Response latency and system performance
- Debuggability and failure tracing
- Reliability and trustworthiness validation

## Implementation Challenges
The workshop is structured into eight progressive implementation modules:

- **Challenge 00: Prerequisites** - Environment setup and dependency configuration.
- **Challenge 01: Foundation** - Microsoft Agent Framework architecture, tool integration, agent design, and multi-agent orchestration.
- **Challenge 02: MVP Development** - Flask web application deployment, initial AI agent implementation with tool-calling, and request routing configuration.
- **Challenge 03: Observability Integration** - Initialization of built-in OpenTelemetry, console trace/metric verification, and telemetry export configuration to New Relic.
- **Challenge 04: Custom Telemetry** - Implementation of custom spans for tools and routes, business logic metric recording, and log-to-trace context correlation in New Relic.
- **Challenge 05: Production Optimization** - Application of monitoring best practices, custom dashboard construction, alert configuration, and AI response quality analysis.
- **Challenge 06: Quality Assurance** - Development of evaluation tests, CI/CD quality gate implementation to block substandard outputs, and continuous AI quality measurement.
- **Challenge 07: Platform Security Baseline** - Configuration of Microsoft Foundry Guardrails, validation of intervention points and risk mitigation actions, and platform-level security telemetry monitoring.
- **Challenge 08: Application Security Controls** - Integration of prompt injection detection, enforcement of request flow blocking, and instrumentation of custom security validation controls.

## Learning Objectives
Completion of the workshop delivers proficiency in:
- AI Agent Architecture for production deployment
- Multi-agent orchestration using the Microsoft Agent Framework
- Comprehensive instrumentation with OpenTelemetry
- Telemetry ingestion and analysis via New Relic
- Production monitoring best practices for AI workloads
- AI quality assurance and automated output gating
- Security controls against prompt injection and reliability risks
- End-to-end development from prototype to production service

## Key Concepts
[[Microsoft Agent Framework]]
[[OpenTelemetry]]
[[New Relic]]
[[AI Agent Observability]]
[[Multi-Agent Orchestration]]
[[Custom Telemetry Spans]]
[[AI Quality Assurance]]
[[Microsoft Foundry Guardrails]]
[[Prompt Injection Detection]]
[[CI/CD Quality Gates]]

## Sources
- GitHub Repository: [microsoft/WhatTheHack - 073-NewRelicAgentObservability](https://github.com/microsoft/WhatTheHack/blob/master/073-NewRelicAgentObservability/README.md)
- Commit: `21a9eb5` (Mar 25, 2026)
- Pull Request: [#1090](https://github.com/microsoft/WhatTheHack/pull/1090)
- Contributors: harrykimpel, MatthewCalder-msft, jrzyshr
