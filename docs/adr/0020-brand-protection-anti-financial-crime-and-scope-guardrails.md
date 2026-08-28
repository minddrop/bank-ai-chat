# ADR 0020: Brand Protection, Anti-Financial Crime (AML/CFT), and Scope Locking Guardrails

* **Status**: Accepted
* **Date**: 2026-08-28
* **Deciders**: Chief Information Security Officer (CISO), Principal AI Security Architect, Head of Retail Banking Compliance

---

## Context & Problem Statement

As a major Japanese commercial bank operating critical national infrastructure and competing in a commercial market, the digital banking AI assistant faces existential operational and brand risks:
1. **Competitor Endorsement**: The LLM could recommend competitor financial institutions (e.g., MUFG, SMBC, Mizuho, SBI Sumishin Net Bank, Sony Bank) or unfavorably compare fee structures.
2. **Financial Crime Incitement**: Malicious actors could attempt to solicit money laundering (資金洗浄), mule accounts (闇バイト / 口座売買), cash structuring below the ¥1,000,000 reporting threshold, tax evasion, or phishing scripts.
3. **Compute Hijacking / Scope Abuse**: Non-customers could exploit the bank's AWS Bedrock endpoint for non-banking tasks (coding, homework, translation of non-banking text, general roleplay).

We require an In-VPC multi-layer guardrail architecture to deterministically intercept competitor mentions, block illicit financial crime vectors, and reject out-of-scope compute hijacking before invoking foundation models.

---

## Decision Drivers

1. **Brand & Profit Protection**: Zero endorsement of competitor banks and strategic redirection to our bank's VIP/Super VIP loyalty tiers and fee waiver benefits.
2. **Anti-Financial Crime Compliance**: Strict compliance with the Act on Prevention of Transfer of Criminal Proceeds (犯罪収益移転防止法), the Banking Act, and FISC security standards.
3. **Infrastructure Resource Optimization**: Prevention of token budget leakage on unauthorized general AI tasks.
4. **Sub-45ms Latency Overhead**: Guardrail evaluation must not degrade the end-to-end response time (< 2.0s P95).

---

## Considered Options

1. **Dedicated In-VPC Guardrail Triple-Engine (`BrandGuardrail`, `CrimeGuardrail`, `ScopeGuardrail`) (Chosen Option)**:
   - Implement deterministic, compiled regex and dictionary evaluators in FastAPI ECS Fargate tasks.
   - Stage 1: Intercept prompt injection and AML financial crimes with immediate session termination and P1 CloudWatch alarms.
   - Stage 2: Reject out-of-scope compute hijacking with courteous standard banking redirection.
   - Stage 3: Scan outputs to suppress competitor names and pivot to our bank's superior benefits.
2. **Pure Prompt Engineering / LLM System Prompt Instructions**:
   - Instruct the LLM in the system prompt to avoid competitors and refuse coding.
   - *Drawback*: Vulnerable to prompt injection, jailbreaks, and hallucinations; wastes expensive Bedrock tokens on off-topic requests.
3. **Generic Cloud Content Moderation API**:
   - Use third-party cloud moderation APIs.
   - *Drawback*: Lacks domain awareness of Japanese commercial banking entities, financial crime patterns, and violates In-VPC data boundaries.

---

## Decision Outcome

Chosen Option: **Option 1 (Dedicated In-VPC Guardrail Triple-Engine)**.

### Architecture & Control Flow:
- **`ScopeGuardrail`**: Evaluates intent against banking keywords and off-topic patterns (code, homework, non-banking translation).
- **`CrimeGuardrail`**: Enforces zero tolerance on money laundering, mule accounts (*闇バイト*), cash structuring, and fraud.
- **`BrandGuardrail`**: Maintains a 35+ institution dictionary of Japanese megabanks, net banks, and regional banks; intercepts outbound mentions and pivots to our bank's Happy Program VIP tiers.

---

## Consequences

### Positive:
- **Zero Competitor Endorsement**: Guaranteed protection of bank market share and brand reputation.
- **Regulatory Defensibility**: Audit logs capture blocked crime attempts for FISC compliance reporting.
- **Low Overhead**: Regex-compiled pipeline adds $< 5\text{ms}$ processing latency.

### Negative / Risks:
- **Dictionary Maintenance**: Regular updates required as new competitor fintechs and banking brands launch in Japan.
