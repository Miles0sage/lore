---
backlinks: []
concepts:
- synthetic trace generation
- agentic security models
- qlora fine-tuning
- temporal attack pattern detection
- multi-agent ai security
- opentelemetry trace analysis
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: temporal-attack-pattern-detection-in-multi-agent-ai-workflows
sources:
- raw/2026-04-05-opentelemetry-arxiv.md
status: published
title: Temporal Attack Pattern Detection in Multi-Agent AI Workflows
updated: '2026-04-05'
---

# Temporal Attack Pattern Detection in Multi-Agent AI Workflows

**Temporal Attack Pattern Detection in Multi-Agent AI Workflows: An Open Framework for Training Trace-Based Security Models** is a research paper authored by Ron F. Del Rosario, submitted to arXiv on 29 Dec 2025 (arXiv:2601.00848). The document spans 26 pages, contains 3 figures and 7 tables, and is classified under ACM class I.2.7. It falls within the subjects of Artificial Intelligence (cs.AI) and Cryptography and Security (cs.CR). The work introduces an openly documented methodology for fine-tuning language models to detect temporal attack patterns in multi-agent AI workflows using OpenTelemetry trace analysis.

## Methodology and Training Pipeline

The research utilizes a curated dataset comprising 80,851 examples sourced from 18 public cybersecurity repositories, supplemented by 35,026 synthetic OpenTelemetry traces. Model training employs iterative QLoRA fine-tuning executed on resource-constrained ARM64 hardware, specifically an NVIDIA DGX Spark system. The training process spans three distinct iterations incorporating strategic data augmentation.

Performance evaluation on a custom benchmark demonstrates a statistically significant improvement in detection accuracy, rising from 42.86% to 74.29%, representing a 31.4-point gain. The study empirically demonstrates that targeted training examples addressing specific knowledge gaps yield superior results compared to indiscriminate dataset scaling.

## Key Contributions

The framework delivers three primary contributions to agentic AI security:
* **Synthetic Trace Generation:** A documented methodology for generating synthetic OpenTelemetry traces that simulate multi-agent coordination attacks and regulatory compliance violations.
* **Data Composition Impact:** Empirical validation that the structural composition of training data fundamentally dictates model security behavior and detection capabilities.
* **Open Release:** Complete public distribution of all datasets, training scripts, and evaluation benchmarks via HuggingFace.

## Deployment Considerations

While the framework establishes a reproducible baseline for building custom agentic security models tailored to specific threat landscapes, practical deployment necessitates human oversight. The current iteration exhibits non-trivial false positive rates, requiring manual verification in production environments.

## Resources and Access

* **HuggingFace Repository:** https://huggingface.co/guerilla7/agentic-safety-gguf
* **PDF:** https://arxiv.org/pdf/2601.00848
* **HTML (Experimental):** https://arxiv.org/html/2601.00848v1
* **DOI:** https://doi.org/10.48550/arXiv.2601.00848

## Key Concepts
[[OpenTelemetry Trace Analysis]]
[[QLoRA Fine-Tuning]]
[[Multi-Agent AI Security]]
[[Temporal Attack Pattern Detection]]
[[Synthetic Trace Generation]]
[[Agentic Security Models]]

## Sources
* Del Rosario, R. F. (2025). *Temporal Attack Pattern Detection in Multi-Agent AI Workflows: An Open Framework for Training Trace-Based Security Models*. arXiv:2601.00848. Retrieved from https://arxiv.org/abs/2601.00848
