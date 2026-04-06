---
backlinks: []
concepts:
- agentic ai safety
- cascading action chains
- unintended control amplification
- ai-q research assistant
- ciaan framework
- tool misuse
- defense-in-depth architecture
- ai guardrails
- contextual risk management
- ai-driven red teaming
- security taxonomy
- aegis framework
- emergent system properties
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: a-safety-and-security-framework-for-real-world-agentic-systems
sources:
- raw/2026-04-05-agentic-ai-security-guardrails-arxiv.md
- raw/2026-04-05-agentic-ai-security-guardrails-web.md
status: published
title: A Safety and Security Framework for Real-World Agentic Systems
updated: '2026-04-05'
---

# A Safety and Security Framework for Real-World Agentic Systems

## Overview
Published as arXiv:2511.21990v1 [cs.LG] on 27 Nov 2025, this paper introduces a dynamic framework for securing agentic AI systems in enterprise deployments. Authored by researchers from NVIDIA (Shaona Ghosh, Barnaby Simkin, Soumili Nandi, Dan Zhao, Nikki Pope, Roopa Prabhu, Michael Demoret, Bartley Richardson) and Lakera AI (Kyriacos Shiarlis, Matthew Fiedler, Julia Bazinska), the work posits that safety and security are emergent properties arising from interactions among models, orchestrators, tools, and data. The framework targets engineering, policy, safety/security, and governance teams, providing an operational strategy to instrument, discover, measure, and mitigate user harms in complex agentic workflows. Complementary to this academic approach, practical [[Defense-in-Depth Architecture]] implementations have emerged to address immediate production deployment challenges (per Sahu, 2026).

## Terminology and Positioning
The framework establishes precise definitions to unify safety and security under a user-safety lens:
- **Safety:** An umbrella system property preventing or mitigating unacceptable outcomes to people, organizations, or society from model behavior or system operation, whether accidental or adversarial. Encompasses content/behavioral issues and security concerns.
- **Security:** Protection of the agentic system and its assets against adversarial compromise, aligned with application security principles (CIAAN: Confidentiality, Integrity, Availability, Authenticity, Non-repudiation).
- **Harm:** Realized negative impact on users, systems, or third parties (e.g., financial loss, safety incident, privacy breach, reputational damage).
- **Risk:** The combination of likelihood and severity of a harm given a hazard or threat, conditioned on context and controls.
- **Trustworthiness:** The system’s ability to behave reliably under real-world conditions and governance constraints, combining safety, security, and assurance practices (testing, auditability, policy conformance).

## Agentic Risk Taxonomy
Traditional LLM safety and security are distinct in isolation but converge in agentic systems. The paper defines an operational taxonomy unifying traditional concerns with novel agentic risks, including:
- Tool misuse
- Cascading action chains
- Unintended control amplification
- Hazards introduced across expanded attack surfaces due to autonomous planning and multi-step execution
- Compounding failure propagation through inter-dependent components (models, memory stores, external APIs, UIs)

Practical deployments further highlight specific high-impact risk vectors that require explicit mitigation (per Sahu, 2026):
- **Hallucination at Scale:** When autonomous agents execute real-world actions (e.g., executing trades, booking appointments, processing refunds), hallucinated facts transition from user confusion to tangible financial or operational harm.
- **Data Leakage:** Agentic workflows processing sensitive inputs risk exposing personally identifiable information (PII), protected health information (PHI), or material non-public information (MNPI) without explicit safeguards.
- **Compliance Violations:** In regulated sectors (finance, healthcare, legal), AI-generated outputs must strictly adhere to industry regulations (e.g., FINRA Rule 2210), making ungoverned autonomous responses a direct legal liability.

## Operational Framework Architecture
The core framework operationalizes contextual agentic risk management through:
- **Dynamic Risk Management:** Utilizes auxiliary AI models and agents, combined with human oversight, to assist in contextual risk discovery, evaluation, and mitigation.
- **AI-Driven Red Teaming:** Employs sandboxed, automated red teaming to discover novel agentic risks that are subsequently mitigated contextually.
- **Observability & Traceability:** Addresses the non-deterministic nature of LLM-driven decision-making, where indefinite action sets and complex component interactions obscure root causes and complicate traditional deterministic testing.

In parallel, production-focused architectures like the **Aegis Framework** implement a multi-layered [[AI Guardrails]] strategy based on defense-in-depth principles. This approach layers input validation, output filtering, and compliance checks to intercept failures before they reach end-users, with reported efficacy in catching up to 95% of agentic failures pre-production (per Sahu, 2026).

## Case Study and Dataset Release
The framework is validated through a detailed case study of NVIDIA’s flagship agentic research assistant, the AI-Q Research Assistant. The study demonstrates end-to-end safety and security evaluations within complex, enterprise-grade workflows. 

To advance community research, the authors release the Nemotron-AIQ-Agentic-Safety-Dataset-1.0, available at https://huggingface.co/datasets/nvidia/Nemotron-AIQ-Agentic-Safety-Dataset-1.0. The dataset contains execution traces from over 10,000 realistic attack and defense scenarios. Future releases will include analyses of additional NVIDIA agentic systems to provide evolving insights into next-generation architecture safety, robustness, and operational behavior.

Practical validation of agentic guardrails is further illustrated by real-world deployment failures, such as an early financial query agent that hallucinated stock price predictions and violated FINRA compliance rules within its first hour of operation. This case underscores the necessity of layered intervention systems and has been documented alongside open-source implementations like the Aegis Framework, available at https://github.com/Suchi-BITS/agentic-guardrails/ (per Sahu, 2026).

## Key Concepts
[[Agentic AI Safety]]
[[Security Taxonomy]]
[[CIAAN Framework]]
[[Contextual Risk Management]]
[[AI-Driven Red Teaming]]
[[AI Guardrails]]
[[Defense-in-Depth Architecture]]
[[Aegis Framework]]

## Sources
- Ghosh, S., Simkin, B., Nandi, S., Zhao, D., Pope, N., Prabhu, R., Demoret, M., Richardson, B., Shiarlis, K., Fiedler, M., & Bazinska, J. (2025). *A Safety and Security Framework for Real-World Agentic Systems*. arXiv:2511.21990v1 [cs.LG].
- Sahu, S. (2026, Jan 24). *Building Production-Ready Guardrails for Agentic AI: A Defense-in-Depth Framework*. Medium. Retrieved from https://ssahuupgrad-93226.medium.com/building-production-ready-guardrails-for-agentic-ai-a-defense-in-depth-framework-4ab7151be1fe
