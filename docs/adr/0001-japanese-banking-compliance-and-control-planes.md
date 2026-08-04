# ADR 0001: Japanese Banking Compliance & Control Planes

* **Status**: Accepted
* **Date**: 2026-08-04
* **Deciders**: AI Bank Engineering Team, Security & Compliance Lead

## Context & Problem Statement
Deploying an AI Customer Assistant in a major Japanese bank requires strict adherence to Japanese privacy laws (APPI / 個人情報保護法), Financial Services Agency (FSA) guidelines, FISC security standards (FISC安全対策基準), and the Banking Act (銀行法). Unchecked LLM interactions could expose customer PII, generate false financial commitments, or violate financial solicitation laws.

## Decision Drivers
* Strict PII scrubbing requirement before sending data outside VPC or to LLM endpoints.
* Prohibition of un-licensed financial/investment recommendations.
* Necessity of auditability and explainability for regulatory reporting to the FSA.
* Need for real-time hallucination prevention and disclaimer enforcement.

## Considered Options
1. Direct LLM API access without guardrails (Rejected - High legal and regulatory risk).
2. Third-party US-based cloud guardrail SaaS (Rejected - Violates FISC data sovereignty guidelines).
3. Custom In-VPC Dual Control Planes (Input Guardrail + Output Guardrail + FISC Audit Logger) (Chosen).

## Decision Outcome
Chosen Option: **Option 3 (Custom In-VPC Dual Control Planes)**.

### Implementation Details:
* **Input Guardrail**: Scans all customer input for Japanese PII patterns (7-digit account numbers `\d{7}`, 3-digit branch codes `\d{3}`, Katakana names, passwords) and redacts them prior to prompt assembly.
* **Output Guardrail**: Validates generated text against RAG FAQ ground truth, filters accidental PII echo, and appends mandatory Japanese legal disclaimers.
* **Audit Logger**: Stores tamper-evident logs of all interactions in AWS Tokyo region (`ap-northeast-1`).

## Consequences
* **Positive**: Full compliance with APPI, FSA, and FISC standards; risk of data leakage or regulatory penalty eliminated.
* **Negative**: Slight latency overhead (~15-30ms) for regex and guardrail checks per request.
