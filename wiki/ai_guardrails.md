---
backlinks: []
concepts:
- dry-validation
- ruby-gem
- version-control
- auto-fix-hooks
- ci-cd-pipeline
- schema-validation
- ai-guardrails
- rspec-testing
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: ai_guardrails
sources:
- raw/2026-04-05-ai-guardrails-github.md
status: published
title: ai_guardrails
updated: '2026-04-05'
---

# ai_guardrails

## Overview
`ai_guardrails` is a Ruby gem developed by `logicbunchhq` that provides schema validation and structural guardrails for AI application outputs. The library leverages `dry-validation` for contract-based data checking and includes automated remediation hooks for malformed JSON and schema responses.

## Repository Metadata
- **Repository URL:** `https://github.com/logicbunchhq/ai_guardrails`
- **Primary Maintainer:** `faisalrazap`
- **Branches:** 1 (`main`)
- **Tags:** 1
- **Total Commits:** 13
- **Latest Commit:** `40761a32298f2fe9d1bb9f997dc1d2d1edcc187c` (Dec 16, 2025)

## Directory Structure
The codebase adheres to standard Ruby gem conventions:
- `.github/workflows`: CI pipeline configuration
- `bin`: Executable scripts
- `lib`: Core implementation, including `AiGuardrails::SchemaValidator`
- `sig`: Type signature definitions
- `spec`: RSpec test suite
- `.gitignore`: Version control exclusion rules
- `.rspec`: RSpec configuration

## Core Features
- **Schema Validation:** Implemented via `AiGuardrails::SchemaValidator` using the `Dry::Validation` contract API for strict type and structure enforcement.
- **Auto-Fix Hooks:** Integrated JSON and Schema Auto-Fix Hooks to automatically correct invalid AI outputs.
- **Schema Hints:** Configuration option `schema_hint` available to guide validation behavior.
- **DSL Management:** Documentation references a domain-specific language for rule definition; recent updates removed redundant DSL output prints.

## Commit History & Versioning
Development progressed through documented releases and stability improvements:
- **Initial Scaffold & Validation (`81f906820172425ba58f1bb065b3f9871656e0e9`, Nov 28, 2025):** Added `AiGuardrails::SchemaValidator`, integrated `dry-validation` dependency, implemented RSpec tests, and resolved Rubocop offenses. Module naming refactored to align with Rails conventions.
- **Stability & CI Updates (`a3f0c3c339a29bd4fe7ba204cda5d34ede1995eb`, Dec 12, 2025):** Added CI workflow, configured coverage setup, updated `Gemfile` and `gemspec` for multiple Ruby versions, removed `byebug` gem, updated `Gem::Specification`, and logged changes with dates/tags in `CHANGELOG.md`.
- **Documentation & Final Cleanup (`40761a32298f2fe9d1bb9f997dc1d2d1edcc187c`, Dec 16, 2025):** Updated documentation, examples, and removed redundant DSL output prints.
- **Version Progression:** `1.1.5` → `1.1.6` (CI/Bundler alignment) → `1.2.0` (squashed commits and changelog updates).

## CI/CD & Testing
- Automated GitHub Actions workflow configured for multiple Ruby versions.
- Test coverage pipeline integrated into CI.
- RSpec suite validates schema contracts and core validation logic.
- CI Ruby and Bundler versions synchronized with local development environments as of Dec 12, 2025.

## Key Concepts
[[ai-guardrails]]
[[schema-validation]]
[[dry-validation]]
[[ruby-gem]]
[[auto-fix-hooks]]
[[ci-cd-pipeline]]
[[rspec-testing]]
[[version-control]]

## Sources
- `2026-04-05-ai-guardrails-github.md` (GitHub repository interface, file tree, and commit history for `logicbunchhq/ai_guardrails`)
