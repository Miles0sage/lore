---
backlinks: []
concepts:
- sdk-development
- ci-cd-automation
- vector-database-integration
- prompt-injection-mitigation
- monorepo-architecture
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: rebuff
sources:
- raw/2026-04-05-prompt-injection-mitigation-github.md
status: published
title: Rebuff
updated: '2026-04-05'
---

# Rebuff

## Repository Overview
Rebuff is a software project hosted at `https://github.com/protectai/rebuff`. The repository was archived by the owner on May 16, 2025, and is currently in a read-only state. As of the final recorded activity, the project contains 345 commits across 5 branches and 4 tags, with 1.5k stars and 133 forks.

## Architecture & Directory Structure
The codebase is structured as a monorepo, established on May 28, 2023. The architecture adopts npm workspaces, isolates client SDKs into dedicated directories, and centralizes shared TypeScript interfaces between the server and client in a `types` package. Code quality is enforced via ESLint and Prettier at the root level.

Core directories and files include:
- `javascript-sdk`: Client-side JavaScript/TypeScript SDK.
- `python-sdk`: Python client SDK.
- `server`: Backend service implementation.
- `docs`: Project documentation.
- `.github/workflows`: CI/CD pipeline configurations.
- `Makefile`: Test execution and build automation.
- `.gitignore`: Version control exclusion rules.
- `LICENSE`: Project licensing (added Jun 1, 2023).

## Commit History & Recent Activity
Active development concluded in January 2024. The latest commit (`4d2fe06`) was authored by `ristomcgehee` on Jan 25, 2024. Notable updates and pull requests include:
- **Jan 25, 2024 (PR #94)**: Updated GitHub Actions to allow trusted contributors to run tests and clarified workflow execution triggers.
- **Jan 25, 2024 (PR #93)**: Implemented an SDK initialization function while preserving the public SDK constructor in the JavaScript SDK.
- **Jan 24, 2024 (PR #108)**: Fixed a missing API key configuration for Pinecone in the Python SDK.
- **Jan 22, 2024 (PR #106)**: Updated Pinecone integration usage and corresponding documentation.
- **Jan 21, 2024 (PR #104)**: Restructured the testing framework via the `Makefile`.
- **Jan 19, 2024 (PR #97)**: Implemented packaging configurations for the Python SDK.
- **Jan 15, 2024 (PR #66)**: Added server-side support for the Chroma vector database.

## Key Concepts
[[prompt-injection-mitigation]]
[[monorepo-architecture]]
[[vector-database-integration]]
[[sdk-development]]
[[ci-cd-automation]]

## Sources
- `https://github.com/protectai/rebuff` (Archived May 16, 2025)
- Repository file tree, commit history, and pull request metadata (Last active: Jan 25, 2024)
