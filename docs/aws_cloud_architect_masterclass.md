# AWS Cloud Architect Masterclass: Japanese Major Bank AI Assistant
## Enterprise Architecture, Security Controls, Compliance & Implementation Specification

> **Target Audience**: AWS Cloud Architects, Enterprise Security Auditors, Infrastructure Leads, and Engineering Directors.
> **Compliance Standards**: FISC Security Standards (Japan), APPI (個人情報保護法), FSA Guidelines (金融庁ガイドライン), FIEA Article 38 (金融商品取引法), PCI-DSS 4.0, GLBA, ISO 42001.
> **Deployment Region**: AWS Tokyo (`ap-northeast-1`)

---

## 1. Executive Topology & Multi-Tier VPC Network Architecture

### 1.1 Hybrid Cloud Infrastructure Pattern
The system bridges an **On-Premise Core Banking Mainframe Center (勘定系センター)** with a high-availability **AWS Private Cloud** in `ap-northeast-1`.

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

### 1.2 Subnet Layout & Traffic Isolation Boundary
- **Public Subnets (AZ1: `10.100.1.0/24`, AZ2: `10.100.2.0/24`)**: Hosts Dual-AZ Application Load Balancer (ALB) and NAT Gateways. Strictly no application application business logic or database components are placed here.
- **Application Private Subnets (AZ1: `10.100.10.0/24`, AZ2: `10.100.20.0/24`)**: Hosts AWS ECS Fargate Tasks running containerized microservices (`src/backend`). No direct ingress from internet; accepts traffic exclusively from ALB Security Group on port 8000.
- **Isolated Private Endpoints Subnets (AZ1: `10.100.100.0/24`, AZ2: `10.100.200.0/24`)**: Hosts Interface VPC Endpoints (AWS PrivateLink). All AWS service calls (Bedrock, KMS, AOSS, S3, CloudWatch) route strictly through internal AWS backbone network IPs without traversing the public internet.

---

## 2. Compute Architecture Evaluation: AWS ECS Fargate vs AWS Lambda ([ADR 0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md))

### 2.1 Architectural Decision Rationale
During architecture review, serverless compute (AWS Lambda + API Gateway) was evaluated against containerized compute (AWS ECS Fargate). **ECS Fargate was selected as the mandatory standard** for the following architectural reasons:

| Evaluation Dimension | AWS Lambda + API Gateway | AWS ECS Fargate (Chosen Standard) | Architectural Implication |
|---|---|---|---|
| **API Timeout Limits** | Hard 29-second API Gateway limit | Configurable HTTP timeout (up to 300s) | Bedrock LLM generation + Guardrail evaluation + RAG context lookup can take 2-5 seconds. API Gateway's hard 29s proxy limit creates severe outage risk during peak load retries. |
| **Server-Sent Events (SSE)** | Requires API Gateway HTTP API streaming workaround | Native HTTP/1.1 & HTTP/2 chunked SSE support | Enables real-time token streaming to frontend client with zero response buffering ([ADR 0013](file:///home/joe/src/bank-ai-chat/docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md)). |
| **Cold Start Latency** | 500ms - 3,000ms VPC attachment penalty | Zero Cold Starts (Pre-warmed auto-scaling pools) | Guarantees strict banking SLA: P50 $\le 360\text{ ms}$, P95 $\le 630\text{ ms}$. |
| **Control Plane Memory Footprint** | Memory constraints per invocation | Shared in-memory vector index cache & NER regex engines | In-VPC PII regex engines and NLI entailment scoring models execute in-memory with sub-10ms overhead. |

---

## 3. AI Model Selection & Governance: Amazon Bedrock ([ADR 0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md))

### 3.1 Model Sizing & Data Sovereignty
- **Model ID**: `amazon.nova-lite-v1:0`
- **Region**: AWS Tokyo (`ap-northeast-1`).
- **Data Privacy Guarantee**: Under AWS Bedrock service terms for Tokyo region:
  1. Customer prompts and generated model responses are **never** used to train Amazon foundation models.
  2. In-flight data is encrypted with TLS 1.3 and processed exclusively within `ap-northeast-1`.
  3. No prompt payload data is stored unencrypted on disk by AWS.

### 3.2 Boto3 SDK Session Provider Resolution
The application uses boto3's default session credential chain, allowing seamless authentication across:
1. **Developer Workstations**: AWS SSO (`aws login`) / temporary STS tokens.
2. **ECS Fargate Tasks**: IAM Task Execution Roles (IAM Roles for Tasks) using short-lived container metadata credentials.

---

## 4. In-VPC Dual Control Planes & Regulatory Compliance

### 4.1 Inbound Control Plane (APPI Compliance - [ADR 0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md) & [ADR 0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md))
To comply with Japan's **Act on the Protection of Personal Information (APPI / 個人情報保護法)**:

1. **Unicode NFC Normalization**: Strips zero-width spaces (`U+200B`), invisible ciphers, and Base64 prompt injection attempts before tokenization.
2. **Multi-Pattern PII Scrubbing**:
   - Japanese Kanji/Katakana Names (`ヤマダ タロウ`, `山田 太郎`) $\rightarrow$ Scrubbed to `[NAME_MASKED]`.
   - 7-digit Account Numbers (`\d{7}`) $\rightarrow$ Scrubbed to `[ACCOUNT_MASKED: XXXXXXX]`.
   - 3-digit Branch Codes (`\d{3}`) $\rightarrow$ Scrubbed to `[BRANCH_MASKED: XXX]`.
   - PINs / Passwords $\rightarrow$ Scrubbed to `[PIN_MASKED]`.
3. **In-VPC KMS Salted Token Vault**: Raw PII is intercepted before prompt assembly, encrypted using AWS KMS Customer Managed Keys (CMK) AES-256 HMAC-SHA256, and mapped to tokenized UUID placeholders (`[TOKEN_ACCT_a1b2c3d4]`). **Zero raw PII ever reaches Amazon Bedrock or external model endpoints.**

### 4.2 Outbound Control Plane (FSA & FIEA Article 38 Compliance - [ADR 0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) & [ADR 0010](file:///home/joe/src/bank-ai-chat/docs/adr/0010-personalized-account-tier-reasoning.md))
To comply with the **Financial Services Agency (FSA)** and **Financial Instruments and Exchange Act (FIEA Article 38)**:

1. **NLI Entailment Grounding Verification ($\ge 0.85$)**: Computes entailment scores between generated LLM responses and retrieved Rakuten FAQ contexts to prevent hallucinated financial statements.
2. **Securities Advice Restriction (FIEA Art. 38)**: Prohibits un-licensed investment solicitation, stock recommendations, or guaranteed return projections.
3. **Personalized Deposit Tier Reasoning ([ADR 0010](file:///home/joe/src/bank-ai-chat/docs/adr/0010-personalized-account-tier-reasoning.md))**: Fuses customer balances with loyalty program rules to perform dynamic savings delta calculations ($\text{Target} - \text{Current Balance} = \text{Delta}$), helping customers upgrade to Happy Program stages (e.g. VIP, Super VIP) safely.
4. **Mandatory Legal Disclaimer Append**: Automatically appends standardized Japanese banking legal disclaimers to every response.

---

## 5. RAG Vector Search & Data Isolation: Amazon OpenSearch Serverless (AOSS) ([ADR 0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md))

### 5.1 OpenSearch Security & Vector Standard
- **Network Isolation**: OpenSearch Serverless collection is configured with **Private VPC Access Policies**, blocking all public internet endpoints.
- **Embedding Standard**: **1,024-dimension vector embeddings** (produced by `amazon.titan-embed-text-v2:0`) with **Cosine Similarity** scoring (`hnsw`).
- **Metadata RBAC Filtering**: Enforces Tier-Based Metadata Access Controls (`REGULAR`, `PREMIUM`, `VIP`, `SUPER_VIP`) to isolate document retrieval contexts per customer authorization level.

---

## 6. Enterprise Cryptography & FISC Audit Logger ([ADR 0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md) & [ADR 0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))

### 6.1 AWS KMS Customer Managed Keys (CMK)
- **Key Spec**: `SYMMETRIC_DEFAULT` (AES-256-GCM).
- **Key Rotation**: Automatic annual CMK key rotation enabled.
- **Scope**: Encrypts S3 audit buckets, OpenSearch index storage, DynamoDB state locks, and PII token vault keys.

### 6.2 FISC Tamper-Evident Audit Stream
- **S3 Object Lock Bucket**: Immutable audit log storage configured with S3 Object Lock in **`COMPLIANCE` WORM mode** for a mandatory 10-year (3,650 days) retention period per banking regulations.
- **Cryptographic Verification**: Every transaction generates a SHA-256 signature calculated over:
  $$\text{Signature} = \text{SHA256}(\text{SessionID} \parallel \text{Timestamp} \parallel \text{SanitizedPrompt} \parallel \text{GuardrailFlags} \parallel \text{TokenUsage})$$
- Asynchronously streamed to AWS CloudWatch Logs and encrypted S3 WORM storage.

---

## 7. Edge Security & Perimeter Defense

### 7.1 AWS WAF Web ACL
- **OWASP Top 10 Managed Rules**: Shields against SQL Injection (SQLi), Cross-Site Scripting (XSS), and Command Injection.
- **FISC Rate Limiting Rule**: Enforces a strict threshold of 1,000 requests per 5 minutes per IP address to mitigate DDoS attempts.
- **IP Reputation Rule**: Automatically blocks known malicious TOR exit nodes and botnets.

### 7.2 Application Load Balancer (ALB)
- **TLS Protocol**: Enforces **TLS 1.3** (`ELBSecurityPolicy-TLS13-1-2-2021-06`).
- **SSL Certificates**: Managed via AWS Certificate Manager (ACM) with automated DNS validation renewal.

---

## 8. Deterministic Infrastructure as Code (IaC) & Remote State ([ADR 0016](file:///home/joe/src/bank-ai-chat/docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md) & [ADR 0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md))

### 8.1 Terraform Remote State Topology
- **State Storage**: Amazon S3 bucket with versioning and AES-256 KMS encryption enabled.
- **State Locking**: Amazon DynamoDB table (`japan-bank-ai-tfstate-lock`) preventing race conditions during concurrent CI/CD pipelines.

### 8.2 Enterprise IAM Least-Privilege Scoping
- **Execution Role**: `BankAiEcsTaskExecutionRole` granted `kms:Decrypt`, `bedrock:InvokeModel`, and `logs:CreateLogStream` strictly bounded by condition keys (`aws:PrincipalOrgID`, `aws:ViaAWSService`).

---

## 9. Observability, Telemetry & SRE Metrics ([ADR 0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md))

### 9.1 CloudWatch Dashboards & Alarms
- **P95 Latency Alarm**: Alerts if response latency exceeds $630\text{ ms}$.
- **Guardrail Block Rate Alarm**: Alerts if Input/Output Guardrail block rate exceeds 5% over a 5-minute window (potential active prompt injection attack).
- **Model Drift & Refusal Tracking**: Tracks entailment score distributions and refusal metrics in real time via AWS X-Ray distributed tracing.

---

## 10. Cost Sizing & Deflection ROI Matrix ([ADR 0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md))

| Sizing Target | Monthly Traffic | AWS Monthly Cost (USD) | AWS Monthly Cost (JPY @ ¥150/$) | Operational Value / ROI |
|---|---|---|---|---|
| **Local WSL Environment** | Unlimited Dev Testing | **$0.00** | **¥0** | Offline developer velocity & zero cloud friction. |
| **AWS 24-Hour Test Session** | ~100 Test Requests | **$3.16** | **¥474** | Instant cloud validation & teardown flexibility. |
| **Full Production (1M Reqs/mo)** | 1,000,000 Inquiries | **$540.40 / mo** | **¥81,060 / 月** | **85%+ Cost Advantage** over legacy models. Deflects 1M human call center inquiries/yr = **¥300,000,000 JPY annual operational savings** for the bank. |

---

## Summary Checklist for Cloud Architect Review

1. **Data Sovereignty**: 100% AWS Tokyo (`ap-northeast-1`) bounded.
2. **Zero PII Exposure**: KMS Salted Token Vault scrubbed prior to LLM invocation.
3. **Network Isolation**: All AWS service traffic routes over PrivateLink Interface Endpoints.
4. **Regulatory Auditability**: 10-Year S3 Object Lock WORM bucket with SHA-256 event signatures.
5. **Compute & SLA**: ECS Fargate container auto-scaling guaranteeing zero cold starts and HTTP SSE token streaming.

