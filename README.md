# Japanese Major Bank AI Customer Assistant (AWS Production Architecture)

[![Language: English](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![Language: 日本語](https://img.shields.io/badge/Language-日本語-red.svg)](README_JA.md)

> **Language Switch**: [English](README.md) | [日本語 (Japanese)](README_JA.md)

An enterprise-grade, 24/7/365 digital banking assistant deployed on AWS Tokyo (`ap-northeast-1`) designed for retail banking customers across Japan. Powered by Amazon Bedrock (Amazon Nova Lite `amazon.nova-lite-v1:0`), Amazon OpenSearch Service RAG, In-VPC Dual Control Plane guardrails, resilient Core Banking circuit breakers, and deterministic Terraform IaC.

---

## 🌟 Key Architectural Features

1. **Polite Japanese Banking Persona (敬語・丁寧語)**
   - Operates strictly using natural, courteous Japanese banking Keigo (丁寧語・敬語) to ensure trustworthy, non-authoritative customer service.

2. **In-VPC Dual Control Planes (Input & Output Guardrails)**
   - **Input Guardrail**: Automatic redaction of Personally Identifiable Information (PII) like 7-digit account numbers, customer names, branch codes, PINs, and phone numbers before prompt assembly (APPI / 個人情報保護法 compliance). Intercepts prompt injection and jailbreak attacks.
   - **Output Guardrail**: N-gram semantic entailment grounding score validation (REQ-AI-013), strict prohibition of specific investment/stock advice (FSA & FIEA compliance), competitor bank redirection, and automated inclusion of legal disclaimers.

3. **Real-Time W3C Server-Sent Events (SSE) Streaming (REQ-IF-015, ADR-0013)**
   - Sub-second streaming chat endpoint (`POST /api/chat/stream`) emitting real-time control plane events, typing chunks, and completion telemetry.

4. **Zero-Trust Authentication & Step-Up MFA (REQ-FUN-005, ADR-0014)**
   - Pure Python RFC 7519 JWT implementation with KMS-backed secret management, token blacklist revocation, and automated intent detection redirecting high-risk transactions (transfers, PIN change, account closure) to official Internet Banking MFA portals.

5. **Core Banking Resilience & 3-State Circuit Breaker (REQ-FUN-004, ADR-0008)**
   - FISC contingency-compliant 3-state Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`), 60s in-memory cache TTL, 1.5s execution timeout, and graceful degradation returning polite Japanese maintenance notices during core banking outages.

6. **Deterministic Infrastructure as Code (Terraform) (REQ-OPS-017, ADR-0016)**
   - Multi-AZ 3-tier VPC (`10.100.0.0/16`), AWS KMS CMK AES-256, Least-Privilege IAM Roles, OpenSearch Serverless Vector Collection (1024-dim Titan v2), Application Load Balancer with TLS 1.3, AWS WAF v2 managed rules, and ECS Fargate cluster.

7. **FISC Security & Tamper-Evident Audit Logging**
   - Cryptographic SHA-256 signed audit logging stored in AWS Tokyo (`ap-northeast-1`) with S3 Object Lock 10-year WORM compliance and AWS KMS AES-256 encryption.

---

## 📁 Repository Structure

```
bank-ai-chat/
├── GEMINI.md                         # Project governance, architectural rules, & guidelines
├── README.md                         # English README (Primary)
├── README_JA.md                      # Japanese README (日本語)
├── data/                             # Production synthetic bank accounts & Rakuten FAQ datasets
├── docs/                             # AWS Architecture, Detailed Specification, CI/CD, Costs, & adr/
│   ├── adr/                          # Architectural Decision Records (ADR-0001 - ADR-0021)
│   └── requirements/                 # Enterprise Requirements Suite (18 specifications)
├── scripts/                          # FAQ crawler, database tools, & grounding benchmark CLI
│   └── evaluate_grounding.py         # 100-pair golden dataset grounding evaluation runner
├── src/                              # Backend, Control Plane, Core Banking, Frontend, LLM, RAG
│   ├── backend/                      # FastAPI, SSE streaming, JWT Auth & Step-Up MFA, RFC 7807
│   ├── control_plane/                # In-VPC Input & Output Guardrails, Brand, AML, Audit Logger
│   ├── core_banking/                 # Synthetic banking DB & resilient client with Circuit Breaker
│   ├── frontend/                     # Simulator UI & User Portal with real-time SSE & Step-Up cards
│   ├── llm/                          # Bedrock Nova Lite & Local LLM client engines
│   └── rag/                          # Pre-indexed TF-IDF / OpenSearch vector search store
├── terraform/                        # Deterministic Terraform IaC Suite (REQ-OPS-017)
│   ├── environments/                 # Root environment configs (dev, prod) with S3 remote state
│   └── modules/                      # Reusable modules (vpc, security, alb, waf, opensearch, ecs)
└── tests/                            # 60 automated unit & integration tests
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) fast Python package & environment manager
- (Optional) Ollama or LM Studio for local LLM inference (e.g., `ollama pull qwen2.5:0.5b`)

### Installation
1. Clone the repository and sync dependencies using `uv`:
   ```bash
   uv sync
   ```

### 💻 Running the Application Locally (Using `uv`)

#### Mode A: Local LLM Provider (Recommended for Offline Dev & Zero AWS Cost)
Run the application in local provider mode without AWS credentials using `uv`. The system connects to a local Ollama server if active, or automatically falls back to the built-in Local Light Development Engine:
```bash
export LLM_PROVIDER=local
export LOCAL_LLM_MODEL=qwen2.5:0.5b   # Optional: qwen2.5:0.5b, qwen2.5:1.5b, gemma:2b
export LOCAL_LLM_URL=http://localhost:11434/v1 # Optional: Ollama/LM Studio endpoint

# Launch the FastAPI backend server with uv
uv run python3 src/backend/app.py
```

#### Mode B: AWS Bedrock Provider Mode (Production Preview)
Run against live Amazon Bedrock (`amazon.nova-lite-v1:0`) in AWS Tokyo (`ap-northeast-1`) using `uv` (requires active AWS IAM credentials):
```bash
export LLM_PROVIDER=bedrock
uv run python3 src/backend/app.py
```

#### Mode C: Standard HTTP Server (Zero External Frameworks)
Alternatively, launch using the native Python standard library HTTP server with `uv`:
```bash
uv run python3 src/backend/server.py
```

#### Mode D: Containerized Stack (Docker & Docker Compose)
Build and run the stack in a Docker container (emulating AWS ECS Fargate topology):
```bash
docker-compose up --build
```

---

### 🌐 Accessing the Web Interface
Once the server is running, open your web browser and navigate to:
- **Simulator & Control Plane**: **`http://localhost:8000`**
- **Direct Customer Banking Portal**: **`http://localhost:8000/user/`**

Featuring:
- Real-time W3C Server-Sent Events (SSE) token streaming
- Interactive Step-Up MFA redirection cards on high-risk transaction queries
- Synthetic Customer Context Switcher (`山田 太郎`, `佐藤 花子`)
- In-VPC Control Plane Telemetry Dashboard (Input/Output Guardrails, Grounding gauge, FISC Audit log viewer)

---

### 🧪 Running Automated Unit & Compliance Tests
Run the automated test suite across control planes, RAG engines, circuit breakers, and SSE endpoints:
```bash
uv run pytest
# or using python virtual environment:
PYTHONPATH=src ./.venv/bin/pytest tests/ -v
```

### 📊 Running Grounding Benchmark Evaluation (REQ-AI-013)
Run the automated grounding benchmark CLI against the 100-pair golden FAQ dataset:
```bash
./.venv/bin/python3 scripts/evaluate_grounding.py --limit 100
```

---

## ⚖️ Regulatory & Security Standards

- **APPI (個人情報保護法)**: Zero PII transmission to external LLM endpoints.
- **FSA AI Guidelines & FIEA (金融商品取引法)**: Automated grounding checks and financial advice restrictions.
- **FISC Security Standards (FISC安全対策基準)**: Tamper-evident audit logging and KMS encryption.
- **Global Financial Standards**: Full traceability against **PCI-DSS 4.0**, **GLBA**, **CFPB AI Guidance**, **SR 11-7**, **ISO 42001/AIUC-1**, and **NYDFS Part 500**. See [Security & Compliance Requirements](docs/requirements/04_security_and_compliance/08_appi_pii_dlp_requirements.md) and [ADR 0009](docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md).
- **Compute Architecture & Streaming Governance**: AWS ECS Fargate container architecture ensuring un-truncated SSE response streaming, 29-second proxy limit evasion, zero cold starts, and 3-tier VPC FISC compliance. See [ADR 0011](docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) and [ADR 0013](docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md).
- **In-VPC Salted PII Tokenization & Step-Up Auth**: Tokenized PII vaulting under APPI ([ADR 0012](docs/adr/0012-in-vpc-salted-tokenization-vault.md)) and legal boundary enforcement under the Japanese Banking Act ([ADR 0014](docs/adr/0014-zero-trust-step-up-authentication-boundary.md)).
- **Brand Defense, AML & Scope Locking**: Deterministic competitor institution suppression (35+ Japanese banks/fintechs), anti-financial crime & money laundering interception (犯罪収益移転防止法), and anti-compute hijacking ([ADR 0020](docs/adr/0020-brand-protection-anti-financial-crime-and-scope-guardrails.md)).
- **Infrastructure Codification & Production Readiness**: OpenSearch Serverless network policies & 1024-dim Titan v2 embedding standards ([ADR 0015](docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md)), deterministic Terraform IaC remote state management ([ADR 0016](docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md)), enterprise IAM least-privilege role scoping ([ADR 0017](docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md)), and production CloudWatch observability targets ([ADR 0018](docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md)). See detailed [Enterprise Requirements Definition Suite (18 Specs)](docs/requirements/README.md).

---

## 📝 Documentation Maintenance Policy

As defined in [`GEMINI.md`](GEMINI.md), **dual-language (English & Japanese) documentation maintenance is specifically restricted to the README files** (`README.md` and `README_JA.md`). All other internal documentation and ADRs remain in their designated canonical languages.
