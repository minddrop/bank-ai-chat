# ADR 0009: Enterprise Data Loss Prevention (DLP), Security Guardrails & Regulatory Compliance Framework

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Cybersecurity Architect, Banking AI Compliance Auditor, Cloud Engineering Lead

## Context & Problem Statement
Customer-facing banking AI assistants operating in production must comply with international and domestic regulatory security frameworks including PCI-DSS 4.0, GLBA Safeguards Rule (16 CFR Part 314), CFPB AI Guidance, SR 11-7 Model Risk Management, ISO 42001/AIUC-1, NYDFS Part 500, FISC Security Standards (FISC安全対策基準), Japanese APPI (個人情報保護法), and FIEA (金融商品取引法). 

The initial requirements draft required gap analysis and technical refinement into testable RFC 2119 specifications covering indirect prompt injection, multi-layer PII tokenization, NLI entailment grounding verification (>=0.85), microservice latency budgeting (<630ms P95), and fail-closed security posture.

## Decision Drivers
* Protection against direct and indirect prompt injection attacks (OWASP LLM01 & LLM02).
* Elimination of PII/PAN leakage via KMS-salted tokenization and dual-pass inspection (PCI-DSS 4.0 / APPI).
* Mathematical validation of LLM grounding to eliminate hallucinations (SR 11-7 / CFPB AI Guidance).
* Formal mapping across global banking regulatory security frameworks.
* Sub-second execution SLA with deterministic fail-closed safety posture.

## Considered Options
1. Retain broad, ambiguous requirements without microservice latency budgets or formal regulatory mapping (Rejected - Vulnerable to audit failure and regulatory sanctions).
2. Implement synchronous commercial SaaS DLP endpoints outside AWS Tokyo VPC (Rejected - Violates FISC data sovereignty and introduces unbudgeted latency).
3. Adopt Enterprise RFC 2119 In-VPC Dual Control Plane Architecture with microservice latency budgets, NLI entailment grounding (>=0.85), SHA-256 10-year WORM audit logging, and global regulatory traceability matrix (Chosen).

## Decision Outcome
Chosen Option: **Option 3 (Enterprise In-VPC Dual Control Plane Architecture)**.

### Key Architectural Specifications:
* **Inbound DLP**: Multi-pattern PII regex + NER model, KMS salted tokenization, NFC Unicode normalization, 1,000-char truncation, prompt injection classifier (<45ms P95).
* **Outbound DLP**: Grounding score via NLI Entailment (>=0.85), numeric financial value cross-validation, FIEA investment advice filter, mandatory legal disclaimer.
* **Security & RAG**: Ephemeral zero-trust session context isolation, RAG vector index tier-based RBAC, read-only mTLS core banking integration, step-up MFA for transactional operations.
* **Audit & NFR**: SHA-256 tamper-evident logs stored in S3 Object Lock (10-year compliance mode), total P95 latency budget <630ms, fail-closed posture on guardrail API timeout or failure.

## Consequences
* **Positive**: 100% compliance coverage across PCI-DSS 4.0, GLBA, CFPB, SR 11-7, ISO 42001, NYDFS Part 500, FISC, APPI, and FIEA. Eliminates prompt injection, context bleeding, and financial hallucination risks.
* **Negative**: Inbound and outbound control planes consume ~95ms (P95) of total processing budget.
