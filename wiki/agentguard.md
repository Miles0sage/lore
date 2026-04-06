---
backlinks: []
concepts:
- dotnet-solution-architecture
- ci-cd-configuration
- microsoft-defender-ai
- prompt-injection-blocking
- opentelemetry-integration
- agentguard
- error-propagation
- agentic-ai-security
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: agentguard
sources:
- raw/2026-04-05-agentic-ai-security-guardrails-github.md
status: published
title: AgentGuard
updated: '2026-04-05'
---

# AgentGuard

AgentGuard is a public GitHub repository maintained by `filipw` that provides security guardrails and observability infrastructure for agentic AI systems. The project is built on a .NET solution architecture and includes core libraries, sample implementations, documentation, and CI/CD configurations.

## Repository Metadata
- **URL:** https://github.com/filipw/AgentGuard
- **Visibility:** Public
- **Statistics:** 5 stars, 0 forks, 2 branches, 3 tags
- **Total Commits:** 53
- **Latest Commit:** `5bd77f8` (Merge pull request #1 from `filipw/otel`) - April 2, 2026
- **Initial Commit:** March 14, 2026

## Project Structure & Development History
The repository is organized into the following directories, with recent development activity focused on documentation, OpenTelemetry (OTEL) integration, and rule engine improvements:

- **`src`**: Core library implementation. Last updated April 2, 2026 ("added OTEL integration").
- **`tests`**: Test suite. Last updated April 2, 2026 ("added OTEL integration").
- **`samples`**: Example implementations. Last updated March 31, 2026 ("renamed BlockPromptInjectionWithOnnx to BlockPromptInjectionWithDefender and added sensible defaults, website updates").
- **`docs`**: Project documentation. Last updated April 2, 2026 ("added docs").
- **`website`**: Documentation site source. Last updated April 2, 2026 ("added docs").
- **`eng`**: Engineering and build tooling. Last updated March 28, 2026 ("improved error propagation from all rules").
- **`.github`**: GitHub Actions and repository configuration. Last updated March 31, 2026 ("fixed pages publishing").

Build and configuration files include:
- `AgentGuard.slnx`: Solution file, reworked March 24, 2026.
- `Directory.Build.props`: Version management, updated April 2, 2026.
- `Directory.Build.targets`: CI warning configuration, updated March 17, 2026.
- `Directory.Packages.props`: Dependency management, updated April 2, 2026.
- `global.json`: SDK version pinning, updated March 14, 2026.
- `nuget.config`: Package source configuration, created March 14, 2026.
- `.editorconfig` & `.gitignore`: Code style and ignore rules, last modified March 14 and April 1, 2026, respectively.

## Core Capabilities
Based on commit history and directory structure, the framework implements the following technical components:

- **Prompt Injection Mitigation**: Includes rule implementations for blocking prompt injection. The implementation was transitioned from an ONNX-based model (`BlockPromptInjectionWithOnnx`) to a Microsoft Defender-based approach (`BlockPromptInjectionWithDefender`) with sensible defaults.
- **Observability Integration**: Native OpenTelemetry (OTEL) support added to the core library, test suite, and package dependencies as of April 2, 2026.
- **Rule Engine & Error Handling**: Engineered error propagation mechanisms across all security rules to improve fault tolerance and debugging.
- **CI/CD & Build System**: Configured to suppress warning failures in continuous integration pipelines (`do not fail on warnings in CI`), with standardized package and version management via MSBuild directory props/targets.

## Key Concepts
[[agentguard]]
[[agentic-ai-security]]
[[prompt-injection-blocking]]
[[opentelemetry-integration]]
[[error-propagation]]
[[ci-cd-configuration]]
[[dotnet-solution-architecture]]
[[microsoft-defender-ai]]

## Sources
- `filipw/AgentGuard` GitHub Repository: https://github.com/filipw/AgentGuard
- Commit History & File Structure: `filipw/AgentGuard` (53 commits, latest `5bd77f8` on April 2, 2026)
