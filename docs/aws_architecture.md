# AWS & Hybrid Architecture Design: Japanese Major Bank AI Portal

## 1. Executive Summary & Topology

This document outlines the enterprise hybrid topology (On-Premise Core Banking System + AWS Private Cloud) for the Japanese Major Bank AI Customer Assistant. The architecture integrates an In-VPC Dual Control Plane with Data Loss Prevention (DLP), multi-pattern PII tokenization, direct/indirect prompt injection protection, RAG vector index Role-Based Access Control (RBAC), Natural Language Inference (NLI) Entailment grounding verification ($\ge 0.85$), sub-second microservice latency budgets ($360\text{ ms}$ P50 / $630\text{ ms}$ P95), and full regulatory compliance against FISC Security Standards, APPI, PCI-DSS 4.0, GLBA, CFPB, SR 11-7, ISO 42001/AIUC-1, and NYDFS Part 500.

---

## 2. Target Hybrid Architecture Pattern

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           On-Premise Banking Infrastructure (勘定系センター)                                │
│                                                                                                           │
│  ┌────────────────────────┐                   ┌────────────────────────────────────────────────────────┐  │
│  │ Core Banking Mainframe │                   │ Customer Account Database & PII Vault                  │  │
│  │ (勘定系 DB - Read Only) │                   │ (顧客マスター DB - Encrypted NPI)                       │  │
│  └───────────┬────────────┘                   └───────────────────────────┬────────────────────────────┘  │
└──────────────┼────────────────────────────────────────────────────────────┼───────────────────────────────┘
               │ Dedicated AWS Direct Connect 10Gbps (Encrypted IPsec VPN)  │ Short-Lived OAuth 2.0 mTLS
               ▼                                                            ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   AWS Tokyo Region (ap-northeast-1)                                       │
│                                                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Private VPC Security Zone (10.100.0.0/16)                                                           │  │
│  │                                                                                                     │  │
│  │   ┌───────────────────────────────┐               ┌──────────────────────────────────────────────┐  │  │
│  │   │ AWS WAF + ALB (TLS 1.3)       ├──────────────►│ Bank AI ECS Fargate App Microservice         │  │  │
│  │   │ (OWASP & FISC Rate Rules)     │               │ (FastAPI / `src/backend`)                     │  │  │
│  │   └───────────────────────────────┘               └──────────────────────┬───────────────────────┘  │  │
│  │                                                                          │                          │  │
│  │      ┌───────────────────────────────────────────────────────────────────┼────────────────────────┐ │  │
│  │      ▼                                                                   ▼                        ▼ │  │
│  │ ┌──────────────────────────────────────────┐    ┌───────────────────────────────────┐  ┌─────────┴─────────┐ │  │
│  │ │ 1. INBOUND CONTROL PLANE & DLP           │    │ 2. CONTEXT RETRIEVAL LAYER        │  │ 5. FISC AUDIT    │ │  │
│  │ │  - Unicode NFC & Cipher Normalization    │    │  - OpenSearch Serverless (AOSS)   │  │    LOGGER &      │ │  │
│  │ │  - Direct & Indirect Injection Scanner  │    │  - Tier-Based RBAC Metadata Filter│  │    TELEMETRY     │ │  │
│  │ │  - PII Masking & Salted Token Vault      │    │  - Core Banking Account Lookup    │  │  - SHA-256 Sig   │ │  │
│  │ └────────────────────┬─────────────────────┘    └─────────────────┬─────────────────┘  │  - Async Write   │ │  │
│  │                      │ Sanitized Prompt                           │ Context Payload    └─────────┬─────────┘ │  │
│  │                      ▼                                            ▼                              │           │  │
│  │ ┌──────────────────────────────────────────────────────────────────────────────────┐             │           │  │
│  │ │ 3. INFERENCE LAYER (AWS PrivateLink VPC Endpoint)                                │             │           │  │
│  │ │  - Amazon Bedrock Runtime: Amazon Nova Lite (`amazon.nova-lite-v1:0`)            │             │           │  │
│  │ └────────────────────┬─────────────────────────────────────────────────────────────┘             │           │  │
│  │                      │ Raw Generated Output                                                      │           │  │
│  │                      ▼                                                                           │           │  │
│  │ ┌──────────────────────────────────────────────────────────────────────────────────┐             │           │  │
│  │ │ 4. OUTBOUND CONTROL PLANE & DLP                                                  │             │           │  │
│  │ │  - NLI Entailment Grounding Score ($\ge 0.85$) Verification                       │             │           │  │
│  │ │  - Outbound PII Reflection Scan & Numeric Financial Value Validation             │             │           │  │
│  │ │  - FIEA Investment Advice Prohibitions & Mandatory Disclaimer Injection          │             │           │  │
│  │ └────────────────────┬─────────────────────────────────────────────────────────────┘             │           │  │
│  │                      │ Validated Response + Metadata                                             │           │  │
│  └──────────────────────┼───────────────────────────────────────────────────────────────────────────┼───────────┘  │
│                         │                                                                           │              │
│                         ▼                                                                           ▼              │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ AWS Managed AI & Security Infrastructure Services                                                   │  │
│  │                                                                                                      │  │
│  │   ┌───────────────────────────────┐     ┌───────────────────────────────┐    ┌────────────────────┐  │  │
│  │   │ AWS KMS Customer Managed Keys │     │ Amazon S3 Object Lock Bucket  │    │ AWS GuardDuty &    │  │  │
│  │   │ (AES-256 CMK Key Rotation)    │     │ (10-Yr WORM Compliance Mode)  │    │ Security Hub Alerts│  │  │
│  │   └───────────────────────────────┘     └───────────────────────────────┘    └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key AWS Components & Roles

### 3.1 Amazon Bedrock (Model: Amazon Nova Lite)
- **Region**: AWS Tokyo (`ap-northeast-1`).
- **Model ID**: `amazon.nova-lite-v1:0`.
- **Connectivity**: Restricted strictly to Private Interface VPC Endpoints (`com.amazonaws.ap-northeast-1.bedrock-runtime`).
- **Data Sovereignty**: Inference processing remains 100% inside AWS Tokyo boundaries. Model input/output data is **never** retained for model training or stored unencrypted outside the VPC.

### 3.2 Dual Control Planes & DLP Security Layers
- **Inbound DLP & Guardrail**:
  - Unicode NFC normalizer stripping zero-width spaces (`U+200B`), invisible ciphers, Base64 smuggling, and homoglyphs.
  - Active ML threat classifier for direct prompt injection, system prompt extraction, and indirect prompt injection embedded in external inputs or RAG context.
  - Multi-pattern PII detector covering Japanese Katakana/Kanji names, 7-digit account numbers (`\d{7}`), 3-digit branch codes, 16-digit PCI card numbers (PAN), 12-digit My Number IDs, and phone numbers.
  - KMS-encrypted Salted Token Vault replacing raw PII with cryptographically secure UUID tokens (`[TOKEN_ACCT_a1b2c3d4]`).
- **Outbound DLP & Guardrail**:
  - Natural Language Inference (NLI) Entailment model computing grounding scores against retrieved RAG FAQ passages ($\text{Entailment Score} \ge 0.85$).
  - Outbound PII reflection scanner prohibiting accidental echoing of sensitive customer data.
  - Financial numeric cross-validator verifying interest rates, fee amounts in JPY, and balances against core sources.
  - FIEA Article 38 compliance classifier suppressing un-licensed stock recommendations or guaranteed investment return claims.
  - Automatic Japanese legal disclaimer appender.
- **Session Security & RAG Isolation**:
  - Ephemeral session memory zeroization within $< 10\text{ ms}$ upon thread termination or customer profile switch.
  - OpenSearch Serverless Tier-Based Metadata Filtering (`REGULAR`, `PREMIUM`, `VIP`, `SUPER_VIP`).
- **AWS KMS**: Encrypts all data at rest (S3, OpenSearch Vector Index, Token Vault, Audit logs) using Customer Managed Keys (CMK) with annual key rotation.

### 3.3 Storage, RAG & FISC Audit Logger
- **S3 Bucket**: Stores Rakuten Bank FAQ JSON collections and immutable audit logs with S3 Object Lock configured in `COMPLIANCE` WORM mode for 10 years (3,650 days).
- **Amazon OpenSearch Serverless (AOSS)**: Vector search engine hosting 1,536-dimensional embeddings with Cosine similarity scoring and private VPC access.
- **FISC Audit Logger**: Computes `SHA-256` signatures over session ID, timestamp, sanitized prompt, guardrail flags, Bedrock token usage, and latency, streaming logs asynchronously to CloudWatch Logs and encrypted S3.

---

## 4. Comprehensive Compliance & Standards Traceability Matrix

| Compliance Standard / Framework | Specific Section / Control | System Implementation & Architecture Defense | Operational Verification |
|---|---|---|---|
| **FISC Security Standards (FISC安全対策基準)** | Sec 3.1 Data Sovereignty, Sec 4.2 Cryptographic Audit, Sec 5.1 Transport | All resources bound to AWS Tokyo (`ap-northeast-1`); TLS 1.3 enforced; SHA-256 signed audit logs in S3 10-Yr Object Lock WORM bucket. | Verified (10-Yr WORM Lock Enabled) |
| **APPI (個人情報保護法 - Japan)** | Article 20 Security Measures, Article 23 Anonymization | Zero raw PII transmitted outside VPC or to Bedrock LLM endpoints; In-VPC KMS Salted Token Vault. | Verified (Multi-Pattern PII Redaction) |
| **FSA AI Guidelines & FIEA (金融商品取引法)** | FIEA Art 38 Prohibited Solicitations, FSA Explainability | NLI Entailment Grounding score $\ge 0.85$; automated investment advice blocking; mandatory legal disclaimers. | Verified (NLI Entailment Classifier) |
| **PCI-DSS 4.0** | Req 3.3/3.4 PAN Masking, Req 6.4.3 Web Defense, Req 8.4 MFA, Req 10.2 Log Integrity | Detection and tokenization of 16-digit Primary Account Numbers (PAN); WAF OWASP rules; Step-Up MFA for actions. | Verified (PCI PAN Regex & NER) |
| **GLBA Safeguards Rule (16 CFR Part 314)** | § 314.4(c)(1) NPI Encryption, § 314.4(c)(2) Access Control, § 314.4(e) Audit | KMS AES-256 encryption for Nonpublic Personal Information (NPI); zero-trust session context isolation. | Verified (KMS CMK Encryption) |
| **CFPB AI Chatbot Guidance** | 2023 Circular (Accurate Info, Non-Deception, Human Escalation) | NLI Grounding verification prevents financial hallucinations; UI explicit AI notice with one-click human escalation. | Verified (Grounding Score & Escalation UI) |
| **SR 11-7 / OCC 2011-12** | Model Risk Management (Conceptual Soundness, Outcomes Analysis) | Daily CloudWatch telemetry tracking model drift, refusal rates, guardrail block rates, and P50/P95/P99 latency. | Verified (Model Risk Dashboard) |
| **ISO 42001 / AIUC-1** | A.6 AI Attack Risk, A.8 System Validation, A.9 Behavior Limits | Active ML scanner for direct/indirect prompt injection; Unicode normalizer; deterministic fail-closed circuit breakers. | Verified (OWASP LLM Benchmark Tests) |
| **NYDFS Part 500 (23 NYCRR 500)** | 500.06 Audit Trails, 500.12 Multi-Factor Auth, 500.15 Encryption | SHA-256 immutable audit trails; Step-Up MFA for transactional boundaries; end-to-end TLS 1.3/KMS encryption. | Verified (NYDFS Audit Policy) |

---

## 5. Microservice Latency Budget & Failure-Mode Specifications

### 5.1 Latency Budget Allocation ($630\text{ ms}$ P95 Target)
- **Phase 1: Inbound DLP** (Regex + NER + Prompt Injection Scanner): **$45\text{ ms}$ (P95)**
- **Phase 2: RAG Retrieval** (OpenSearch Serverless Vector Query): **$85\text{ ms}$ (P95)**
- **Phase 3: LLM Inference** (Amazon Bedrock Nova Lite `ap-northeast-1` TTFT): **$450\text{ ms}$ (P95)**
- **Phase 4: Outbound DLP** (NLI Grounding Score + Outbound PII + FIEA Scan): **$50\text{ ms}$ (P95)**
- **Phase 5: FISC Audit Logger** (Async SHA-256 Hashing & CloudWatch Write): **$12\text{ ms}$ (P95 Async)**
- **Total Client SLA**: **$360\text{ ms}$ (P50)** / **$630\text{ ms}$ (P95)** / **$1,045\text{ ms}$ (P99)**.

### 5.2 Deterministic Failure-Mode Circuit Breakers
- **Inbound DLP Timeout (>100ms) / Error**: **FAIL CLOSED** $\rightarrow$ Return polite Japanese error message: `"システム混雑のためセキュリティ検証を終了できませんでした。時間をおいて再試行してください。"`
- **Prompt Injection Detected ($\ge 0.90$)**: **FAIL CLOSED** $\rightarrow$ Terminate pipeline, log Security Hub incident, return static response: `"セキュリティ保護のためリクエストを処理できませんでした。"`
- **Grounding Score Violation ($< 0.85$)**: **FAIL CLOSED** $\rightarrow$ Suppress LLM output, return verified static RAG reference answer link.
- **Bedrock API Rate Limit (429)**: **GRACEFUL DEGRADE** $\rightarrow$ Exponential backoff retry (max 3 retries, $300\text{ ms}$ total), failover to cached static FAQ answer.

---

## 6. Detailed AWS Architecture & Production Specifications

For complete subnet IPv4 routing plans, Amazon OpenSearch Serverless index schemas, S3 Object Lock Terraform IaC definitions, and RFC 2119 requirement specifications, refer to:

- [AWS Detailed Architecture Design Specification](aws_detailed_design_specification.md)
- [Enterprise Security, DLP & Compliance Specification](security_dlp_guardrails_requirements.md)
- [ADR 0007: Production AWS Detailed Architecture Design Specification](adr/0007-production-aws-detailed-design-specification.md)
- [ADR 0009: Enterprise DLP, Security Guardrails & Regulatory Compliance Framework](adr/0009-dlp-security-guardrails-and-compliance-framework.md)
- [ADR 0015: OpenSearch Serverless Network Isolation & Vector Dimension Standard](adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md)
- [ADR 0016: Deterministic Terraform IaC Architecture & Remote State Management](adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md)
- [ADR 0017: Enterprise IAM Least-Privilege Access & KMS Key Policy Topology](adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md)
- [ADR 0018: Production Observability, CloudWatch Alarms & Security Telemetry Targets](adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md)

