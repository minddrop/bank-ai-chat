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

## 3. Key AWS Components & Governing Architectural Decisions

### 3.1 Synchronous Compute Topology: AWS ECS Fargate vs AWS Lambda
- **Synchronous Chat Pipeline (AWS ECS Fargate)**: Hosted on AWS ECS Fargate warm container tasks across 3 Availability Zones (`ap-northeast-1a`, `1c`, `1d`) behind an Application Load Balancer. Guarantees 0ms cold starts, un-truncated HTTP Server-Sent Events (SSE) streaming, and avoids API Gateway 29-second proxy timeouts. *(See [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md))*
- **Asynchronous Workflows (AWS Lambda)**: Event-driven Lambda functions handle background tasks only (S3 audit log SHA-256 integrity verification, daily OpenSearch FAQ re-indexing, CloudWatch alarm processing). *(See [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md))*

### 3.2 Amazon Bedrock (Model: Amazon Nova Lite)
- **Region**: AWS Tokyo (`ap-northeast-1`).
- **Model ID**: `amazon.nova-lite-v1:0`. *(See [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md))*
- **Connectivity**: Restricted strictly to Private Interface VPC Endpoints (`com.amazonaws.ap-northeast-1.bedrock-runtime`).
- **Data Sovereignty**: Inference processing remains 100% inside AWS Tokyo boundaries. Model input/output data is **never** retained for model training or stored unencrypted outside the VPC.

### 3.3 Dual Control Planes & DLP Security Layers
- **Inbound DLP & Guardrail**: *(See [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*
  - Unicode NFC normalizer stripping zero-width spaces (`U+200B`), invisible ciphers, Base64 smuggling, and homoglyphs.
  - Active ML threat classifier for direct prompt injection, system prompt extraction, and indirect prompt injection embedded in external inputs or RAG context.
  - Multi-pattern PII detector covering Japanese Katakana/Kanji names, 7-digit account numbers (`\d{7}`), 3-digit branch codes, 16-digit PCI card numbers (PAN), 12-digit My Number IDs, and phone numbers.
  - KMS-encrypted Salted Token Vault replacing raw PII with cryptographically secure UUID tokens (`[TOKEN_ACCT_a1b2c3d4]`) using a dynamic salt fetched from Secrets Manager. *(See [ADR-0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md))*
- **Outbound DLP & Guardrail**: *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0013](file:///home/joe/src/bank-ai-chat/docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md))*
  - Natural Language Inference (NLI) Entailment model computing grounding scores against retrieved RAG FAQ passages ($\text{Entailment Score} \ge 0.85$).
  - Outbound PII reflection scanner prohibiting accidental echoing of sensitive customer data.
  - Financial numeric cross-validator verifying interest rates, fee amounts in JPY, and balances against core sources.
  - FIEA Article 38 compliance classifier suppressing un-licensed stock recommendations or guaranteed investment return claims.
  - Automatic Japanese legal disclaimer appender.
- **Transactional Intent & Zero Trust Step-Up Auth**:
  - Detects high-risk intent (`振込`, `暗証番号変更`, `口座解約`, `限度額変更`) and halts conversational AI execution, presenting a mandatory MFA step-up modal redirecting to Direct Banking. *(See [ADR-0014](file:///home/joe/src/bank-ai-chat/docs/adr/0014-zero-trust-step-up-authentication-boundary.md))*
- **Session Security & RAG Isolation**:
  - Ephemeral session memory zeroization within $< 10\text{ ms}$ upon thread termination or customer profile switch.
  - OpenSearch Serverless Tier-Based Metadata Filtering (`REGULAR`, `PREMIUM`, `VIP`, `SUPER_VIP`).
- **AWS KMS**: Encrypts all data at rest (S3, OpenSearch Vector Index, Token Vault, Audit logs) using Customer Managed Keys (CMK) with annual key rotation and strict key policies. *(See [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md))*

### 3.4 Storage, RAG & FISC Audit Logger
- **S3 Bucket**: Stores Rakuten Bank FAQ JSON collections and immutable audit logs with S3 Object Lock configured in `COMPLIANCE` WORM mode for 10 years (3,650 days). *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*
- **Amazon OpenSearch Serverless (AOSS)**: Vector search engine hosting **1024-dimensional embeddings** (produced by `amazon.titan-embed-text-v2:0`) with Cosine similarity scoring (`hnsw`) and private VPC access (`AllowPublicAccess = false`). *(See [ADR-0003](file:///home/joe/src/bank-ai-chat/docs/adr/0003-rakuten-bank-faq-rag-pipeline.md) and [ADR-0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md))*
- **FISC Audit Logger**: Computes `SHA-256` signatures over session ID, timestamp, sanitized prompt, guardrail flags, Bedrock token usage, and latency, streaming logs asynchronously to CloudWatch Logs and encrypted S3. *(See [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md))*

---

## 4. Comprehensive Compliance & Standards Traceability Matrix

| Compliance Standard / Framework | Specific Section / Control | System Implementation & Architecture Defense | Operational Verification | Governing ADR |
|---|---|---|---|---|
| **FISC Security Standards (FISC安全対策基準)** | Sec 3.1 Data Sovereignty, Sec 4.2 Cryptographic Audit, Sec 5.1 Transport | All resources bound to AWS Tokyo (`ap-northeast-1`); TLS 1.3 enforced; SHA-256 signed audit logs in S3 10-Yr Object Lock WORM bucket. | Verified (10-Yr WORM Lock Enabled) | [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **APPI (個人情報保護法 - Japan)** | Article 20 Security Measures, Article 23 Anonymization | Zero raw PII transmitted outside VPC or to Bedrock LLM endpoints; In-VPC KMS Salted Token Vault. | Verified (Multi-Pattern PII Redaction) | [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md) |
| **FSA AI Guidelines & FIEA (金融商品取引法)** | FIEA Art 38 Prohibited Solicitations, FSA Explainability | NLI Entailment Grounding score $\ge 0.85$; automated investment advice blocking; mandatory legal disclaimers. | Verified (NLI Entailment Classifier) | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **PCI-DSS 4.0** | Req 3.3/3.4 PAN Masking, Req 6.4.3 Web Defense, Req 8.4 MFA, Req 10.2 Log Integrity | Detection and tokenization of 16-digit Primary Account Numbers (PAN); WAF OWASP rules; Step-Up MFA for actions. | Verified (PCI PAN Regex & NER) | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0014](file:///home/joe/src/bank-ai-chat/docs/adr/0014-zero-trust-step-up-authentication-boundary.md) |
| **GLBA Safeguards Rule (16 CFR Part 314)** | § 314.4(c)(1) NPI Encryption, § 314.4(c)(2) Access Control, § 314.4(e) Audit | KMS AES-256 encryption for Nonpublic Personal Information (NPI); zero-trust session context isolation. | Verified (KMS CMK Encryption) | [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) |
| **CFPB AI Chatbot Guidance** | 2023 Circular (Accurate Info, Non-Deception, Human Escalation) | NLI Grounding verification prevents financial hallucinations; UI explicit AI notice with one-click human escalation. | Verified (Grounding Score & Escalation UI) | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **SR 11-7 / OCC 2011-12** | Model Risk Management (Conceptual Soundness, Outcomes Analysis) | Daily CloudWatch telemetry tracking model drift, refusal rates, guardrail block rates, and P50/P95/P99 latency. | Verified (Model Risk Dashboard) | [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| **ISO 42001 / AIUC-1** | A.6 AI Attack Risk, A.8 System Validation, A.9 Behavior Limits | Active ML scanner for direct/indirect prompt injection; Unicode normalizer; deterministic fail-closed circuit breakers. | Verified (OWASP LLM Benchmark Tests) | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **NYDFS Part 500 (23 NYCRR 500)** | 500.06 Audit Trails, 500.12 Multi-Factor Auth, 500.15 Encryption | SHA-256 immutable audit trails; Step-Up MFA for transactional boundaries; end-to-end TLS 1.3/KMS encryption. | Verified (NYDFS Audit Policy) | [ADR-0014](file:///home/joe/src/bank-ai-chat/docs/adr/0014-zero-trust-step-up-authentication-boundary.md), [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) |

---

## 5. Microservice Latency Budget & Failure-Mode Specifications

### 5.1 Latency Budget Allocation ($630\text{ ms}$ P95 Target) *(See [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md), [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md))*
- **Phase 1: Inbound DLP** (Regex + NER + Prompt Injection Scanner): **$45\text{ ms}$ (P95)**
- **Phase 2: RAG Retrieval** (OpenSearch Serverless Vector Query): **$85\text{ ms}$ (P95)**
- **Phase 3: LLM Inference** (Amazon Bedrock Nova Lite `ap-northeast-1` TTFT): **$450\text{ ms}$ (P95)**
- **Phase 4: Outbound DLP** (NLI Grounding Score + Outbound PII + FIEA Scan): **$50\text{ ms}$ (P95)**
- **Phase 5: FISC Audit Logger** (Async SHA-256 Hashing & CloudWatch Write): **$12\text{ ms}$ (P95 Async)**
- **Total Client SLA**: **$360\text{ ms}$ (P50)** / **$630\text{ ms}$ (P95)** / **$1,045\text{ ms}$ (P99)**.

### 5.2 Deterministic Failure-Mode Circuit Breakers *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*
- **Inbound DLP Timeout (>100ms) / Error**: **FAIL CLOSED** $\rightarrow$ Return polite Japanese error message: `"システム混雑のためセキュリティ検証を終了できませんでした。時間をおいて再試行してください。"`
- **Prompt Injection Detected ($\ge 0.90$)**: **FAIL CLOSED** $\rightarrow$ Terminate pipeline, log Security Hub incident, return static response: `"セキュリティ保護のためリクエストを処理できませんでした。"`
- **Grounding Score Violation ($< 0.85$)**: **FAIL CLOSED** $\rightarrow$ Suppress LLM output, return verified static RAG reference answer link.
- **Bedrock API Rate Limit (429)**: **GRACEFUL DEGRADE** $\rightarrow$ Exponential backoff retry (max 3 retries, $300\text{ ms}$ total), failover to cached static FAQ answer.

---

## 6. Detailed AWS Architecture & Production Specifications

For complete subnet IPv4 routing plans, Amazon OpenSearch Serverless index schemas, S3 Object Lock Terraform IaC definitions, and RFC 2119 requirement specifications, refer to:

- [AWS Detailed Architecture Design Specification](file:///home/joe/src/bank-ai-chat/docs/aws_detailed_design_specification.md)
- [Enterprise Security, DLP & Compliance Specification](file:///home/joe/src/bank-ai-chat/docs/security_dlp_guardrails_requirements.md)
- [ADR 0001: Japanese Banking Compliance & Control Planes](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md)
- [ADR 0002: AWS Bedrock Nova Lite Model Selection](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md)
- [ADR 0003: Rakuten Bank FAQ RAG Pipeline](file:///home/joe/src/bank-ai-chat/docs/adr/0003-rakuten-bank-faq-rag-pipeline.md)
- [ADR 0005: Hybrid Cloud & AWS PoC Architecture](file:///home/joe/src/bank-ai-chat/docs/adr/0005-hybrid-cloud-and-aws-poc-architecture.md)
- [ADR 0007: Production AWS Detailed Architecture Design Specification](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md)
- [ADR 0008: Decoupled Core Banking Database and API](file:///home/joe/src/bank-ai-chat/docs/adr/0008-decoupled-core-banking-database-and-api.md)
- [ADR 0009: Enterprise DLP, Security Guardrails & Regulatory Compliance Framework](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md)
- [ADR 0011: Compute Architecture Re-evaluation (ECS vs Lambda)](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md)
- [ADR 0012: In-VPC Salted Tokenization Vault](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md)
- [ADR 0013: SSE Streaming and Guardrail Buffer Architecture](file:///home/joe/src/bank-ai-chat/docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md)
- [ADR 0014: Zero Trust Step-Up Authentication Boundary](file:///home/joe/src/bank-ai-chat/docs/adr/0014-zero-trust-step-up-authentication-boundary.md)
- [ADR 0015: OpenSearch Serverless Network Isolation & Vector Dimension Standard](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md)
- [ADR 0016: Deterministic Terraform IaC Architecture & Remote State Management](file:///home/joe/src/bank-ai-chat/docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md)
- [ADR 0017: Enterprise IAM Least-Privilege Access & KMS Key Policy Topology](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md)
- [ADR 0018: Production Observability, CloudWatch Alarms & Security Telemetry Targets](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md)
- [ADR 0019: Local LLM Provider and Fallback Architecture](file:///home/joe/src/bank-ai-chat/docs/adr/0019-local-llm-provider-and-fallback-architecture.md)


