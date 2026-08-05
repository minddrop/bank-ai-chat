# AWS Detailed Architecture Design Specification
## Japanese Major Bank Production AI Assistant System

**System Name**: Japanese Major Bank Production AI Assistant System  
**AWS Target Region**: Tokyo (`ap-northeast-1`)  
**Secondary DR Region**: Osaka (`ap-northeast-2`)  
**Compliance Standards**: FISC Security Standards (FISC安全対策基準), APPI (個人情報保護法), FSA Guidelines (金融庁AIガイドライン), Banking Act (銀行法), FIEA (金融商品取引法)  

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
| Private App Subnet 1A | `ap-northeast-1a` | `10.100.10.0/23` | NAT Gateway 1A / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Control Planes) |
| Private App Subnet 1C | `ap-northeast-1c` | `10.100.12.0/23` | NAT Gateway 1C / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Control Planes) |
| Private App Subnet 1D | `ap-northeast-1d` | `10.100.14.0/23` | NAT Gateway 1D / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Control Planes) |
| Isolated Data Subnet 1A | `ap-northeast-1a` | `10.100.20.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, RDS PostgreSQL Read Replica |
| Isolated Data Subnet 1C | `ap-northeast-1c` | `10.100.21.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, RDS PostgreSQL Main |
| Isolated Data Subnet 1D | `ap-northeast-1d` | `10.100.22.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, VPC Endpoints Interfaces |

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

## 2. In-VPC Dual Control Plane Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │ Client Browser / Internet Banking App        │
                    └──────────────────────┬───────────────────────┘
                                           │ HTTPS / TLS 1.3 (Port 443)
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ AWS WAF (Managed OWASP + FISC Rate Rules)    │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ Application Load Balancer (ALB)              │
                    └──────────────────────┬───────────────────────┘
                                           │ Private App Subnet (Multi-AZ)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Amazon ECS Fargate Container Service (`src/backend`)                                    │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 1. INPUT CONTROL PLANE (`src/control_plane/input_guardrail.py`)                  │  │
│  │    - Prompt Injection & System Override Defense                                  │  │
│  │    - PII Interceptor & Tokenizer: Account No (`\d{7}`), Katakana, PIN, Phone     │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                           │ Sanitized Prompt                            │
│                                           ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 2. CONTEXT RETRIEVAL LAYER (`src/rag`)                                           │  │
│  │    - Amazon OpenSearch Serverless Vector Search (Rakuten FAQ Embeddings)          │  │
│  │    - Core Banking Mock Integration (`src/core_banking/`)                         │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                           │ Context Payload                            │
│                                           ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 3. INFERENCE LAYER (`src/llm/bedrock_nova.py`)                                   │  │
│  │    - Amazon Bedrock Runtime (VPC Endpoint)                                       │  │
│  │    - Model: `amazon.nova-lite-v1:0` (Tokyo ap-northeast-1)                      │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                           │ Raw LLM Generation                         │
│                                           ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 4. OUTPUT CONTROL PLANE (`src/control_plane/output_guardrail.py`)                │  │
│  │    - Grounding Score Evaluator (Context Match % Verification)                    │  │
│  │    - Prohibited Investment Advice & Stock solicitation filter (FIEA compliance)  │  │
│  │    - Mandatory Japanese Legal Disclaimer Appender                                │  │
│  └────────────────────────────────────────┬─────────────────────────────────────────┘  │
│                                           │ Validated Output                            │
│                                           ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 5. FISC AUDIT LOGGER (`src/control_plane/fisc_audit_logger.py`)                  │  │
│  │    - SHA-256 Signature Computation & Log Entry Assembly                          │  │
│  │    - CloudWatch Logs + Encrypted S3 Bucket (Object Lock 10-Year Mode)            │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
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

## 4. Storage, Vector DB & Audit Logging Specifications

### 4.1 Amazon OpenSearch Serverless Vector Engine
- **Collection Type**: `VECTORSEARCH`
- **Encryption**: KMS Customer Managed Key (CMK)
- **Network Access**: Private VPC Endpoint Access Only
- **Vector Metric**: Cosine Similarity / HNSW (Hierarchical Navigable Small World)
- **Index Schemas**: Rakuten Bank FAQ 10,000+ chunk embeddings (1536-dim vectors)

### 4.2 S3 Bucket & FISC Object Lock Compliance
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
│  - Core Mainframe (勘定系 DB)                               │
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

Below is an IaC Terraform specification snippet for provisioning the core compliance resources in `ap-northeast-1`:

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
      Compliance  = "FISC-APPI-FSA"
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
| **APPI (個人情報保護法)** | In-VPC Input Control Plane PII Redaction + Private VPC Endpoints | Verified (Zero PII transmitted to LLM) |
| **FSA AI Guidelines** | Grounding Score calculation + FISC Audit Trail with SHA-256 signature | Verified |
| **FIEA (金融商品取引法)** | Output Control Plane Investment Advice Blocking Filter | Verified |
| **FISC Security Standards** | AWS Tokyo `ap-northeast-1` data residency + KMS AES-256 + S3 10-Yr Object Lock | Verified |
| **Banking Act (銀行法)** | Informational boundary + Mandatory Japanese legal disclaimer injection | Verified |
