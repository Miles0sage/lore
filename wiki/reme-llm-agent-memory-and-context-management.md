---
backlinks: []
concepts:
- llm agent memory management
- dependency injection
- react agent pattern
- two-stage truncation
- context compaction
- long-term memory triggers
- vector store integration
- pre-reasoning hook
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: reme-llm-agent-memory-and-context-management
sources:
- raw/2026-04-05-stale-memory-detection-and-invalidation-in-llm-agent-vector-stores-github.md
status: published
title: 'ReMe: LLM Agent Memory and Context Management'
updated: '2026-04-05'
---

# ReMe: LLM Agent Memory and Context Management

## Repository Overview
ReMe is an open-source project maintained by `agentscope-ai` focused on memory management, context handling, and vector store integration for LLM agents. As of March 31, 2026, the repository tracks 2.6k stars, 214 forks, 11 branches, 54 tags, and 805 total commits.

## Architecture and Directory Structure
- `reme`: Core library handling vector stores, file stores, and dependency management.
- `reme_ai`: Agent implementations, including memory agents and base ReAct logic.
- `benchmark`: Performance evaluation tools, including `locomo` integration.
- `docs`: Design documentation for context management and system architecture.
- `test`: Unit and integration tests for memory formatting and logging.
- `.github/workflows`: CI/CD pipeline configurations.

## Recent Development and Commits
- **Mar 31, 2026** (`d5c929722bfec6bb4268d5430d62c69792582098`): Refactored `file_store` to move `sqlite3` imports inside initialization methods (#193).
- **Mar 30, 2026** (`2a999ce4f4b52f7d6b5c90a19f0dc1a60932d23c`): Added comprehensive context management design documentation (#187).
- **Mar 9, 2026** (`8b45493634001a61f09b248449463bd56d398117`): Added `locomo` benchmark code (#148).
- **Mar 4, 2026** (`1ee7376fa4f145bdb6cd4ccb5e7a217e8a0c5c60`): Upgraded GitHub Actions for Node 24 compatibility (#136).
- **Jan 26, 2026** (`d3fa645832a711863095d3a20518f10b6b5a0556`): Restructured memory agents and base ReAct implementation.

## Context Management Design (CoPaw V2)
Documentation added in PR #187 outlines the CoPaw context management architecture:
- Defines in-memory and file system cache layer architecture.
- Explains the Pre-Reasoning Hook workflow with a four-step process.
- Details a two-stage truncation strategy for tool results.
- Implements protection thresholds for Markdown files and special handling for `readFile` tools.
- Describes long-term memory trigger mechanisms.
- Includes Mermaid diagrams for visualizing context flow and examples for Browser Use and ReadFile tools.

## Dependency and Import Refactoring
PR #193 updated the core library (version `0.3.1.7` to `0.3.1.8`) with the following changes:
- Moved `sqlite3` imports from module-level to inside `init` methods to prevent early dependency loading.
- Changed `CHROMADB_AVAILABLE` flag to `_CHROMADB_IMPORT_ERROR` exception storage for graceful `chromadb` import handling.
- Replaced hardcoded `ImportError` messages with dynamic exception raising.
- Broadened import error handling from `ImportError` to `Exception` for `ray`, `chromadb`, `elasticsearch`, `asyncpg`, and `qdrant`.
- Added explicit type hints (`Exception | None`) for all import error variables.
- Standardized logger initialization using the `get_logger` utility.

## Testing and Formatting Updates
PR #175 (`7b02c4521826c3f497f95d3077d676cd31b11a74`) applied the following modifications:
- Changed default `include_thinking` parameter to `True` in `as_msg_handler.py`.
- Replaced angle brackets with square brackets for block formatting in `as_msg_stat.py`.
- Added newline replacement in the text truncation method in `as_msg_stat.py`.
- Added loading duration timing to embedding cache loading in `base_embedding_model.py`.
- Replaced XML-style tags with markdown headers in `compactor.py` conversation formatting.

## Key Concepts
[[LLM Agent Memory Management]]
[[Context Compaction]]
[[Vector Store Integration]]
[[ReAct Agent Pattern]]
[[Dependency Injection]]
[[Pre-Reasoning Hook]]
[[Two-Stage Truncation]]
[[Long-Term Memory Triggers]]

## Sources
- https://github.com/agentscope-ai/ReMe
