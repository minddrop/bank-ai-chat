# 7. Production AWS Detailed Architecture Design Specification

* **Status**: Accepted
* **Date**: 2026-08-05
* **Context**: Architectural Decision Record for Japanese Major Bank Production AI Assistant System

---

## Context & Problem Statement

The AI Assistant System must operate in production under strict regulatory constraints enforced by Japanese financial law (APPI, FSA Guidelines, FISC Security Standards, Banking Act, FIEA). A complete detailed design specification for AWS Tokyo (`ap-northeast-1`) infrastructure, network segmentation, container compute, vector database, auditing, and continuous deployment is required.

---

## Decision Drivers

1. **Strict FISC Compliance & Data Sovereignty**: All data storage, Bedrock Nova Lite LLM inference, and audit logging must remain strictly within AWS Tokyo (`ap-northeast-1`) inside private subnets using AWS PrivateLink VPC Endpoints.
2. **In-VPC Dual Control Planes**: PII interception and prompt injection mitigation must occur prior to model inference, while grounding score calculation, legal disclaimers, and prohibited financial advice filters must execute before returning responses.
3. **FISC 10-Year Audit Retention**: Audit logs require cryptographic SHA-256 signatures and S3 Object Lock in COMPLIANCE mode for 10 years with KMS CMK AES-256 encryption.
4. **Automated Zero-Downtime Deployment**: Continuous Deployment pipeline using GitHub Actions with AWS OIDC authentication and ECS Fargate Blue/Green rollouts.

---

## Decision Outcome

Adopt the complete **AWS Detailed Architecture Design Specification** detailed in [Infrastructure & IaC Requirements](../requirements/07_operations_and_infra/17_infrastructure_iac_requirements.md).

### Architecture Highlights:
- **VPC Address Space**: `10.100.0.0/16` across 3 Availability Zones (`ap-northeast-1a`, `1c`, `1d`).
- **3-Tier Subnet Topology**: Public (ALB, NAT Gateways), Private App (ECS Fargate tasks), Isolated Data (OpenSearch Serverless, RDS, PrivateLink VPC Endpoints).
- **AWS Bedrock Endpoint**: `com.amazonaws.ap-northeast-1.bedrock-runtime` for model `amazon.nova-lite-v1:0`.
- **Vector Search Engine**: Amazon OpenSearch Serverless with KMS CMK encryption.
- **Continuous Deployment**: [GitHub Actions CD workflow](../../.github/workflows/cd.yml) using AWS OIDC role assumption, ECR image building, Trivy security scanning, and ECS Fargate deployment (configured, not executed).

---

## Consequences

- **Positive**: Complete compliance alignment with FISC, APPI, FSA, and Banking Act standards; zero internet exposure for sensitive AI control plane traffic; automated, repeatable IaC and CD pipeline setup.
- **Negative**: Requires maintaining VPC endpoints for multiple AWS services, increasing base VPC endpoint hourly cost (~$0.01/hr per endpoint per AZ), which is fully justified for production banking infrastructure.
