# Japanese Major Bank AI Customer Assistant (AWS Production Architecture)

[![Language: English](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![Language: 日本語](https://img.shields.io/badge/Language-日本語-red.svg)](README_JA.md)

> **Language Switch**: [English](README.md) | [日本語 (Japanese)](README_JA.md)

An enterprise-grade, 24/7/365 digital banking assistant deployed on AWS Tokyo (`ap-northeast-1`) designed for retail banking customers across Japan. Powered by Amazon Bedrock (Amazon Nova Lite `amazon.nova-lite-v1:0`), Amazon OpenSearch Service RAG, and an In-VPC Dual Control Plane architecture.

---

## 🌟 Key Features

1. **Polite Japanese Banking Persona (敬語・丁寧語)**
   - Operates strictly using natural, courteous Japanese banking Keigo (丁寧語・敬語) to ensure trustworthy customer service.

2. **In-VPC Dual Control Planes (Input & Output Guardrails)**
   - **Input Guardrail**: Automatic redaction of Personally Identifiable Information (PII) like 7-digit account numbers, customer names, branch codes, PINs, and phone numbers before prompt assembly (APPI / 個人情報保護法 compliance). Protection against prompt injection attacks.
   - **Output Guardrail**: Grounding score validation against retrieved context, strict prohibition of specific investment/stock advice (FSA & FIEA compliance), and automated inclusion of legal disclaimers.

3. **RAG Knowledge Base & Core Banking Integration**
   - Direct integration with real Japanese banking FAQ knowledge bases (Rakuten Bank FAQ database).
   - Core banking synthetic account lookup (Ordinary Deposits / 普通預金, Fixed Term / 定期預金, Foreign Currency / 外貨預金, transaction histories).

4. **FISC Security & Audit Compliance**
   - Cryptographic SHA-256 signed audit logging stored in AWS Tokyo (`ap-northeast-1`) with S3 Object Lock and AWS KMS AES-256 encryption.

---

## 📁 Repository Structure

```
bank-ai-chat/
├── GEMINI.md                         # Project governance, architectural rules, & guidelines
├── README.md                         # English README (Primary)
├── README_JA.md                      # Japanese README (日本語)
├── data/                             # Production synthetic bank accounts & Rakuten FAQ datasets
├── docs/                             # AWS Architecture, Detailed Specification, CI/CD, Costs, & adr/
│   └── adr/                          # Architectural Decision Records
├── scripts/                          # FAQ crawler & database initialization tools
├── src/                              # Backend, Control Plane, Core Banking, Frontend, LLM, RAG
└── tests/                            # Automated unit tests for guardrails, RAG, & schemas
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- (Optional) Ollama or LM Studio for local LLM inference (e.g., `ollama pull qwen2.5:0.5b`)

### Installation
1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 💻 Running the Application Locally

#### Mode A: Local LLM Provider (Recommended for Offline Dev & Zero AWS Cost)
Run the application in local provider mode without AWS credentials. The system connects to a local Ollama server if active, or automatically falls back to the built-in Local Light Development Engine:
```bash
# Set environment variables for Local LLM Provider
export LLM_PROVIDER=local
export LOCAL_LLM_MODEL=qwen2.5:0.5b   # Optional: qwen2.5:0.5b, qwen2.5:1.5b, gemma:2b
export LOCAL_LLM_URL=http://localhost:11434/v1 # Optional: Ollama/LM Studio endpoint

# Launch the FastAPI backend server
python3 src/backend/app.py
```

#### Mode B: AWS Bedrock Provider Mode (Production Preview)
Run against live Amazon Bedrock (`amazon.nova-lite-v1:0`) in AWS Tokyo (`ap-northeast-1`) (requires active AWS IAM credentials):
```bash
export LLM_PROVIDER=bedrock
python3 src/backend/app.py
```

#### Mode C: Standard HTTP Server (Zero External Frameworks)
Alternatively, launch using the native Python standard library HTTP server:
```bash
python3 src/backend/server.py
```

### 🌐 Accessing the Web Interface
Once the server is running, open your web browser and navigate to:
**`http://localhost:8000`**

This loads the interactive Japanese Banking AI Portal UI, featuring:
- Live Chat Assistant with natural Japanese Keigo responses
- Synthetic Customer Context Switcher (`山田 太郎`, `佐藤 花子`)
- In-VPC Control Plane Telemetry Dashboard (Input/Output Guardrail status, Grounding score gauge, and FISC Audit log viewer)

### 🧪 Running Unit & Compliance Tests
Run the automated test suite across control planes, RAG engines, and LLM providers:
```bash
python3 -m unittest discover -s tests
# or verify local LLM setup specifically:
python3 scripts/setup_local_llm.py
```

---

## ⚖️ Regulatory & Security Standards

- **APPI (個人情報保護法)**: Zero PII transmission to external LLM endpoints.
- **FSA AI Guidelines & FIEA (金融商品取引法)**: Automated grounding checks and financial advice restrictions.
- **FISC Security Standards (FISC安全対策基準)**: Tamper-evident audit logging and KMS encryption.
- **Global Financial Standards**: Full traceability against **PCI-DSS 4.0**, **GLBA**, **CFPB AI Guidance**, **SR 11-7**, **ISO 42001/AIUC-1**, and **NYDFS Part 500**. See [Enterprise Security, DLP & Compliance Specification](docs/security_dlp_guardrails_requirements.md) and [ADR 0009](docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md).
- **Compute Architecture & Streaming Governance**: Re-evaluated container compute (AWS ECS Fargate) vs. serverless (AWS Lambda) ensuring un-truncated SSE response streaming, 29-second proxy limit evasion, zero cold starts, and 3-tier VPC FISC compliance. See [ADR 0011](docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) and [ADR 0013](docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md).
- **In-VPC Salted PII Tokenization & Step-Up Auth**: Tokenized PII vaulting under APPI ([ADR 0012](docs/adr/0012-in-vpc-salted-tokenization-vault.md)) and legal boundary enforcement under the Japanese Banking Act ([ADR 0014](docs/adr/0014-zero-trust-step-up-authentication-boundary.md)).
- **Infrastructure Codification & Production Readiness**: OpenSearch Serverless network policies & 1024-dim Titan v2 embedding standards ([ADR 0015](docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md)), deterministic Terraform IaC remote state management ([ADR 0016](docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md)), enterprise IAM least-privilege role scoping ([ADR 0017](docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md)), production CloudWatch observability targets ([ADR 0018](docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md)), and Local LLM Provider & fallback dev environment ([ADR 0019](docs/adr/0019-local-llm-provider-and-fallback-architecture.md)). See detailed [Enterprise Requirements Definition](docs/requirements_definition.md), [AWS Detailed Architecture Specification](docs/aws_detailed_design_specification.md), and [Local LLM Development Guide](docs/local_llm_development.md).


---

## 📝 Documentation Maintenance Policy

As defined in [`GEMINI.md`](GEMINI.md), **dual-language (English & Japanese) documentation maintenance is specifically restricted to the README files** (`README.md` and `README_JA.md`). All other internal documentation and ADRs remain in their designated canonical languages.

