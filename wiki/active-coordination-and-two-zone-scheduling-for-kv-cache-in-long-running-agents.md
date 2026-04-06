---
backlinks: []
concepts:
- session-aware reference counting
- llm agent context optimization
- prefix caching
- kv cache management
- active invalidation interface
- hyperbolic two-zone scheduling
- time-to-first-token optimization
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: active-coordination-and-two-zone-scheduling-for-kv-cache-in-long-running-agents
sources:
- raw/2026-04-05-stale-memory-detection-and-invalidation-in-llm-agent-vector-stores-web.md
status: published
title: Active Coordination and Two-Zone Scheduling for KV Cache in Long-Running Agents
updated: '2026-04-05'
---

# Active Coordination and Two-Zone Scheduling for KV Cache in Long-Running Agents

## Problem Statement

### Temporal Mismatch Between Agent Context and KV Cache
Modern LLM inference engines rely on **Prefix Caching** to store historical KV states in GPU memory, bypassing redundant prefix computations to optimize Time-To-First-Token (TTFT). This mechanism operates on the assumption that context is strictly append-only. In **Deep Agent** workflows (e.g., OpenCLAW, Claude Code, AutoGen), the context engine continuously performs dynamic operations:
- **Compression**: Merging multi-turn dialogues into concise summaries.
- **Offloading**: Moving large text blocks or images to external storage.
- **Refinement**: Replacing raw history with abstract summaries.
- **Skill Switching**: Dynamically injecting or removing System Prompts and tool definitions.

The inference engine remains unaware of these semantic modifications, retaining KV cache blocks for context the Agent has already discarded or altered. This creates severe memory inefficiency and degrades inference service performance.

### Performance Degradation Cascade
In high-concurrency environments, this mismatch triggers three compounding failures:
1. **Zombie Cache Accumulation**: Traditional Least Recently Used (LRU) eviction policies rely on last access time. Recently compressed contexts are incorrectly classified as "hot data" and retained, consuming VRAM.
2. **Cache Hit Rate Avalanche**: Zombie data occupies valid cache space, forcing premature eviction of genuinely useful prefixes. The system repeatedly executes expensive Prefill computations and incurs additional cache lookup overhead.
3. **Throughput Blockage**: Multi-session concurrency wastes compute resources on redundant Prefill operations and ineffective cache management, sharply reducing overall service throughput.

## Solution Overview

The proposed architecture establishes an **Active Coordination Mechanism** between the Agent context engine and the KV Cache, enabling the Agent to directly manage cache lifecycles. Key innovations include:
- **Active Invalidation Interface**: Enables clients to precisely notify the inference engine to release invalid cache blocks based on detected context differences.
- **Session-Aware Reference Counting**: Implements reference counting for multi-session shared caching, ensuring safe block release without breaking concurrent dependencies.
- **Hyperbolic Two-Zone Scheduling**: Replaces standard LRU with dual queues (**Aging Zone** and **Fresh Zone**) to accelerate eviction of explicitly invalidated data while protecting potentially hot data from premature removal.

## Design Specification

The architecture shifts from passive eviction to active coordination, granting context-aware entities control over KV Cache operations.

### Overall Architecture
- **Agent Side**: The Context Engine monitors context changes, calculates diffs, and initiates release commands.
- **Inference Engine Side (vLLM)**:
  - Extends `KvCacheManager` to support active release interfaces.
  - Introduces `KvCacheSessionManager` to handle multi-session sharing logic.
  - Refactors `FreeBlockQueue` into a dual-zone scheduling queue (Aging/Fresh).

### Core Functional Modules
#### Session Management and Reference Counting
Cache blocks shared across multiple clients or dialogue sessions require robust reference counting to prevent accidental deletion.
- **Concepts**:
  - `session_id` (`cache_salt`): Uniquely identifies a complete dialogue or task flow.
  - **Sharing Rule**: A block accessed by multiple sessions records all associated `session_id`s. The cache is only recyclable when **all** associated sessions declare its release.
- **`KvCacheSessionManager` Methods**:
  - `add_blocks(session_id, block_list)`: Establishes mapping between session and blocks.
  - `reset_blocks(session_id, block_list)`: Resets mappings (used when evicted blocks are reused).
  - `release_blocks(session_id, block_list)`: Removes the mapping for a specific session.

#### Active Cache Release Interface
A dedicated API endpoint allows clients to notify the engine of invalidation ranges upon context changes.

**Endpoint:** `POST /release_kv_cache`

**Request Body Example:**
```json
{
    "messages_released_index": 20,
    "tools_released_index": 100,
    "cache_salt": "1234",
    "cache_sharing": true,
    "model": "Qwen3-32B",
    "messages": [],
    "tools": []
}
```

## Performance Impact
Experimental results in high-concurrency Agent scenarios with frequent context operations demonstrate:
- Up to **26% reduction** in TTFT.
- Significant improvements in Prefix Cache hit rates.
- Measurable increases in overall system throughput.

## Key Concepts
[[KV Cache Management]]
[[Prefix Caching]]
[[Active Invalidation Interface]]
[[Session-Aware Reference Counting]]
[[Hyperbolic Two-Zone Scheduling]]
[[LLM Agent Context Optimization]]
[[Time-To-First-Token Optimization]]

## Sources
- GitHub RFC Issue #37168: "[RFC]: Active Coordination and Two-Zone Scheduling Mechanism for KV Cache in Long-Running Agents" by @xinrunxue, opened Mar 16, 2026. https://github.com/vllm-project/vllm/issues/37168
