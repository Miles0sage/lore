---
backlinks: []
concepts:
- prompt-injection-attacks
- multi-agent-defense-framework
- chain-of-agents-pipeline
- attack-success-rate
- real-time-threat-mitigation
- hierarchical-coordinator-system
- llm-security
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: a-multi-agent-llm-defense-pipeline-against-prompt-injection-attacks
sources:
- raw/2026-04-05-prompt-injection-mitigation-arxiv.md
status: published
title: A Multi-Agent LLM Defense Pipeline Against Prompt Injection Attacks
updated: '2026-04-05'
---

# A Multi-Agent LLM Defense Pipeline Against Prompt Injection Attacks

## Overview
Prompt injection attacks represent a major vulnerability in Large Language Model (LLM) deployments, where malicious instructions embedded in user inputs can override system prompts and induce unintended behaviors. This research presents a multi-agent defense framework that employs specialized LLM agents in coordinated pipelines to detect and neutralize prompt injection attacks in real-time.

## Architecture & Methodology
The framework evaluates two distinct architectural implementations:
- Sequential chain-of-agents pipeline
- Hierarchical coordinator-based system

The system is engineered to maintain standard functionality for legitimate queries while actively filtering adversarial inputs across multiple attack vectors.

## Evaluation & Results
The defense pipeline was tested across two LLM platforms: ChatGLM and Llama2. The evaluation dataset consisted of 400 attack instances derived from 55 unique prompt injection attacks, organized into 8 categories.

**Baseline Performance (No Defense):**
- ChatGLM Attack Success Rate (ASR): 30%
- Llama2 Attack Success Rate (ASR): 20%

**Framework Performance:**
- Achieved 100% mitigation across all tested scenarios
- Reduced ASR to 0% for both platforms
- Demonstrated robustness against direct overrides, code execution attempts, data exfiltration, and obfuscation techniques

## Publication Details
- **arXiv ID:** 2509.14285
- **DOI:** https://doi.org/10.48550/arXiv.2509.14285
- **Subjects:** Cryptography and Security (cs.CR); Machine Learning (cs.LG)
- **Authors:** S M Asif Hossain, Ruksat Khan Shayoni, Mohd Ruhul Ameen, Akif Islam, M. F. Mridha, Jungpil Shin
- **Conference:** Accepted at the 11th IEEE WIECON-ECE 2025
- **Submission History:**
  - v1: 16 Sep 2025
  - v2: 1 Oct 2025
  - v3: 13 Dec 2025
  - v4: 17 Dec 2025
- **Access Links:** [PDF](https://arxiv.org/pdf/2509.14285), [HTML](https://arxiv.org/html/2509.14285v4), [TeX Source](https://arxiv.org/src/2509.14285)

## Key Concepts
[[prompt-injection-attacks]]
[[multi-agent-defense-framework]]
[[chain-of-agents-pipeline]]
[[hierarchical-coordinator-system]]
[[attack-success-rate]]
[[llm-security]]
[[real-time-threat-mitigation]]

## Sources
- arXiv:2509.14285 - *A Multi-Agent LLM Defense Pipeline Against Prompt Injection Attacks* by S M Asif Hossain et al. (Submitted 16 Sep 2025, revised 17 Dec 2025). Available at: https://arxiv.org/abs/2509.14285
