# Requirements Definition: Japanese Bank AI Customer Assistant

## 1. Overview & Business Objectives
This document specifies the technical, functional, regulatory, and security requirements for an **AI Customer Assistant** designed for major Japanese financial institutions. The system provides real-time banking customer support, account query assistance, and general banking FAQ resolution while ensuring strict adherence to Japanese laws, Financial Services Agency (FSA) guidelines, and FISC security standards.

---

## 2. Regulatory & Compliance Framework

### 2.1 Act on the Protection of Personal Information (個人情報保護法 - APPI)
- **Data Minimization & Anonymization**: Absolutely no raw PII (Personally Identifiable Information) may be transmitted to external LLM endpoints.
- **PII Definition in Japanese Banking**:
  - Full Names (Kanji/Katakana: 口座名義人)
  - Account Numbers (口座番号: 7-digit)
  - Branch Codes/Names (支店コード: 3-digit, 支店名)
  - Personal Identification / Passwords (暗証番号, PIN, Password)
  - Phone Numbers, Email Addresses, Postal Addresses (電話番号, 住所)
- **Enforcement**:
  - Input Guardrail MUST scrub/mask all PII into tokenized placeholders (e.g. `[REDACTED_ACCOUNT_NO]`, `[REDACTED_NAME]`) before prompt construction.
  - LLM context is strictly limited to ephemeral sessions; no customer data is used for model training.

### 2.2 Financial Services Agency (FSA) Guidelines (金融庁ガイドライン)
- **AI Governance & Explainability**: All AI decisions, retrieved FAQ contexts, and guardrail interventions must be recorded with traceable audit logs.
- **Financial Advice Prohibition**: Under Japanese Financial Instruments and Exchange Act (金融商品取引法), the AI MUST NOT provide specific financial/investment recommendations (e.g. stock purchases, specific fund advice) without human financial advisor licensing.
- **Mandatory Disclaimers**: Every response MUST include a clear disclaimer stating that AI responses are for informational purposes only.

### 2.3 FISC Security Guidelines (FISC安全対策基準)
- **Data Sovereignty**: All cloud infrastructure, LLM endpoints (Amazon Bedrock), and data stores MUST reside in AWS Tokyo (`ap-northeast-1`) or Osaka (`ap-northeast-2`) regions.
- **Encryption**: AES-256 (AWS KMS) for data at rest, TLS 1.3 for data in transit.
- **Audit Logs**: Immutable, tamper-evident audit logging for all interactions, stored in encrypted S3 buckets with lifecycle retention policies.

### 2.4 Banking Act (銀行法)
- **Contract Boundary**: AI responses do not form legally binding contracts or transaction commitments. Actions such as funds transfer (振込), password resets, or account closures require explicit multi-factor authenticated step-up operations.

---

## 3. System Components & Architecture

### 3.1 Control Planes (AI Safety Engine)
- **Input Guardrail**:
  - PII Detection & Masking (Regex + NER).
  - Jailbreak / Prompt Injection Filter (blocks system prompt extraction and behavioral overriding).
  - Scope Classifier (routes or blocks non-banking topics).
- **Output Guardrail**:
  - PII Leakage Scanner (ensures LLM did not generate or echo PII).
  - Grounding & Hallucination Verifier (compares LLM output against retrieved RAG context).
  - Compliance Disclaimer Injector (appends regulatory notices).
- **Audit Logger**:
  - Captures Session ID, Timestamp, Sanitized Query, Guardrail Status, RAG Context IDs, Latency, and Response Payload.

### 3.2 Data Infrastructure
- **Synthetic Mock Account Database**: Realistic mock datasets matching Japanese bank schema formats (普通預金, 定期預金, カタカナ名義, 直近振込明細).
- **Rakuten Bank FAQ RAG**: Ingested FAQ dataset from Rakuten Bank (`https://help-personal.rakuten-bank.net/`) indexed for semantic vector search.

### 3.3 LLM & Inference Engine
- **Provider**: Amazon Bedrock (Amazon Nova Lite `amazon.nova-lite-v1:0`).
- **Tone & Persona**: Polite Japanese Business Keigo (丁寧語・敬語), clear, helpful, non-authoritative on financial investments.

---

## 4. Functional Requirements

| ID | Feature | Description | Priority |
|---|---|---|---|
| FR-01 | Account Inquiry | Retrieve synthetic account balances and recent transactions after PII sanitization | High |
| FR-02 | FAQ Search | Answer customer inquiries using Rakuten Bank FAQ via RAG | High |
| FR-03 | Input Guardrail | Redact PII (account number, PIN, name) before sending to LLM | High |
| FR-04 | Output Guardrail | Verify grounding against RAG sources and append Japanese legal disclaimers | High |
| FR-05 | Audit Log Dashboard | Real-time governance view displaying guardrail execution and logs | High |
| FR-06 | Compliance Disclaimers | Automatically inject financial advice limitations & informational disclaimers | High |
