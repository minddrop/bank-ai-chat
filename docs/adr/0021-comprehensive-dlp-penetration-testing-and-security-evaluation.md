# ADR 0021: Comprehensive DLP, Server Penetration Testing, and Security Evaluation Framework

* **Status**: Accepted
* **Date**: 2026-08-28
* **Deciders**: Lead Cybersecurity Architect, Head of Penetration Testing & Red Teaming, Cloud Compliance Officer

---

## Context & Problem Statement

As national critical banking infrastructure deployed on AWS Tokyo (`ap-northeast-1`), the AI Assistant must withstand sophisticated adversarial attacks, including:
1. **DLP Evasion**: Unicode zero-width evasion (`\u200B`), space padding, and prompt extraction aiming to leak customer account numbers or synthetic database schemas.
2. **Infrastructure Exploitation**: Server-Sent Events (SSE) `/api/chat/stream` slowloris buffer starvation, memory exhaustion, and indirect RAG vector injection into OpenSearch Serverless.
3. **Cross-Tenant & Token Leakage**: Reconstruction of PII from in-memory tokenization digests.

A rigorous, multi-tier security testing framework is required to continuously evaluate the system prior to and during production operations.

---

## Decision Drivers

1. **APPI & FISC Compliance**: Complete assurance of zero PII transmission to external LLMs.
2. **Adversarial Resilience**: Validation against Japanese-language jailbreaks (DAN modes, persona hijacking, delimiter escapes).
3. **Infrastructure Robustness**: Verification that SSE streams and API endpoints handle oversized payloads without buffer crashes or ReDoS.
4. **Automated CI/CD Quality Gates**: Enforcing 100% PII recall and < 45ms guardrail overhead in automated test pipelines.

---

## Considered Options

1. **3-Tier Automated Security Testing Suite (`tests/test_penetration.py`, `tests/test_guardrails_extended.py`) (Chosen Option)**:
   - Tier 1: Adversarial LLM Red Teaming (Japanese DAN jailbreaks, hypothetical roleplays, obfuscated PII).
   - Tier 2: AWS Server & Streaming Penetration Testing (oversized payload ReDoS, indirect RAG injection, token vault irreversibility).
   - Tier 3: Automated Latency & Benchmarking Gates in CI/CD.
2. **Periodic Manual Third-Party Penetration Testing Only**:
   - Run penetration testing once every 6 months via external consultancy.
   - *Drawback*: Leaves day-to-day code deployments and model prompt changes vulnerable to regressions between audit cycles.
3. **Model-Level Evaluation Only (LLM-as-a-Judge)**:
   - Only test prompt outputs.
   - *Drawback*: Ignores API buffer vulnerabilities, SSE connection starvation, and In-VPC token vault memory safety.

---

## Decision Outcome

Chosen Option: **Option 1 (3-Tier Automated Security Testing Suite)**.

### Testing Architecture:
- **`tests/test_penetration.py`**: Validates buffer overflow protection (50KB payloads), indirect vector injection, HMAC salt unpredictability, and sub-45ms latency budgets.
- **`tests/test_guardrails_extended.py`**: Validates PII masking across My Number (12 digits), Luhn-verified credit cards, zero-width spaces (`\u200B`), and competitor redirection.

---

## Consequences

### Positive:
- **Continuous Security Verification**: Every code commit and pull request verifies 29+ security and compliance vectors.
- **Zero-Day Vulnerability Defense**: Defends against obfuscation and indirect injection before traffic reaches Amazon Bedrock.
- **Audit-Ready FISC Evidence**: Test suites provide reproducible compliance evidence for Financial Services Agency (FSA) examinations.

### Negative / Risks:
- **Test Maintenance**: Test matrices must expand as new jailbreak patterns and regulatory guidance emerge.
