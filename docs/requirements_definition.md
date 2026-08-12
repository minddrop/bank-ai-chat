# Enterprise Requirements Definition & Specification
## Japanese Major Bank AI Customer Assistant System

---

## 1. Overview & Business Objectives

This document establishes the canonical, deterministic functional, non-functional, security, data schema, API interface, error handling, state transition, infrastructure topology, IAM, CI/CD, and cost estimation specifications for the **AI Customer Assistant System** of a major Japanese commercial bank (メガバンク).

The system serves as a 24/7/365 digital banking portal assistant deployed on AWS Tokyo (`ap-northeast-1`). It handles customer account inquiries, transaction history searches, personalized loyalty tier analysis, and general banking FAQ guidance while ensuring 100% compliance with Japanese legal regulations, Financial Services Agency (FSA) guidelines, and FISC security standards.

The primary engineering objective of this specification is **zero ambiguity, zero hand-waving, and zero manual fallback or unguided guessing** during deployment and Infrastructure as Code (IaC) implementation.

### 1.1 Architectural Decision Record (ADR) Traceability Matrix

Every requirement and technical specification in this document is bound to historical Architectural Decision Records (ADRs) located in [`docs/adr/`](file:///home/joe/src/bank-ai-chat/docs/adr). Engineers implementing features or deploying infrastructure should consult the respective governing ADRs for trade-off analysis, rationale, and design history:

| ADR ID | Decision Title | Primary Governing Requirements / Domain |
|---|---|---|
| [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md) | Japanese Banking Compliance & Control Planes | In-VPC Dual Control Planes, Keigo Persona |
| [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md) | AWS Bedrock Nova Lite Model Selection | LLM Inference Model (`amazon.nova-lite-v1:0`) |
| [ADR-0003](file:///home/joe/src/bank-ai-chat/docs/adr/0003-rakuten-bank-faq-rag-pipeline.md) | Rakuten Bank FAQ RAG Pipeline | RAG FAQ Indexing & Vector Search |
| [ADR-0004](file:///home/joe/src/bank-ai-chat/docs/adr/0004-synthetic-japanese-account-schema.md) | Synthetic Japanese Account Schema | Synthetic Banking Schemas & Validation |
| [ADR-0005](file:///home/joe/src/bank-ai-chat/docs/adr/0005-hybrid-cloud-and-aws-poc-architecture.md) | Hybrid Cloud & AWS PoC Architecture | On-Premise Core Banking Integration & VPC Topology |
| [ADR-0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md) | CI/CD & Production Cost Estimation | CI/CD Quality Gates & Financial Model |
| [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) | Production AWS Detailed Design Specification | 3-Tier VPC Subnetting & ALB TLS 1.3 |
| [ADR-0008](file:///home/joe/src/bank-ai-chat/docs/adr/0008-decoupled-core-banking-database-and-api.md) | Decoupled Core Banking Database & API | Core Banking REST Client & Fallback Controls |
| [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) | DLP Security Guardrails & Compliance Framework | Pre/Post-LLM DLP, NLI Entailment, Audit WORM |
| [ADR-0010](file:///home/joe/src/bank-ai-chat/docs/adr/0010-personalized-account-tier-reasoning.md) | Personalized Account Tier Reasoning | Happy Program Loyalty Tier Rules & Explanation |
| [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) | Compute Architecture Re-evaluation (ECS vs Lambda) | Synchronous ECS Fargate vs Async Lambda |
| [ADR-0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md) | In-VPC Salted Tokenization Vault | KMS CMK Salted HMAC-SHA256 Tokenization |
| [ADR-0013](file:///home/joe/src/bank-ai-chat/docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) | SSE Streaming & Guardrail Buffer Architecture | Chunked SSE Streaming & Output Buffer |
| [ADR-0014](file:///home/joe/src/bank-ai-chat/docs/adr/0014-zero-trust-step-up-authentication-boundary.md) | Zero Trust Step-Up Authentication Boundary | Transaction Intent Filter & Direct Banking MFA |
| [ADR-0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md) | OpenSearch Serverless Isolation & Vector Dimension | 1024-dim Titan Text Embeddings v2 & AOSS VPC VPCE |
| [ADR-0016](file:///home/joe/src/bank-ai-chat/docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md) | Terraform IaC Architecture & Remote State | 100% IaC Codification & S3 State Locking |
| [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) | IAM Least Privilege Access & KMS Key Policies | TaskRole vs ExecutionRole, KMS Policies |
| [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) | Observability CloudWatch Alarms & Security Telemetry | CloudWatch Metrics, Security Alarms, P95 SLAs |
| [ADR-0019](file:///home/joe/src/bank-ai-chat/docs/adr/0019-local-llm-provider-and-fallback-architecture.md) | Local LLM Provider & Fallback Architecture | Offline Dev Light Local Engine & Dev Fallback |

---

## 2. Regulatory & Legal Framework

### 2.1 Act on the Protection of Personal Information (個人情報保護法 - APPI)
- **Zero PII Transmission Boundary**: Absolutely no raw Personally Identifiable Information (PII) may leave the In-VPC Control Plane boundaries or be passed to external LLM endpoints (including Amazon Bedrock). *(See [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md) and [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) for rationale)*
- **PII Scrubbing Taxonomy & Deterministic Matching**:
  - Full Kanji / Katakana Names (`口座名義人`: `ヤマダ タロウ`, `山田 太郎`) -> Matched via regex `^[\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\s]{2,20}$` and scrubbed to `[NAME_MASKED]`.
  - Account Numbers (`口座番号`: 7-digit numeric `\d{7}`) -> Scrubbed to `[ACCOUNT_MASKED: XXXXXXX]`.
  - Branch Codes (`支店コード`: 3-digit numeric `\d{3}`) -> Scrubbed to `[BRANCH_MASKED: XXX]`.
  - Passwords, PINs, Security Card Coordinates (`暗証番号`, `PIN`) -> Scrubbed to `[PIN_MASKED]`.
  - Phone Numbers (`電話番号`: `0\d{1,4}-\d{1,4}-\d{4}` or `0\d{9,10}`) -> Scrubbed to `[TEL_MASKED]`.
- **Enforcement**: The In-VPC Input Guardrail intercepts prompts, extracts raw PII into a KMS CMK salted HMAC-SHA256 vault, and replaces raw values with tokenized placeholders before prompt assembly. *(See [ADR-0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md) for vault architecture)*

### 2.2 Financial Services Agency (FSA) AI Guidelines & FIEA (金融庁ガイドライン・金融商品取引法)
- **AI Explainability & Governance**: Deterministic audit logging for all AI responses, including input scrubbed tokens, retrieved RAG contexts, vector similarity scores, and grounding entailment scores. *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*
- **Financial Instruments and Exchange Act (金融商品取引法 - FIEA Article 38)**: Prohibits un-licensed investment solicitation, stock/mutual fund purchase recommendations, or guaranteed return projections.
- **Mandatory Disclaimers**: Automatic append of standardized Japanese legal notices stating that AI answers provide general information only and do not form binding financial advice or legal contracts. *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*

### 2.3 FISC Security Guidelines for Financial Information Systems (FISC安全対策基準)
- **Data Sovereignty**: Infrastructure, storage, and LLM processing (Amazon Bedrock) strictly restricted to AWS Tokyo (`ap-northeast-1`) or Osaka (`ap-northeast-2`) regions. *(See [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md) and [ADR-0005](file:///home/joe/src/bank-ai-chat/docs/adr/0005-hybrid-cloud-and-aws-poc-architecture.md))*
- **Encryption**: AES-256 (KMS CMK) for data at rest across S3, OpenSearch, and DynamoDB; TLS 1.3 for data in transit. *(See [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md))*
- **Audit Retention**: Immutable, tamper-evident log streams with SHA-256 signature verification retained for 10 years per banking regulations using S3 Object Lock in `COMPLIANCE` mode. *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*

### 2.4 Banking Act (銀行法 - Ginkō Hō)
- **Contract Boundary**: AI assistant responses are strictly informational. Actionable operations (fund transfers `振込`, PIN resets, account closures, credit limit changes) are prohibited within conversational chat and MUST require step-up Multi-Factor Authentication (MFA) redirecting the customer to the official Internet Banking portal. *(See [ADR-0014](file:///home/joe/src/bank-ai-chat/docs/adr/0014-zero-trust-step-up-authentication-boundary.md))*

---

## 3. Data Schemas & Validation Contracts

To fulfill enterprise production standards while protecting customer privacy under APPI, realistic synthetic datasets and validation rules are defined.

### 3.1 Validation Rules & Character Rules
- **Kanji Name**: Regex `^[\u4E00-\u9FFF\u3040-\u309F\s]{1,20}$`
- **Katakana Name**: Regex `^[\u30A0-\u30FF\u30FC\s]{1,30}$`
- **Account Number**: Regex `^\d{7}$`
- **Branch Code**: Regex `^\d{3}$`
- **Zero-Width Character Filter**: Automatically strip unicode ranges `\u200B-\u200D`, `\uFEFF` prior to guardrail evaluation.

### 3.2 Customer Profile Schema (`CustomerProfile`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CustomerProfile",
  "type": "object",
  "properties": {
    "customer_id": {
      "type": "string",
      "pattern": "^CUST-\\d{4}$",
      "description": "Unique Synthetic Customer ID"
    },
    "name_kanji": {
      "type": "string",
      "pattern": "^[\\u4E00-\\u9FFF\\u3040-\\u309F\\s]{1,20}$",
      "description": "Customer Name in Kanji"
    },
    "name_katakana": {
      "type": "string",
      "pattern": "^[\\u30A0-\\u30FF\\u30FC\\s]{1,30}$",
      "description": "Customer Name in Katakana"
    },
    "birth_date": {
      "type": "string",
      "format": "date",
      "description": "Date of Birth (YYYY-MM-DD)"
    },
    "branch_code": {
      "type": "string",
      "pattern": "^\\d{3}$",
      "description": "3-digit Japanese Bank Branch Code"
    },
    "branch_name": {
      "type": "string",
      "description": "Branch Name in Japanese"
    },
    "account_number": {
      "type": "string",
      "pattern": "^\\d{7}$",
      "description": "Main Savings 7-digit Account Number"
    },
    "customer_tier": {
      "type": "string",
      "enum": ["SUPER_VIP", "VIP", "PREMIUM", "REGULAR"],
      "description": "Loyalty Program Tier"
    },
    "happy_program_stage": {
      "type": "string",
      "description": "Fee waiver description stage"
    }
  },
  "required": ["customer_id", "name_kanji", "name_katakana", "branch_code", "account_number", "customer_tier"]
}
```

### 3.3 Account Schema (`BankAccount`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BankAccount",
  "type": "object",
  "properties": {
    "account_id": {
      "type": "string",
      "pattern": "^ACC-\\d{4}-\\w+$"
    },
    "account_type": {
      "type": "string",
      "enum": ["普通預金", "定期預金", "外貨預金", "カードローン"]
    },
    "account_type_code": {
      "type": "string",
      "enum": ["SAVINGS", "TIME_DEPOSIT", "FOREIGN_USD", "CARD_LOAN"]
    },
    "balance": {
      "type": "number"
    },
    "currency": {
      "type": "string",
      "enum": ["JPY", "USD", "EUR"]
    },
    "interest_rate": {
      "type": "string",
      "pattern": "^\\d+(\\.\\d+)?%$"
    },
    "maturity_date": {
      "type": ["string", "null"],
      "format": "date"
    }
  },
  "required": ["account_id", "account_type", "account_type_code", "balance", "currency", "interest_rate"]
}
```

### 3.4 Transaction History Schema (`BankTransaction`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BankTransaction",
  "type": "object",
  "properties": {
    "transaction_id": {
      "type": "string",
      "pattern": "^TXN-\\d{5}$"
    },
    "date": {
      "type": "string",
      "format": "date"
    },
    "type": {
      "type": "string"
    },
    "amount": {
      "type": "number"
    },
    "currency": {
      "type": "string",
      "enum": ["JPY", "USD"]
    },
    "description": {
      "type": "string"
    },
    "balance_after": {
      "type": "number"
    }
  },
  "required": ["transaction_id", "date", "type", "amount", "currency", "description", "balance_after"]
}
```

### 3.5 FAQ Knowledge Schema (`FAQItem`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "FAQItem",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^FAQ-[A-Z]{2}-\\d{4,}$"
    },
    "category": {
      "type": "string"
    },
    "question": {
      "type": "string"
    },
    "answer": {
      "type": "string"
    },
    "url": {
      "type": "string",
      "format": "uri"
    },
    "vector_embedding": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 1024,
      "maxItems": 1024,
      "description": "1024-dimensional float vector produced by Amazon Titan Text Embeddings v2"
    }
  },
  "required": ["id", "category", "question", "answer", "url"]
}
```

---

## 4. Functional Features List

| ID | Feature Name | Inputs | Outputs | Deterministic Handling / Rule | Failure Mode & Fallback | Priority | Governing ADR |
|---|---|---|---|---|---|---|---|
| **FR-01** | Account Balance Inquiry | `customer_id`, `account_type_code` | Balance JSON, Japanese summary | Query core banking mock database; redact PII before rendering. | If core banking times out, return `ERR-BANK-001` with Keigo apology. | High | [ADR-0008](file:///home/joe/src/bank-ai-chat/docs/adr/0008-decoupled-core-banking-database-and-api.md) |
| **FR-02** | Transaction History View | `customer_id`, `limit`, `start_date` | Sorted list of transactions | Filter by date range, default limit 10, max limit 50. | Return empty list with notification if zero records found. | High | [ADR-0004](file:///home/joe/src/bank-ai-chat/docs/adr/0004-synthetic-japanese-account-schema.md) |
| **FR-03** | Rakuten FAQ RAG Search | `query_text`, `top_k` (default 3) | Array of `FAQItem` + similarity scores | Vector embedding query via OpenSearch (`cosine >= 0.75`). | If OpenSearch fails, fallback to keyword search or return general guidance. | High | [ADR-0003](file:///home/joe/src/bank-ai-chat/docs/adr/0003-rakuten-bank-faq-rag-pipeline.md), [ADR-0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md) |
| **FR-04** | Input PII Redaction | Raw user prompt | Sanitized prompt, PII mapping tokens | Match regex for account numbers, names, phone numbers, branch codes; replace with tokens. | If PII Vault errors, trip circuit breaker and return `ERR-PII-001`. | High | [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md) |
| **FR-05** | Prompt Injection Filter | Raw user prompt | Injection Flag (`is_injection`), Risk Score | Multi-pattern regex + classifier for system prompt override/jailbreak attempts. | Block prompt immediately, return `ERR-SEC-001`, log to security audit. | High | [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **FR-06** | Output PII Leak Detector | Raw generated response | Validated/Cleaned response | Post-generation scan matching account numbers or names. Scrub matched tokens before stream byte send. | Scrub detected pattern and log output anomaly. | High | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0013](file:///home/joe/src/bank-ai-chat/docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) |
| **FR-07** | RAG Grounding Verification | Generated text, RAG context | Grounding score (`0.0 - 1.0`), `is_grounded` | Compute entailment score; requirement: `score >= 0.85`. | If `score < 0.85`, append unverified grounding disclaimer to output. | High | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **FR-08** | Investment Advice Limitation | User prompt / LLM answer | Compliance Flag (`is_investment_advice`) | Scan for stock picks, mutual fund yield guarantees, investment recommendations per FIEA Art. 38. | Block response, output standardized FIEA compliance notice. | High | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **FR-09** | Disclaimer Injection | Validated AI response | Response + Formatted Disclaimer | Automatically append `【重要事項・免責事項】` footer to every response. | Mandatory stage; non-bypassable. | High | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **FR-10** | FISC Audit Logger | Session ID, prompt, response, latency, hashes | SHA-256 signed log entry | Generate SHA-256 digest of payload, write asynchronously to CloudWatch & S3 WORM bucket. | Retry async queue; log local alert if S3 write fails. | High | [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **FR-11** | Customer Profile Switcher | `target_customer_id` | Profile update event, state refreshed | Toggle active customer context in web demo UI (`山田 太郎`, `佐藤 花子`). | Revert to default customer `CUST-1001` if ID invalid. | High | [ADR-0004](file:///home/joe/src/bank-ai-chat/docs/adr/0004-synthetic-japanese-account-schema.md) |
| **FR-12** | Live Control Plane Dashboard | Telemetry log stream | Real-time visual metrics | Render live Input Guardrail status, grounding score gauge, and audit log tailing in UI. | Display status indicator offline if websocket/SSE disconnects. | High | [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| **FR-13** | Multi-account Support | `customer_id` | All associated `BankAccount` records | Fetch Ordinary, Time Deposit, Foreign Currency USD, and Card Loan balances. | Display unavailable status for uninitialized sub-accounts. | Medium | [ADR-0004](file:///home/joe/src/bank-ai-chat/docs/adr/0004-synthetic-japanese-account-schema.md) |
| **FR-14** | Step-Up Auth Warning | Sensitive action intent | MFA Warning modal / link | Detect transactional intent (`振込`, `暗証番号変更`, `解約`) and provide Direct Banking link. | Suppress AI execution, mandate MFA portal transition. | Medium | [ADR-0014](file:///home/joe/src/bank-ai-chat/docs/adr/0014-zero-trust-step-up-authentication-boundary.md) |
| **FR-15** | Quick Sample Prompts | Preset prompt chip click | Pre-populated prompt payload | Send predefined benchmark prompts (Balance check, FAQ inquiry, PII test, Injection test). | Default to standard prompt execution pipeline. | Medium | [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md) |
| **FR-16** | Personalized Loyalty Tier Reasoning | `customer_id`, balance delta | Savings delta calculation & Keigo explanation | Calculate balance required to reach next Happy Program tier (`スーパーVIP`, `VIP`) and detail fee waiver benefits. | If balance fetch fails, return general tier benefit threshold table. | High | [ADR-0010](file:///home/joe/src/bank-ai-chat/docs/adr/0010-personalized-account-tier-reasoning.md) |
| **FR-17** | Local LLM Provider Mode | Environment vars `LLM_PROVIDER=local`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_URL` | Local LLM response payload | Route prompt generation through `LocalLLMClient` via Ollama/OpenAI API endpoint or internal Local Light Dev Engine. | If local server offline, fallback to Local Light Dev Engine. Restricted strictly to non-production dev environments. | High | [ADR-0019](file:///home/joe/src/bank-ai-chat/docs/adr/0019-local-llm-provider-and-fallback-architecture.md) |

---

## 5. Non-Functional Requirements (NFR)

| ID | Category | Requirement Specification | Metric / Target | Verification Method | Governing ADR |
|---|---|---|---|---|---|
| **NFR-01** | **Availability** | System SLA for Backend API and Control Planes. | 99.99% Uptime | Multi-AZ ECS Fargate across 3 AZs (`ap-northeast-1a`, `1c`, `1d`). | [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) |
| **NFR-02** | **End-to-End Latency** | Full request execution P95 latency limit. | **< 800ms P95** (< 1,200ms P99) | CloudWatch Synthetic Monitoring & APM trace timing. | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md), [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) |
| **NFR-03** | **Throughput** | Peak concurrent request throughput. | 1,000 TPS | Distributed load testing via Locust / AWS Distributed Load Testing. | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **NFR-04** | **Data Sovereignty** | Compute, LLM inference, and storage location. | 100% AWS Tokyo (`ap-northeast-1`) | AWS IAM Condition Keys `aws:RequestedRegion == ap-northeast-1`. | [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md), [ADR-0005](file:///home/joe/src/bank-ai-chat/docs/adr/0005-hybrid-cloud-and-aws-poc-architecture.md) |
| **NFR-05** | **Encryption at Rest** | KMS CMK AES-256 encryption across storage layers. | 100% KMS Encrypted | AWS Config Compliance Rule `s3-bucket-server-side-encryption-enabled`. | [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) |
| **NFR-06** | **Encryption in Transit**| TLS 1.3 enforced for internal microservices & ALB. | TLS 1.3 Only | SSL Labs Audit / ALB Listener Policy `ELBSecurityPolicy-TLS13-1-2-2021-06`. | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **NFR-07** | **Audit Retention** | WORM compliance audit retention period. | 10 Years Immutable | S3 Object Lock `COMPLIANCE` mode with legal hold enabled. | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **NFR-08** | **Disaster Recovery** | Recovery Point Objective (RPO) & Time (RTO). | RPO = 0, RTO < 15 mins | AWS Backup Cross-Region replication to Osaka (`ap-northeast-2`). | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **NFR-09** | **DDoS & Web Security** | Infrastructure protection against OWASP Top 10. | Zero successful bypasses | AWS WAF rate-limiting (100 req/min/IP) + AWS Shield Standard. | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **NFR-10** | **Browser Support** | Desktop & Mobile Japanese browser compatibility. | Chrome, Edge, Safari, iOS/Android | BrowserStack automated cross-browser testing. | [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md) |
| **NFR-11** | **Real-Time Streaming**| HTTP Server-Sent Events (SSE) streaming support. | Zero 29s proxy timeouts | ALB idle timeout 300s; ECS Fargate continuous HTTP/1.1 SSE stream. | [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md), [ADR-0013](file:///home/joe/src/bank-ai-chat/docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) |
| **NFR-12** | **Zero Cold Starts** | Latency penalty for initial chat prompts. | 0ms Cold Start overhead | ECS Fargate minimum 4 warm tasks active 24/7/365. | [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) |
| **NFR-13** | **IaC Codification** | Zero manual AWS console resource creation. | 100% Codified in Terraform | `terraform plan` clean execution in GitHub Actions OIDC pipeline. | [ADR-0016](file:///home/joe/src/bank-ai-chat/docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md) |

---

## 6. Complete Infrastructure & Deployment Specifications

*(See [ADR-0005](file:///home/joe/src/bank-ai-chat/docs/adr/0005-hybrid-cloud-and-aws-poc-architecture.md), [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md), and [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) for architectural decision history)*

### 6.1 Network & VPC Subnet Layout
- **Primary VPC**: CIDR `10.100.0.0/16` in AWS Tokyo (`ap-northeast-1`).
- **Subnet Decomposition**:
  - `Public Subnets` (10.100.1.0/24, 10.100.2.0/24, 10.100.3.0/24): Hosts Application Load Balancers (ALB) and NAT Gateways.
  - `Private App Subnets` (10.100.10.0/23, 10.100.12.0/23, 10.100.14.0/23): Hosts ECS Fargate tasks running FastAPI control planes.
  - `Isolated Data Subnets` (10.100.20.0/24, 10.100.21.0/24, 10.100.22.0/24): Hosts AWS PrivateLink VPC Endpoints (Bedrock, AOSS, KMS, S3, Secrets Manager, CloudWatch Logs). Zero outbound route to 0.0.0.0/0.

### 6.2 Compute Architecture (AWS ECS Fargate)
- **Container Architecture**: Linux `ARM64` (AWS Graviton2). *(See [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md))*
- **Task Resource Allocation**: 1 vCPU (1024 CPU units), 2 GB RAM (2048 MB memory).
- **Auto-scaling Policy**: Minimum 4 tasks (multi-AZ warm base), maximum 30 tasks. Triggers at 70% CPU or 75% Memory utilization.
- **Task Execution Security**: Non-root container execution (`user: "10001:10001"`), `readonlyRootFilesystem: true`, container health check executing every 15s on `/health`.

### 6.3 OpenSearch Serverless (AOSS) & Storage Precision
- **Collection Engine**: `VECTORSEARCH` with Cosine similarity distance metric (`hnsw`). *(See [ADR-0003](file:///home/joe/src/bank-ai-chat/docs/adr/0003-rakuten-bank-faq-rag-pipeline.md))*
- **Vector Dimension Standard**: **1024 dimensions** produced by Amazon Titan Text Embeddings v2 (`amazon.titan-embed-text-v2:0`). *(See [ADR-0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md))*
- **AOSS Network Security**: Network policy `AllowPublicAccess = false`, bound strictly to Private VPC Endpoint (`vpce-xxxxxxxxxxxxxxxxx`). *(See [ADR-0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md))*
- **S3 Audit Bucket**: `japan-bank-ai-audit-log-ap-northeast-1` configured with S3 Object Lock in `COMPLIANCE` mode for 10 years (3,650 days), encrypted with KMS CMK. *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*

### 6.4 Secrets Management & IAM Topology
- **Secrets Manager ARNs**:
  - `arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:bank-ai/vault-hmac-salt` *(See [ADR-0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md))*
  - `arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:bank-ai/oauth-client-secret`
- **IAM Least Privilege**: *(See [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md))*
  - `BankAiEcsTaskExecutionRole`: ECR image pull, Secrets Manager read, CloudWatch log streams.
  - `BankAiEcsTaskRole`: Bedrock model invocation on `amazon.nova-lite-v1:0`, OpenSearch Serverless API access, S3 PutObject on audit bucket, KMS GenerateDataKey/Decrypt on CMK ARN `alias/bank-ai-cmk`.

---

## 7. Complete REST & SSE API Interface Specifications

*(See [ADR-0013](file:///home/joe/src/bank-ai-chat/docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) for SSE streaming and guardrail buffer specs)*

### 7.1 API Overview & Global Headers

All API endpoints enforce HTTPS TLS 1.3 and require the following global headers:

| Header Name | Type | Mandatory | Description | Example |
|---|---|---|---|---|
| `Content-Type` | String | Yes | Media type of payload | `application/json` |
| `X-Session-ID` | String | Yes | Unique UUIDv4 session identifier | `123e4567-e89b-12d3-a456-426614174000` |
| `X-Customer-ID` | String | Yes | Synthetic Customer ID | `CUST-1001` |
| `X-Guardrail-Mode` | String | No | Guardrail enforcement level | `STRICT` (default), `AUDIT_ONLY` |

---

### 7.2 POST `/api/v1/chat/stream` (Synchronous SSE Chat Inference)

Initiates an interactive chat session with real-time Server-Sent Events (SSE) response streaming.

#### Request Payload Schema
```json
{
  "customer_id": "CUST-1001",
  "message": "普通預金の残高と他行への振込手数料を教えてください。",
  "include_account_context": true,
  "stream": true
}
```

#### Response Stream Event Frames (SSE Format)

1. **`event: metadata`** (Emitted first upon pipeline validation)
```json
data: {"session_id": "123e4567-e89b-12d3-a456-426614174000", "input_guardrail": {"pii_masked": true, "injection_detected": false}, "timestamp": "2026-08-07T07:20:00Z"}
```

2. **`event: token`** (Emitted repeatedly as tokens arrive from Bedrock)
```json
data: {"delta": "ヤマダ タロウ様、普通預金の現在残高は "}
```

3. **`event: guardrail`** (Emitted post-generation after Output Guardrail verification)
```json
data: {"grounding_score": 0.96, "disclaimer_appended": true, "fiea_passed": true}
```

4. **`event: done`** (Emitted upon stream completion)
```json
data: {"status": "COMPLETED", "total_tokens": 284, "latency_ms": 520}
```

5. **`event: error`** (Emitted if an exception occurs during streaming)
```json
data: {"code": "ERR-LLM-003", "message": "モデル応答の取得中にタイムアウトが発生しました。", "retryable": true}
```

---

## 8. Observability & Alarm Targets

*(See [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) for telemetry targets and CloudWatch alarm specs)*

| Metric Name | Namespace | Statistic | Window | Alarm Threshold | Priority | Action | Governing ADR |
|---|---|---|---|---|---|---|---|
| `TargetResponseTime` | `AWS/ApplicationELB` | P95 | 5 mins | `> 800 ms` | P2 High | Scale out ECS & alert DevOps | [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md), [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| `HTTPCode_Target_5XX_Count` | `AWS/ApplicationELB` | Sum | 1 min | `> 5 reqs` | P1 Critical | Trigger immediate page & rollback | [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| `GuardrailBlockCount` | `BankAi/ControlPlane` | Sum | 5 mins | `> 10 blocks` | P2 Security | Notify SOC of prompt injection surge | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| `GroundingViolationCount` | `BankAi/ControlPlane` | Sum | 5 mins | `> 5 violations` | P2 High | Alert AI Governance team for RAG drift | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| `S3AuditWriteError` | `BankAi/Audit` | Sum | 1 min | `> 0 errors` | P0 Blocker | Fail closed; alert On-Call Lead | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |

---

## 9. Production AWS Cost Estimation

*(See [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md), [ADR-0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md), and [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) for cost estimation decisions)*

### Breakdown (AWS Tokyo Region `ap-northeast-1`) for 1,000,000 interactions/month

| AWS Service | Unit Cost Metric | Monthly Cost (USD) | Monthly Cost (JPY @ 150/$) | Governing ADR |
|---|---|---|---|---|
| **Amazon Bedrock (Nova Lite)** | 1M Reqs (500 in / 300 out tokens) | $120.00 | ¥18,000 | [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md) |
| **AWS ECS Fargate** | 4 Tasks (1 vCPU, 2GB RAM) Multi-AZ | $180.00 | ¥27,000 | [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) |
| **Amazon OpenSearch Serverless**| 2 OCU (Vector Search Index) | $140.00 | ¥21,000 | [ADR-0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md) |
| **Amazon S3** | Audit logs with Object Lock (50GB) | $15.00 | ¥2,250 | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **AWS KMS** | 2 CMK Keys + API requests | $2.00 | ¥300 | [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) |
| **AWS WAF & Shield** | Managed ACL + OWASP Rules | $35.00 | ¥5,250 | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **Amazon CloudWatch** | Metrics, logs, alarms | $25.00 | ¥3,750 | [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| **Application Load Balancer** | Dual-AZ ALB + TLS 1.3 | $28.00 | ¥4,200 | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **Total Monthly Cost** | | **$545.00 / month** | **¥81,750 / 月** | [ADR-0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md) |
