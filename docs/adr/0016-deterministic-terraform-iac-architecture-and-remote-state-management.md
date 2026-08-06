# ADR 0016: Deterministic Terraform IaC Architecture & Remote State Storage

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Infrastructure Architect, Lead DevOps Engineer, Platform Security Lead

---

## Context & Problem Statement

To achieve zero manual fallback and deterministic deployment of the Japanese Major Bank AI Assistant across AWS Tokyo (`ap-northeast-1`) and secondary DR region Osaka (`ap-northeast-2`), infrastructure management must be fully codified. Legacy deployment descriptions lacked explicit Infrastructure as Code (IaC) modular layout rules, remote state storage definitions, state locking controls, and automated compliance scanning gates.

We must formally specify the IaC framework, remote state backend architecture, directory conventions, and quality gates for automated infrastructure provisioning.

---

## Decision Drivers

1. **Zero Manual Infrastructure Provisioning**: Every AWS resource (VPC, Subnets, ECS, ALB, KMS, S3, OpenSearch, WAF, IAM) must be defined 100% in declarative IaC code.
2. **State Concurrency & Encryption**: Prevent race conditions during concurrent CI/CD pipeline runs and protect sensitive state data containing resource IDs and network mappings.
3. **Automated Security & Drift Detection**: Enforce static IaC vulnerability scanning (`checkov`, `tflint`) before infrastructure state mutation occurs.

---

## Considered Options

1. **Terraform 1.5+ with S3 Remote State, DynamoDB Lock Table, & Checkov CI Gates (Chosen Option)**:
   - Use Terraform 1.5+ with modular HCL structure (`modules/vpc`, `modules/ecs`, `modules/kms`, `modules/security`).
   - Store remote state in an encrypted S3 bucket (`bank-ai-tfstate-ap-northeast-1`) with S3 Object Lock and DynamoDB (`bank-ai-tflock`) state locking.
   - Enforce static analysis quality gates (`terraform fmt`, `tflint`, `checkov`) in the GitHub Actions pipeline.
2. **AWS CloudFormation / CDK**:
   - Native AWS IaC stack templates.
   - *Drawback*: Higher verbosity for complex VPC/AOSS custom policies, slower state diff feedback loops, and limited multi-cloud/hybrid ecosystem tooling compared to Terraform.

---

## Decision Outcome

Chosen Option: **Option 1 (Terraform 1.5+ with S3 Remote State, DynamoDB Lock Table, & Checkov CI Gates)**.

### IaC State & Directory Structure Specifications:

- **Terraform Version**: `>= 1.5.0`
- **AWS Provider**: `hashicorp/aws ~> 5.0`
- **Remote Backend Configuration**:
  ```hcl
  terraform {
    backend "s3" {
      bucket         = "bank-ai-tfstate-ap-northeast-1"
      key            = "prod/terraform.tfstate"
      region         = "ap-northeast-1"
      encrypt        = true
      kms_key_id     = "alias/bank-ai-tfstate-key"
      dynamodb_table = "bank-ai-tflock"
    }
  }
  ```
- **Directory Layout**:
  ```
  infrastructure/terraform/
  ├── main.tf
  ├── variables.tf
  ├── outputs.tf
  ├── terraform.tfvars
  └── modules/
      ├── vpc/
      ├── ecs_fargate/
      ├── kms/
      ├── opensearch/
      ├── s3_audit/
      └── security_groups/
  ```
- **CI/CD Quality Gates**:
  - `terraform fmt -check` (Format compliance)
  - `tflint --recursive` (Syntax & best-practice validation)
  - `checkov -d . --framework terraform` (Security & FISC policy scan)

---

## Consequences

### Positive:
- **Reproducible & Deterministic Infrastructure**: Complete environment rebuilds can be executed in $< 15$ minutes without manual console actions.
- **Concurrent Execution Safety**: DynamoDB state locking prevents corrupted state files during simultaneous pipeline triggers.
- **Proactive Compliance**: Checkov blocks non-compliant resources (e.g. unencrypted S3, public subnets missing WAF) prior to `terraform apply`.

### Negative / Risks:
- **State File Access Protection Required**: S3 state bucket must enforce strict IAM policies to prevent unauthorized inspection.
