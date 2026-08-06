# ADR 0010: Personalized Account & Loyalty Tier Upgrade Reasoning Architecture

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Cybersecurity Architect, Banking AI Compliance Auditor, Retail Banking Product Lead

## Context & Problem Statement
Customers frequently inquire about personalized banking optimization, such as: *"How much more cash do I need to deposit into my ordinary savings account to upgrade to the next Happy Program loyalty stage (e.g. Super VIP)?"*

Under Japanese banking regulations, the system must balance providing intelligent, personalized customer service with strict compliance under the Banking Act (銀行法) and Financial Instruments and Exchange Act (FIEA / 金融商品取引法 Article 38). Specifically:
1. Is LLM-driven calculation of savings targets ($\text{Target Threshold} - \text{Current Balance} = \text{Savings Delta}$) permitted?
2. How does the system ensure personalized financial calculations do not breach prohibited securities investment advice bounds?

## Decision Drivers
* Enable high-value, personalized digital banking guidance based on authenticated customer account state + RAG FAQ tier rules.
* Strict compliance with APPI Article 20/23 (zero raw PII passed outside VPC/LLM endpoints).
* Strict compliance with FIEA Article 38 (prohibiting un-licensed securities recommendations while allowing commercial banking deposit/fee waiver guidance).
* Deterministic mathematical verification of LLM savings delta calculations against core banking ledger data.

## Considered Options
1. Prohibit all personalized financial calculations (Rejected - Substantially degrades customer user experience and fails modern banking expectations).
2. Allow unrestricted financial advice including stock/mutual fund recommendations (Rejected - Severe violation of FIEA Article 38).
3. Architect Dual Context Fusion (Customer Account Balance + RAG FAQ Program Criteria) allowing Banking Act-compliant Personalized Deposit & Loyalty Tier Delta Calculations while Output Guardrails enforce FIEA Securities Restrictions (Chosen).

## Decision Outcome
Chosen Option: **Option 3 (Dual Context Fusion for Banking Act-Compliant Tier Reasoning)**.

### Key Architectural Specifications:
* **Context Layer**: Fuses in-VPC masked customer balance (`普通預金` balance = ¥2,450,000) with retrieved RAG FAQ loyalty program criteria (Super VIP threshold = ¥3,000,000).
* **Inference Layer**: Amazon Bedrock Nova Lite performs deterministic subtraction ($\text{Target} - \text{Current} = \text{Savings Delta}$) and explains fee waiver benefits (e.g., 3 free wire transfers/month).
* **Output Guardrail**: Permits commercial deposit program guidance (普通預金・会員ステージランクアップ案内) while actively scanning and suppressing any prohibited securities advice (stock/crypto/mutual fund yield promises).
* **Disclaimer**: Mandatory Japanese banking legal disclaimer appends automatically to every response.

## Consequences
* **Positive**: Fully enables personalized customer inquiries regarding savings targets, tier upgrades, and fee waiver optimizations. 100% compliant with Banking Act, APPI, and FIEA.
* **Negative**: Requires precise RAG FAQ ground truth context matching to prevent numeric calculation hallucinations.
