# GEMINI.md - Japanese Major Bank Production AI Assistant

This document defines the overarching project concept, core architectural rules, regulatory compliance standards, Architectural Decision Record (ADR) policy, git commit conventions, and operational guidelines for the **Japanese Major Bank Production AI Chat System on AWS**.

---

## 1. Project Concept & Mission Statement

The **Japanese Major Bank AI Customer Assistant** is a full-scale, enterprise-grade digital banking assistant deployed on AWS Tokyo (`ap-northeast-1`). 

It provides 24/7/365 real-time customer support, account inquiry resolution, transaction history analysis, and general banking FAQ assistance for retail bank customers across Japan.

### Key Pillars:
1. **Uncompromised Japanese Legal & Regulatory Compliance**: Strict adherence to the Act on the Protection of Personal Information (APPI / 個人情報保護法), Financial Services Agency (FSA / 金融庁) AI guidelines, FISC Security Standards (FISC安全対策基準), Banking Act (銀行法), and Financial Instruments and Exchange Act (金融商品取引法).
2. **In-VPC Dual Control Planes**: Comprehensive Input Guardrails (PII scrubbing, prompt injection prevention) and Output Guardrails (grounding score verification, financial advice limitations, legal disclaimer appends).
3. **Enterprise AWS Architecture**: Full cloud infrastructure utilizing Amazon Bedrock (Amazon Nova Lite `amazon.nova-lite-v1:0`), AWS ECS Fargate, Amazon OpenSearch Service, AWS KMS AES-256 encryption, and S3 Object Lock audit logging.

---

## 2. Core Desirable Points & Operational Best Practices

To ensure production excellence and prevent regression, all code changes and system updates must adhere to the following principles:

### A. Japanese Language & Banking Etiquette (敬語・丁寧語)
- The AI assistant MUST communicate exclusively in polite, professional Japanese Keigo (丁寧語・敬語).
- Responses must maintain a helpful, non-authoritative, highly courteous bank representative persona.

### B. Strict PII Redaction & Data Minimization (APPI Compliance)
- **Zero PII Leakage Policy**: Absolutely no raw PII may leave the In-VPC Control Plane or be transmitted to model endpoints.
- All 7-digit account numbers (`\d{7}`), Katakana/Kanji customer names, branch codes (`\d{3}`), passwords, PINs, and phone numbers MUST be intercepted and scrubbed into tokenized placeholders before prompt assembly.

### C. RAG Grounding & Financial Advice Limitation (FSA & FIEA Compliance)
- Answers to general banking inquiries MUST be grounded against retrieved FAQ knowledge base context (Rakuten Bank FAQ database).
- The system MUST NEVER provide specific stock, mutual fund, or investment advice or guarantee financial returns.
- Every response MUST automatically include mandatory legal disclaimers.

### D. FISC-Compliant Tamper-Evident Audit Logging
- Every interaction must generate a cryptographic (SHA-256 signature) audit log entry containing session ID, timestamp, sanitized query, guardrail status, latency, and token usage, stored securely in AWS Tokyo (`ap-northeast-1`).

### E. Realistic Synthetic Mock Banking Data
- While live core banking connections are represented via realistic synthetic account data in development and testing, data structures MUST match authentic Japanese commercial banking schemas (普通預金, 定期預金, 外貨預金, カタカナ名義, 直近取引明細).

---

## 3. Architectural Decision Record (ADR) Policy

Architectural and regulatory decisions MUST be formally documented as **Architectural Decision Records (ADRs)** in `docs/adr/`.

### ADR Workflow & Standards:
1. **Creation**: Whenever a key architectural, security, data schema, model selection, or compliance decision is made, create a new Markdown file in `docs/adr/NNNN-<short-description>.md`.
2. **Format**: Follow the standard ADR structure:
   - **Title**: `# ADR NNNN: [Title]`
   - **Status**: `Accepted` | `Proposed` | `Deprecated`
   - **Date**: `YYYY-MM-DD`
   - **Context & Problem Statement**: Detailed background and regulatory context.
   - **Decision Drivers**: Key constraints (FISC, APPI, cost, latency).
   - **Considered Options**: Evaluated alternatives and rationale for rejection.
   - **Decision Outcome**: Selected solution and technical details.
   - **Consequences**: Positive and negative trade-offs.
3. **Commit**: Commit new ADRs to Git immediately alongside corresponding technical changes.

### Current ADR Registry:
- [0001-japanese-banking-compliance-and-control-planes.md](docs/adr/0001-japanese-banking-compliance-and-control-planes.md): APPI/FSA/FISC Compliance & In-VPC Dual Control Planes.
- [0002-aws-bedrock-nova-lite-model-selection.md](docs/adr/0002-aws-bedrock-nova-lite-model-selection.md): Model Selection (Amazon Nova Lite in `ap-northeast-1`).
- [0003-rakuten-bank-faq-rag-pipeline.md](docs/adr/0003-rakuten-bank-faq-rag-pipeline.md): Full Rakuten Bank FAQ Ingestion & RAG Pipeline.
- [0004-synthetic-japanese-account-schema.md](docs/adr/0004-synthetic-japanese-account-schema.md): Realistic Synthetic Japanese Bank Account Data Schema.
- [0005-hybrid-cloud-and-aws-poc-architecture.md](docs/adr/0005-hybrid-cloud-and-aws-poc-architecture.md): Target Hybrid On-Prem + AWS Production Cloud Architecture.
- [0006-cicd-and-production-cost-estimation.md](docs/adr/0006-cicd-and-production-cost-estimation.md): Enterprise CI/CD Pipeline & Production AWS Cost Estimation.

---

## 4. Git Commit Guidelines & Conventions

Frequents, atomic, and clear Git commits are mandatory for this repository.

### Commit Policy:
1. **Regular Milestone Commits**: Make a commit after completing every functional module, dataset update, control plane enhancement, or documentation file.
2. **Conventional Commit Syntax**: Use standardized conventional commit prefixes:
   - `feat(...)`: New system features, control plane logic, or API endpoints.
   - `docs(...)`: Requirement updates, ADR additions, or architectural diagrams.
   - `fix(...)`: Bug fixes, security patches, or regex adjustments.
   - `test(...)`: Automated unit tests or guardrail stress test vectors.
   - `chore(...)`: Configuration updates, dependencies, or `.gitignore` changes.
3. **Commit Message Format**:
   ```
   <type>(<scope>): <short summary in imperative mood>

   [optional detailed description of changes, regulatory justification, or test results]
   ```

---

## 5. System Directory Layout

```
bank-ai-chat/
├── GEMINI.md                         # Overarching project concept, ADR policy, & guidelines
├── README.md                         # Repository overview & quickstart guide
├── .gitignore                        # Git exclusions (caches, runtime logs)
├── data/
│   ├── mock_bank_accounts.json       # Production synthetic Japanese account database
│   └── rakuten_faq.json              # Ingested Rakuten Bank FAQ knowledge base
├── docs/
│   ├── requirements_definition.md    # Comprehensive Enterprise Requirements & Schemas
│   ├── aws_architecture.md           # AWS Production Topology & Hybrid Design
│   ├── cicd_pipeline.md              # CI/CD Automated Testing & Deployment Strategy
│   ├── cost_estimation.md            # AWS Production Cost Estimation & Sizing
│   └── adr/                          # Architectural Decision Records (0001 - 0006+)
├── scripts/
│   └── crawl_full_rakuten_faq.py     # FAQ Knowledge Base ingestion pipeline script
├── src/
│   ├── backend/
│   │   ├── app.py                    # FastAPI Backend Application
│   │   └── server.py                 # Production Web & REST API Server
│   ├── control_plane/
│   │   ├── input_guardrail.py        # Input PII Scrubbing & Prompt Injection Filter
│   │   ├── output_guardrail.py       # Output Grounding Check & Disclaimer Injector
│   │   └── audit_logger.py           # FISC-Compliant Audit Logger
│   ├── llm/
│   │   └── bedrock_nova.py           # Amazon Bedrock (Nova Lite) Interface Client
│   ├── rag/
│   │   └── vector_store.py           # Vector Index & Cosine RAG Search Engine
│   └── frontend/
│       ├── index.html                # Bank Customer AI Portal UI Structure
│       ├── styles.css                # Premium Dark/Navy Bank UI Styling
│       └── app.js                    # Web Frontend Logic & Live Control Plane Monitor
└── tests/
    ├── test_account_data.py          # Account Schema Unit Tests
    ├── test_guardrails.py            # Input/Output Guardrail Unit Tests
    └── test_rag.py                   # RAG Search Unit Tests
```
