# AWS Detailed Architecture Design Specification
## Japanese Major Bank Production AI Assistant System

**System Name**: Japanese Major Bank Production AI Assistant System  
**AWS Target Region**: Tokyo (`ap-northeast-1`)  
**Secondary DR Region**: Osaka (`ap-northeast-2`)  
**Compliance Standards**: FISC Security Standards (FISC安全対策基準), APPI (個人情報保護法), FSA Guidelines (金融庁AIガイドライン), Banking Act (銀行法), FIEA (金融商品取引法), PCI-DSS 4.0, GLBA Safeguards Rule (16 CFR Part 314), CFPB AI Guidance, SR 11-7, ISO 42001/AIUC-1, NYDFS Part 500  

---

## 1. Network Topology & VPC Architecture

### 1.1 VPC IPv4 Address Plan
- **Primary VPC (Tokyo `ap-northeast-1`)**: CIDR Block `10.100.0.0/16`
- **Availability Zones**: Multi-AZ deployment across `ap-northeast-1a`, `ap-northeast-1c`, `ap-northeast-1d`

| Subnet Tier | Zone | CIDR Block | Route Target | Purpose |
|---|---|---|---|---|
| Public Subnet 1A | `ap-northeast-1a` | `10.100.1.0/24` | Internet Gateway (IGW) | Application Load Balancer (ALB), NAT Gateway 1A |
| Public Subnet 1C | `ap-northeast-1c` | `10.100.2.0/24` | Internet Gateway (IGW) | Application Load Balancer (ALB), NAT Gateway 1C |
| Public Subnet 1D | `ap-northeast-1d` | `10.100.3.0/24` | Internet Gateway (IGW) | Application Load Balancer (ALB), NAT Gateway 1D |
| Private App Subnet 1A | `ap-northeast-1a` | `10.100.10.0/23` | NAT Gateway 1A / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Dual Control Planes) |
| Private App Subnet 1C | `ap-northeast-1c` | `10.100.12.0/23` | NAT Gateway 1C / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Dual Control Planes) |
| Private App Subnet 1D | `ap-northeast-1d` | `10.100.14.0/23` | NAT Gateway 1D / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Dual Control Planes) |
| Isolated Data Subnet 1A | `ap-northeast-1a` | `10.100.20.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, Salted Token Vault, KMS Endpoint |
| Isolated Data Subnet 1C | `ap-northeast-1c` | `10.100.21.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, Salted Token Vault, Bedrock Endpoint |
| Isolated Data Subnet 1D | `ap-northeast-1d` | `10.100.22.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, Salted Token Vault, S3 Gateway Endpoint |

### 1.2 AWS PrivateLink & Interface VPC Endpoints
To satisfy FISC data isolation mandates, network traffic to AWS services MUST NOT cross the public Internet. The following Interface/Gateway endpoints are deployed inside the Isolated Data Subnets:

- `com.amazonaws.ap-northeast-1.bedrock-runtime`: Amazon Bedrock (Nova Lite Model `amazon.nova-lite-v1:0`)
- `com.amazonaws.ap-northeast-1.aoss`: Amazon OpenSearch Serverless Vector Store Engine
- `com.amazonaws.ap-northeast-1.kms`: AWS Key Management Service (Customer Managed Keys)
- `com.amazonaws.ap-northeast-1.s3` (Gateway Endpoint): Encryption Audit Bucket & FAQ JSON storage
- `com.amazonaws.ap-northeast-1.ecr.api` & `.dkr`: Amazon Elastic Container Registry
- `com.amazonaws.ap-northeast-1.logs`: Amazon CloudWatch Logs for audit trail streaming
- `com.amazonaws.ap-northeast-1.secretsmanager`: Secrets Manager for database & API tokens

---

## 2. In-VPC Dual Control Plane Architecture & Microservice Pipeline

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │ Client Browser / Internet Banking Web Portal / Mobile App   │
                    └──────────────────────────────┬──────────────────────────────┘
                                                   │ HTTPS / TLS 1.3 (Port 443)
                                                   ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │ AWS WAF (Managed OWASP + FISC Rate Rules + Rate Limiters)   │
                    └──────────────────────────────┬──────────────────────────────┘
                                                   │
                                                   ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │ Application Load Balancer (ALB) Multi-AZ                     │
                    └──────────────────────────────┬──────────────────────────────┘
                                                   │ Private App Subnet (Multi-AZ)
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Amazon ECS Fargate Container Service (`src/backend`)                                                     │
│                                                                                                         │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 1. INPUT CONTROL PLANE & INLINE DLP (`src/control_plane/input_guardrail.py`) [P95 <= 45ms]         │  │
│  │    - Unicode NFC Normalization & Zero-Width Space (`U+200B`) / Cipher Stripper                     │  │
│  │    - Direct & Indirect Prompt Injection Classifier (OWASP LLM01/02)                              │  │
│  │    - Multi-Pattern PII Redactor & Salted Token Vault (`[TOKEN_ACCT_a1b2c3d4]`) (APPI / PCI-DSS 4.0)│  │
│  │    - Payload Bounds (1,000 chars / 500 tokens) & Executable Code / SSRF Sanitizer                 │  │
│  └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘  │
│                                                    │ Sanitized Prompt Payload                           │
│                                                    ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 2. CONTEXT RETRIEVAL LAYER & RAG RBAC (`src/rag`) [P95 <= 85ms]                                   │  │
│  │    - OpenSearch Serverless Vector Search with Tier-Based RBAC Metadata Filter                      │  │
│  │    - Core Banking Integration (Read-Only OAuth 2.0 mTLS Mock Interface)                           │  │
│  └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘  │
│                                                    │ Context Payload                                    │
│                                                    ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 3. INFERENCE LAYER (`src/llm/bedrock_nova.py`) [P95 <= 450ms TTFT]                                │  │
│  │    - Amazon Bedrock Runtime via Private VPC Interface Endpoint                                   │  │
│  │    - Model: `amazon.nova-lite-v1:0` (Tokyo `ap-northeast-1`)                                      │  │
│  └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘  │
│                                                    │ Raw LLM Generated Output                           │
│                                                    ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 4. OUTPUT CONTROL PLANE & POST-DLP (`src/control_plane/output_guardrail.py`) [P95 <= 50ms]        │  │
│  │    - Natural Language Inference (NLI) Entailment Grounding Verification (Entailment Score >= 0.85) │  │
│  │    - Outbound PII Reflection Scanner & Financial Numeric Value Integrity Check                    │  │
│  │    - FIEA Article 38 Prohibited Financial Solicitation Filter & Legal Disclaimer Appender         │  │
│  └─────────────────────────────────────────────────┬─────────────────────────────────────────────────┘  │
│                                                    │ Validated Response + Metadata                      │
│                                                    ▼                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 5. FISC AUDIT LOGGER & TELEMETRY (`src/control_plane/fisc_audit_logger.py`) [P95 <= 12ms Async]   │  │
│  │    - Cryptographic SHA-256 Signature Assembly & Security Event CloudWatch Metric Publisher       │  │
│  │    - Immutable Stream to S3 Object Lock (10-Year WORM Compliance Mode)                           │  │
│  └───────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. ECS Fargate Compute & Scaling Specifications

### 3.1 Task Definition Specification
- **Task CPU**: `1024` (1 vCPU)
- **Task Memory**: `2048` (2 GB RAM)
- **Launch Type**: `FARGATE`
- **Network Mode**: `awsvpc`
- **Operating System**: Linux (`ARM64` / AWS Graviton2 for high performance & 20% cost efficiency)

### 3.2 Auto-scaling Policy
- **Target Tracking Scaling**:
  - `ECSServiceAverageCPUUtilization`: Target value `70%`
  - `ECSServiceAverageMemoryUtilization`: Target value `75%`
  - `ALBRequestCountPerTarget`: Target `1,000` requests per minute
- **Capacity Limits**:
  - Minimum Tasks: `3` (1 task per Availability Zone)
  - Maximum Tasks: `30` (Handles peak dividend payout days and campaign surges)

---

## 4. Storage, Token Vault, Vector DB & Audit Logging Specifications

### 4.1 In-VPC KMS Salted Token Vault
- **Encryption Engine**: AWS KMS Customer Managed Key (`aws:kms`) with AES-256 GCM encryption.
- **Vault Retention**: Ephemeral in-memory database bound strictly to request lifecycle.
- **Token Format**: Cryptographically salted UUID strings (`[TOKEN_ACCT_a1b2c3d4]`).
- **Session Zeroization**: Conversation buffers zeroized within $< 10\text{ ms}$ upon session termination or profile switch per GLBA and NYDFS rules.

### 4.2 Amazon OpenSearch Serverless Vector Engine
- **Collection Type**: `VECTORSEARCH`
- **Encryption**: KMS Customer Managed Key (CMK)
- **Network Access**: Private VPC Endpoint Access Only
- **Vector Metric**: Cosine Similarity / HNSW (Hierarchical Navigable Small World)
- **Index Schemas**: Rakuten Bank FAQ 10,000+ chunk embeddings (1,536-dim vectors)
- **RBAC Filtering**: Metadata pre-filtering on customer authorization tiers (`REGULAR`, `PREMIUM`, `VIP`, `SUPER_VIP`).

### 4.3 S3 Bucket & FISC Object Lock Compliance
- **Audit Bucket Name**: `japan-bank-ai-audit-log-ap-northeast-1`
- **Object Lock Configuration**:
  - Mode: `COMPLIANCE` (Cannot be deleted or modified by any user including AWS Root Account)
  - Retention Period: `3650 days` (10 Years per Banking Act & FISC Standards)
- **Encryption**: `aws:kms` with CMK ARN `arn:aws:kms:ap-northeast-1:123456789012:key/bank-ai-audit-key`
- **Lifecycle Policy**: Glacier Flexible Retrieval after 90 days; Glacier Deep Archive after 365 days.

---

## 5. Security, IAM & Identity Specifications

### 5.1 IAM Roles & OIDC GitHub Actions Integration
- **ECS Task Execution Role (`BankAiEcsTaskExecutionRole`)**:
  - Attached Policies: `AmazonECSTaskExecutionRolePolicy`, `CustomKmsDecryptPolicy`, `CustomSecretsManagerReadPolicy`
- **ECS Task Role (`BankAiEcsTaskRole`)**:
  - Privileges restricted to Bedrock `bedrock:InvokeModel` on `amazon.nova-lite-v1:0`, OpenSearch AOSS search access, and CloudWatch Log PutEvents.
- **GitHub Actions OIDC Role (`GitHubActionsDeployRole`)**:
  - Trust policy bound strictly to repository `minddrop/bank-ai-chat` and branch `refs/heads/main`.
  - Permissions restricted to ECR image pushing and ECS task definition updating in `ap-northeast-1`.

---

## 6. Hybrid Cloud Architecture (Direct Connect & TGW)

```
┌─────────────────────────────────────────────────────────────┐
│ On-Premise Core Banking Data Center (東京勘定系センター)      │
│  - Core Mainframe (勘定系 DB - Read Only)                   │
│  - PII Vault & Customer Master DB                           │
│  - Direct Connect Customer Gateway (CGW)                    │
└──────────────┬──────────────────────────────┬───────────────┘
               │ Dedicated 10 Gbps DX Link    │ Backup IPsec VPN
               ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS Direct Connect Location (Equinix TY3 / TY11 Tokyo)       │
└──────────────┬──────────────────────────────┬───────────────┘
               │ Direct Connect Gateway (DXGW)│
               ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│ AWS Transit Gateway (TGW) (ap-northeast-1)                  │
│  - Route Table: Isolation & Inspection Routing              │
└──────────────┬──────────────────────────────────────────────┘
               │ TGW Attachment
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Bank AI System VPC (10.100.0.0/16)                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Infrastructure as Code (Terraform IaC Example Snippet)

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-northeast-1"
  default_tags {
    tags = {
      Environment = "Production"
      Project     = "JapaneseBankAiAssistant"
      Compliance  = "FISC-APPI-FSA-PCI-GLBA-NYDFS"
    }
  }
}

# 1. FISC Encrypted Audit S3 Bucket with Object Lock
resource "aws_s3_bucket" "audit_log_bucket" {
  bucket              = "japan-bank-ai-audit-log-ap-northeast-1"
  object_lock_enabled = true
}

resource "aws_s3_bucket_object_lock_configuration" "audit_lock" {
  bucket = aws_s3_bucket.audit_log_bucket.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 3650
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_crypto" {
  bucket = aws_s3_bucket.audit_log_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.bank_ai_cmk.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# 2. AWS KMS Customer Managed Key
resource "aws_kms_key" "bank_ai_cmk" {
  description             = "Japanese Major Bank AI Control Plane CMK Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

# 3. Amazon Bedrock VPC Interface Endpoint
resource "aws_vpc_endpoint" "bedrock_runtime" {
  vpc_id              = "vpc-0123456789abcdef0"
  service_name        = "com.amazonaws.ap-northeast-1.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = ["subnet-0a1b2c3d4e5f6g7h8", "subnet-0i9j8h7g6f5e4d3c2"]
  security_group_ids  = ["sg-0123456789abcdef0"]
}
```

---

## 8. Summary Compliance Matrix

| Regulation / Standard | AWS Implementation Mechanism | Verification Status |
|---|---|---|
| **APPI (個人情報保護法)** | In-VPC Input DLP Multi-Pattern Masking + KMS Salted Token Vault | Verified (Zero PII transmitted to LLM) |
| **FSA AI Guidelines** | NLI Entailment Grounding ($\ge 0.85$) + SHA-256 FISC Audit Trail | Verified |
| **FIEA (金融商品取引法)** | Output Control Plane Investment Solicitation Filter (Art 38) | Verified |
| **FISC Security Standards** | AWS Tokyo `ap-northeast-1` residency + KMS AES-256 + 10-Yr S3 WORM Lock | Verified |
| **Banking Act (銀行法)** | Informational boundary + Mandatory Japanese legal disclaimer injection | Verified |
| **PCI-DSS 4.0** | 16-digit PAN Masking (Req 3.3/3.4) + WAF OWASP Application Shield (Req 6.4.3) | Verified |
| **GLBA Safeguards Rule** | KMS CMK NPI Encryption (§ 314.4) + Zero-Trust Memory Isolation | Verified |
| **CFPB AI Chatbot Guidance** | Grounding Entailment prevents financial hallucination; Human Escalation UI | Verified |
| **SR 11-7 Model Risk** | Automated daily drift tracking, refusal rate analytics, latency distribution | Verified |
| **ISO 42001 / AIUC-1** | Direct/Indirect Prompt Injection Classifier + Unicode NFC Normalization | Verified |
| **NYDFS Part 500** | SHA-256 Audit Trail (500.06) + Step-Up MFA Boundary (500.12) | Verified |
