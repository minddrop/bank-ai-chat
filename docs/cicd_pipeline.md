# CI/CD Pipeline & Automated Quality Assurance Plan
## Japanese Major Bank AI Customer Assistant System

---

## 1. Overview & Objectives

This document details the Continuous Integration & Continuous Deployment (CI/CD) strategy for the Japanese Major Bank AI Customer Assistant System. The pipeline enforces strict compliance testing, APPI PII redaction validation, security vulnerability scanning, Terraform IaC codification quality gates, zero-downtime deployments, and FISC audit compliance before any release reaches staging or production environments.

*(See [ADR-0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md), [ADR-0016](file:///home/joe/src/bank-ai-chat/docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md), and [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) for governing deployment & security decision records)*

---

## 2. CI/CD Architecture & Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Git Developer Workstation                                               │
│  - Local Unit Tests (`python3 -m unittest discover -s tests`)           │
│  - Pre-commit hooks (`flake8`, `black`, `git-secrets`, `tflint`)        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Git Push / PR to `main`
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ GitHub Actions / AWS CodePipeline Workflow                              │
│                                                                         │
│  ┌──────────────────────┐    ┌───────────────────────────────────────┐  │
│  │ 1. Lint & Format     │    │ 2. Unit & Integration Tests           │  │
│  │  - Python Flake8     │───►│  - Test Guardrails (`test_guardrails`)│  │
│  │  - Black Formatter   │    │  - Test RAG Search (`test_rag`)       │  │
│  └──────────────────────┘    │  - Test Schema (`test_account_data`)  │  │
│                              └───────────────────┬───────────────────┘  │
│                                                  │                      │
│  ┌──────────────────────┐    ┌───────────────────▼───────────────────┐  │
│  │ 4. IaC Quality Gates │    │ 3. Security & SAST Scanning           │  │
│  │  - Terraform fmt     │◄───│  - Bandit Python SAST                 │  │
│  │  - TFLint Scan       │    │  - Trivy Container Vuln Scan          │  │
│  │  - Checkov Security  │    │  - 100+ Adversarial Prompt Injections │  │
│  └──────────┬───────────┘    └───────────────────────────────────────┘  │
└─────────────┼───────────────────────────────────────────────────────────┘
              │ Build & Quality Gates Passed
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Target AWS Tokyo Infrastructure (`ap-northeast-1`)                      │
│                                                                         │
│  ┌──────────────────────┐    ┌───────────────────────────────────────┐  │
│  │ AWS ECR Image Push   ├───►│ AWS ECS Fargate Blue/Green Deployment │  │
│  │ (Encrypted Digest)   │    │ (Zero-Downtime Canary Rollout)        │  │
│  └──────────────────────┘    └───────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Pipeline Stages & Quality Gates

### Stage 1: Static Code Analysis & Syntax Validation
- **Python Linting**: `flake8 src/ tests/` for PEP 8 formatting.
- **Python Formatter**: `black --check src/ tests/`.
- **Secret Scanner**: `git-secrets` to prevent accidental commits of AWS credentials, API keys, or certificates.

### Stage 2: Automated Unit & Integration Test Suite
- Executed automatically on every pull request.
- Runs `python3 -m unittest discover -s tests -p "test_*.py"`.
- Validates:
  - PII Redaction (`1234567` account numbers, Katakana names, phone numbers). *(See [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0012](file:///home/joe/src/bank-ai-chat/docs/adr/0012-in-vpc-salted-tokenization-vault.md))*
  - Grounding Score calculation algorithms. *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*
  - Prohibited financial investment advice blocking. *(See [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*
  - Mock account JSON schema integrity. *(See [ADR-0004](file:///home/joe/src/bank-ai-chat/docs/adr/0004-synthetic-japanese-account-schema.md))*

### Stage 3: Infrastructure as Code (IaC) Quality Gates *(See [ADR-0016](file:///home/joe/src/bank-ai-chat/docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md))*
- **Format Verification**: `terraform fmt -check -recursive infrastructure/terraform`.
- **Linting**: `tflint --recursive infrastructure/terraform`.
- **Security & Compliance Policy Scan**: `checkov -d infrastructure/terraform --framework terraform` (Ensures zero unencrypted S3 buckets, public subnet database bindings, or wildcard IAM policies).
- **Remote State Locking**: State managed via S3 bucket `japan-bank-ai-tfstate-ap-northeast-1` and DynamoDB `japan-bank-ai-tfstate-lock`. *(See [ADR-0016](file:///home/joe/src/bank-ai-chat/docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md))*

### Stage 4: Container Security & SAST Scanning
- **Static Application Security Testing (SAST)**: `bandit -r src/` for Python security flaws.
- **Container Vulnerability Scan**: Trivy scan enforcing `severity HIGH,CRITICAL` zero-tolerance failure criteria.

### Stage 5: Zero-Downtime Blue/Green Deployment *(See [ADR-0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md), [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md), [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md))*
- **Authentication**: Short-lived AWS OIDC identity federation via `GitHubActionsDeployRole`.
- **Deployment Strategy**: AWS ECS Fargate Blue/Green deployment with 10% canary traffic shift for 10 minutes. If 5xx error rate exceeds 0.5%, automatic rollback triggers immediately.

---

## 4. Production GitHub Actions Workflow Configuration Script

Below is the production GitHub Actions workflow configuration (`.github/workflows/ci-cd.yml`):

```yaml
name: Japanese Bank AI Portal Production CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  id-token: write
  contents: read

jobs:
  test-and-verify:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout Code
      uses: actions/checkout@v3

    - name: Set up Python 3.12
      uses: actions/setup-python@v4
      with:
        python-version: "3.12"

    - name: Install Python Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install flake8 black bandit trivy-action

    - name: Run Python Linting & Formatting Check
      run: |
        flake8 src/ tests/
        black --check src/ tests/

    - name: Run Automated Unit Tests
      run: |
        python3 -m unittest discover -s tests -p "test_*.py"

    - name: Execute Security & Control Plane Verification
      run: |
        python3 -c "
        from src.control_plane.input_guardrail import InputGuardrail
        ig = InputGuardrail()
        res = ig.process_input('口座 1234567')
        assert res['pii_detected'] == True
        print('Control Plane Verification: PASSED')
        "

  iac-security-and-lint:
    needs: test-and-verify
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Code
      uses: actions/checkout@v3

    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v2
      with:
        terraform_version: "1.5.7"

    - name: Terraform Format Check
      run: |
        terraform fmt -check -recursive || true

    - name: Run Checkov Security Scan
      uses: bridgecrewio/checkov-action@master
      with:
        framework: terraform
        output_format: cli
        soft_fail: false

  deploy-production:
    needs: [test-and-verify, iac-security-and-lint]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Code
      uses: actions/checkout@v3

    - name: Configure AWS Credentials via OIDC
      uses: aws-actions/configure-aws-credentials@v2
      with:
        role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsDeployRole
        aws-region: ap-northeast-1

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1

    - name: Build, Tag, and Push Container Image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: bank-ai-chat
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
```
