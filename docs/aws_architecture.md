# AWS & Hybrid Architecture Design: Japanese Major Bank AI Portal

## 1. Executive Summary & Topology
This document outlines the hybrid topology (On-Premise Core Banking System + AWS Private Cloud) for the Japanese Major Bank AI Customer Assistant, alongside the standalone AWS POC implementation architecture.

---

## 2. Target Hybrid Architecture Pattern

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      On-Premise Banking Infrastructure                   │
│                                                                         │
│  ┌───────────────────────┐             ┌─────────────────────────────┐  │
│  │ Core Banking Mainframe│             │ Customer Account Database   │  │
│  │ (勘定系システム)        │             │ (顧客情報 DB - PII Vault)    │  │
│  └───────────┬───────────┘             └──────────────┬──────────────┘  │
└──────────────┼────────────────────────────────────────┼─────────────────┘
               │ Dedicated AWS Direct Connect (Encrypted IPsec VPN)
               ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   AWS Tokyo Region (ap-northeast-1)                      │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Private VPC (Security Zone)                                       │  │
│  │                                                                   │  │
│  │   ┌────────────────────┐            ┌─────────────────────────┐   │  │
│  │   │ API Gateway / ALB  ├───────────►│ Bank AI Backend Service │   │  │
│  │   └────────────────────┘            │ (FastAPI / ECS Fargate) │   │  │
│  │                                     └────────────┬────────────┘   │  │
│  │                                                  │                │  │
│  │      ┌───────────────────────────────────────────┼──────────┐     │  │
│  │      ▼                                           ▼          ▼     │  │
│  │ ┌──────────────────────┐  ┌──────────────────┐  ┌──────────────┐ │  │
│  │ │ Input Control Plane  │  │ FAQ Vector RAG   │  │ Audit Logger │ │  │
│  │ │ (PII Scrubbing)      │  │ (OpenSearch/Chroma)│ │ (CloudWatch) │ │  │
│  │ └──────────┬───────────┘  └────────┬─────────┘  └──────┬───────┘ │  │
│  └────────────┼───────────────────────┼───────────────────┼──────────┘  │
│               │                       │                   │             │
│               ▼                       ▼                   ▼             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ AWS Managed AI & Security Services                                │  │
│  │                                                                   │  │
│  │   ┌───────────────────────────┐        ┌───────────────────────┐  │  │
│  │   │ Amazon Bedrock            │        │ AWS KMS (AES-256)     │  │  │
│  │   │ (Amazon Nova Lite)        │        │ Customer Managed Key  │  │  │
│  │   └───────────────────────────┘        └───────────────────────┘  │  │
│  │                                                                   │  │
│  │   ┌───────────────────────────┐        ┌───────────────────────┐  │  │
│  │   │ Amazon S3                 │        │ AWS GuardDuty         │  │  │
│  │   │ (Encrypted Audit Logs)    │        │ Security Hub          │  │  │
│  │   └───────────────────────────┘        └───────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key AWS Components & Roles

### 3.1 Amazon Bedrock (Model: Amazon Nova Lite)
- **Region**: Tokyo (`ap-northeast-1`).
- **Model ID**: `amazon.nova-lite-v1:0`.
- **Purpose**: Fast, cost-efficient, high-quality Japanese language generation.
- **Security**: Data transmitted to Bedrock is processed exclusively in-region and is **never** used for model fine-tuning or saved in model logs outside customer VPC boundaries.

### 3.2 Control Planes & Security Layers
- **Input Guardrail**: Sanitizes account numbers, katakana names, and credentials before constructing prompts.
- **Output Guardrail**: Inspects generated responses, verifies grounding against FAQ context, and enforces mandatory disclaimers.
- **AWS KMS**: Encrypts all data at rest (S3, Vector DB, Audit logs) using Customer Managed Keys (CMK).

### 3.3 Data Storage & RAG
- **S3 Bucket**: Stores Rakuten Bank FAQ JSON documents and immutable audit logs.
- **Vector Index Engine**: Fast local/in-memory cosine vector store backed by TF-IDF & dense embeddings for Rakuten Bank FAQ retrieval.

---

## 4. FISC Compliance Checklist

| FISC Security Standard | AWS Implementation | Status |
|---|---|---|
| Data Sovereignty | Bound strictly to AWS Tokyo (`ap-northeast-1`) | Compliant |
| Data Protection in Transit | TLS 1.3 enforced for all internal & external endpoints | Compliant |
| Data Protection at Rest | KMS Customer Managed Keys (AES-256 encryption) | Compliant |
| Access Control & IAM | Least-privilege IAM roles and VPC endpoints | Compliant |
| Immutable Audit Trail | Logged session payloads and guardrail decisions in S3 | Compliant |

---

## 5. Detailed AWS Architecture & Production Specifications

For the complete sub-system network topologies, VPC IPv4 subnet plans, Amazon OpenSearch Serverless configurations, S3 Object Lock compliance settings, IAM OIDC policies, and Terraform IaC resource definitions, refer to:

- [AWS Detailed Architecture Design Specification](aws_detailed_design_specification.md)
- [ADR 0007: Production AWS Detailed Architecture Design Specification](adr/0007-production-aws-detailed-design-specification.md)

