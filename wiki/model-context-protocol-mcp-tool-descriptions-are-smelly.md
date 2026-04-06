---
backlinks: []
concepts:
- component ablation
- context window optimization
- ai agent efficiency
- foundation model
- execution cost trade-offs
- tool description smells
- model context protocol
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: model-context-protocol-mcp-tool-descriptions-are-smelly
sources:
- raw/2026-04-05-model-context-protocol-mcp-arxiv.md
status: published
title: Model Context Protocol (MCP) Tool Descriptions Are Smelly!
updated: '2026-04-05'
---

# Model Context Protocol (MCP) Tool Descriptions Are Smelly!

The Model Context Protocol (MCP) provides a standardized specification for Foundation Model (FM)-based agents to interact with external systems via tool invocation. FMs rely on natural-language tool descriptions to determine functionality, select optimal tools for subtasks, and correctly format input arguments. Deficiencies or "smells" in these descriptions directly impact agent guidance and execution reliability.

## Study Methodology
Researchers conducted an empirical analysis of 856 tools distributed across 103 MCP servers to quantify description quality and measure downstream effects on agent performance. The methodology comprised:
- Identifying six core components of tool descriptions from existing literature.
- Developing a scoring rubric based on these six components.
- Formalizing tool description smells according to the rubric criteria.
- Operationalizing the rubric through an automated FM-based scanner.

## Key Findings
The analysis revealed widespread deficiencies in existing MCP tool descriptions and quantified the impact of augmentation:
- **Smell Prevalence:** 97.1% of analyzed tool descriptions contain at least one identified smell.
- **Purpose Ambiguity:** 56% of descriptions fail to clearly state their intended purpose.
- **Augmentation Benefits:** Enhancing descriptions to include all six components improves agent outcomes:
  - Task success rates increase by a median of 5.85 percentage points.
  - Partial goal completion improves by 15.12%.
- **Operational Trade-offs:** Full augmentation introduces measurable overhead:
  - Execution steps increase by 67.46%.
  - Performance regresses in 16.67% of evaluated cases.
These metrics indicate that performance optimization is non-linear and heavily influenced by execution cost trade-offs and environmental context.

## Optimization Strategies
Component ablation studies demonstrate that maximal description verbosity is unnecessary for reliable agent behavior. Compact variants utilizing targeted combinations of description components:
- Preserve behavioral reliability.
- Reduce unnecessary token overhead.
- Enable more efficient utilization of the FM context window.
- Lower overall execution costs.

## Key Concepts
[[Model Context Protocol]]
[[Foundation Model]]
[[Tool Description Smells]]
[[AI Agent Efficiency]]
[[Context Window Optimization]]
[[Execution Cost Trade-offs]]
[[Component Ablation]]

## Sources
- arXiv:2602.14878 (cs.SE; cs.ET) - "Model Context Protocol (MCP) Tool Descriptions Are Smelly! Towards Improving AI Agent Efficiency with Augmented MCP Tool Descriptions" by Mohammed Mehedi Hasan, Hao Li, Gopi Krishnan Rajbahadur, Bram Adams, Ahmed E. Hassan. Submitted 16 Feb 2026 (v1), revised 21 Feb 2026 (v2). DOI: https://doi.org/10.48550/arXiv.2602.14878. PDF: https://arxiv.org/pdf/2602.14878. HTML: https://arxiv.org/html/2602.14878v2.
