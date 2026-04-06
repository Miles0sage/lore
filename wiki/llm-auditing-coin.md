---
backlinks: []
concepts:
- verifier-training
- llm-auditing
- case-lab-umd
- hugging-face-integration
- hash-tree-construction
- chain-of-inference-pipeline
- token-to-block-mapping
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: llm-auditing-coin
sources:
- raw/2026-04-05-chain-of-thought-auditing-github.md
status: published
title: LLM-Auditing-CoIn
updated: '2026-04-05'
---

# LLM-Auditing-CoIn

`LLM-Auditing-CoIn` is a public repository maintained by the CASE Lab at the University of Maryland (`CASE-Lab-UMD`). The project provides a structured, multi-stage codebase for auditing large language model reasoning processes, organized around data preprocessing, hash tree construction, token/block mapping, verifier training, and pipeline execution.

## Directory Structure
The repository is organized into sequentially numbered pipeline stages and supporting directories. Each directory is associated with specific commit timestamps and update messages:

- `0_preprocess`: Data preprocessing utilities (updated Mar 9, 2026)
- `1_mk_data`: Dataset creation and formatting (updated Mar 9, 2026)
- `2_hash_tree`: Hash tree implementation (updated Mar 9, 2026)
- `3_Block2Answer`: Logic for mapping reasoning blocks to outputs (initialized Jun 9, 2025)
- `3_Tokens2Block`: Token aggregation into reasoning blocks (initialized Jun 9, 2025)
- `4_train_verifier`: Verifier model training scripts (initialized Jun 9, 2025)
- `5_CoIn_pipline`: Core CoIn pipeline execution (initialized Jun 9, 2025)
- `6_discussion`: Discussion and analysis materials (updated Mar 9, 2026)
- `7_eval_data`: Evaluation datasets (initialized Jun 9, 2025)
- `huggingface_cards`: Hugging Face model/dataset cards (updated Mar 9, 2026)
- `misc`: Miscellaneous configuration and utility files (updated Mar 9, 2026)
- Root files: `.gitignore`, `LICENSE`, `README.md`

## Development History & Metadata
The repository operates on a single `main` branch with zero published tags. Development is tracked across three total commits, spanning two primary release windows:

- **Initial Codebase (Jun 9, 2025):** Core pipeline directories (`3_Block2Answer`, `3_Tokens2Block`, `4_train_verifier`, `5_CoIn_pipline`, `7_eval_data`) were initialized under commit `bdbc03efb42ba1931830d120cf4b1d4fefdfe310` with the message `init part of code`.
- **Data & Integration Update (Mar 9, 2026):** The repository was updated to integrate Hugging Face links for datasets and matching heads. Authored by `s1ghhh`, this commit (`06c3246ae19d761151c255defc99888ee4683894`) modified `0_preprocess`, `1_mk_data`, `2_hash_tree`, `6_discussion`, `huggingface_cards`, `misc`, `.gitignore`, `LICENSE`, and `README.md`. The commit message reads: `update README with hf links for the data and matching head`.

## Key Concepts
[[LLM-Auditing]]
[[Chain-of-Inference-Pipeline]]
[[Hash-Tree-Construction]]
[[Token-to-Block-Mapping]]
[[Verifier-Training]]
[[Hugging-Face-Integration]]
[[CASE-Lab-UMD]]

## Sources
- CASE-Lab-UMD/LLM-Auditing-CoIn GitHub Repository: https://github.com/CASE-Lab-UMD/LLM-Auditing-CoIn
- Repository file tree, commit history, and metadata (Accessed Mar 9, 2026)
