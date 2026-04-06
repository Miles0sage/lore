---
backlinks: []
concepts:
- agent-lifecycle-management
- gaia-benchmark
- self-evolving-agents
- multi-agent-orchestration
- hierarchical-agent-architecture
- tea-protocol
- version-tracking-for-agents
- agentorchestra
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: agentorchestra-orchestrating-multi-agent-intelligence-with-the-tea-protocol
sources:
- raw/2026-04-05-multi-agent-orchestration-arxiv.md
status: published
title: 'AgentOrchestra: Orchestrating Multi-Agent Intelligence with the TEA Protocol'
updated: '2026-04-05'
---

# AgentOrchestra: Orchestrating Multi-Agent Intelligence with the TEA Protocol

## Overview
AgentOrchestra is a hierarchical multi-agent framework designed to resolve structural limitations in existing LLM-based agent systems. The architecture is built on the Tool-Environment-Agent (TEA) protocol, which standardizes the management of computational components across complex, long-horizon tasks. The framework was introduced in arXiv preprint 2506.12508, originally submitted on 14 Jun 2025 and last revised on 11 Jan 2026 (v5). The research was conducted by Wentao Zhang, Liang Zeng, Yuzhen Xiao, Yongcong Li, Ce Cui, Yilei Zhao, Rui Hu, Yang Liu, Yahui Zhou, and Bo An.

## The TEA Protocol
Current LLM-based agent protocols, specifically A2A and MCP, under-specify critical operational dimensions:
- Cross-entity lifecycle and context management
- Version tracking
- Ad-hoc environment integration
These gaps typically force developers into fixed, monolithic agent compositions and brittle glue code. The TEA protocol addresses these deficiencies by:
- Modeling environments, agents, and tools as first-class resources with explicit lifecycles and versioned interfaces
- Establishing a principled foundation for end-to-end lifecycle and version management
- Associating each execution run with its corresponding context and outputs across all components to improve traceability and reproducibility
- Enabling continual self-evolution of agent-associated components via a closed feedback loop, which supports automated version selection and rollback

## AgentOrchestra Framework
AgentOrchestra implements the TEA protocol through a centralized hierarchical architecture. A central planner dynamically orchestrates specialized sub-agents to execute discrete operational domains:
- Web navigation
- Data analysis
- File operations
The framework supports continual adaptation by dynamically instantiating, retrieving, and refining tools online during runtime execution. This design eliminates static composition constraints and allows the system to scale across heterogeneous task environments.

## Evaluation and Results
AgentOrchestra was evaluated across three challenging benchmarks. The framework consistently outperformed strong baseline models and achieved state-of-the-art performance on the GAIA benchmark, scoring 89.04%. Empirical results confirm that integrating the TEA protocol with hierarchical orchestration significantly improves scalability and generality in multi-agent systems.

## Key Concepts
[[tea-protocol]]
[[agentorchestra]]
[[multi-agent-orchestration]]
[[agent-lifecycle-management]]
[[version-tracking-for-agents]]
[[hierarchical-agent-architecture]]
[[gaia-benchmark]]
[[self-evolving-agents]]

## Sources
- arXiv:2506.12508v5 - *AgentOrchestra: Orchestrating Multi-Agent Intelligence with the Tool-Environment-Agent(TEA) Protocol* (Submitted 14 Jun 2025, Revised 11 Jan 2026). Authors: Wentao Zhang, Liang Zeng, Yuzhen Xiao, Yongcong Li, Ce Cui, Yilei Zhao, Rui Hu, Yang Liu, Yahui Zhou, Bo An. 
- Access: [PDF](https://arxiv.org/pdf/2506.12508) | [HTML (experimental)](https://arxiv.org/html/2506.12508v5) | [DOI](https://doi.org/10.48550/arXiv.2506.12508)
