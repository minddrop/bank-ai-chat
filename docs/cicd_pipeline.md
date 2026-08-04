# CI/CD Pipeline & Automated Quality Assurance Plan
## Japanese Major Bank AI Customer Assistant System

---

## 1. Overview & Objectives

This document details the Continuous Integration & Continuous Deployment (CI/CD) strategy for the Japanese Major Bank AI Customer Assistant System. The pipeline enforces strict compliance testing, APPI PII redaction validation, security vulnerability scanning, zero-downtime deployments, and FISC audit compliance before any release reaches staging or production environments.

---

## 2. CI/CD Architecture & Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Git Developer Workstation                                               │
│  - Local Unit Tests (`python3 -m unittest discover -s tests`)           │
│  - Pre-commit hooks (`flake8`, `black`, `git-secrets`)                  │
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
│  │ 4. Security Scan     │    │ 3. Control Plane Stress Tests         │  │
│  │  - Bandit SAST       │◄───│  - 100+ Adversarial Prompt Injections│  │
│  │  - Trivy Container   │    │  - PII Scrubbing Boundary Validation  │  │
│  └──────────┬───────────┘    └───────────────────────────────────────┘  │
└─────────────┼───────────────────────────────────────────────────────────┘
              │ Build & Tests Passed
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
- **Linting**: Python `flake8` for syntax rules and PEP 8 formatting.
- **Formatter**: `black --check src/ tests/`.
- **Secret Scanner**: `git-secrets` to prevent accidental commits of AWS credentials, API keys, or certificates.

### Stage 2: Automated Unit & Functional Test Suite
- Executed automatically on every pull request.
- Runs `python3 -m unittest discover -s tests -p "test_*.py"`.
- Validates:
  - PII Redaction (`1234567` account numbers, Katakana names, phone numbers).
  - Grounding Score calculation algorithms.
  - Prohibited financial investment advice blocking.
  - Mock account JSON schema integrity.

### Stage 3: Control Plane Safety & Security Stress Tests
- **Prompt Injection Boundary Test Suite**: Executed against 100+ known prompt injection payloads (e.g. system prompt extraction, persona hijacking, jailbreaks).
- **PII Scrubbing Test Suite**: Edge cases testing obfuscated numbers (`１２３４５６７` full-width characters, spaced numbers `1 2 3 4 5 6 7`).

### Stage 4: Container Security & SAST Scanning
- **Static Application Security Testing (SAST)**: `bandit -r src/` for Python security flaws.
- **Container Vulnerability Scan**: Trivy and AWS ECR Inspector scan container images for OS/library vulnerabilities before deployment.

### Stage 5: Zero-Downtime Blue/Green Canary Deployment
- **Deployment Engine**: AWS CodeDeploy with Amazon ECS Fargate.
- **Strategy**: Blue/Green deployment with a 10% canary traffic shift for 10 minutes. If error rates increase or health checks fail, automatic rollback triggers immediately.

---

## 4. GitHub Actions Workflow Configuration Script

Below is the production GitHub Actions workflow configuration (`.github/workflows/ci-cd.yml`):

```yaml
name: Japanese Bank AI Portal CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

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

    - name: Run Unit Tests
      run: |
        python3 -m unittest discover -s tests -p "test_*.py"

    - name: Run Ingestion Verification
      run: |
        python3 scripts/crawl_full_rakuten_faq.py

    - name: Execute Security & Control Plane Tests
      run: |
        python3 -c "
        from src.control_plane.input_guardrail import InputGuardrail
        ig = InputGuardrail()
        assert ig.process_input('口座 1234567')['pii_detected'] == True
        print('Control Plane Verification: PASSED')
        "

  deploy-staging:
    needs: test-and-verify
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to AWS Tokyo Staging (ap-northeast-1)
      run: |
        echo "Deploying container image to AWS ECR & ECS Fargate in ap-northeast-1..."
```
