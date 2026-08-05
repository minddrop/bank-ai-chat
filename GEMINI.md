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
2. **Format**: Standard ADR format (`Title`, `Status`, `Date`, `Context & Problem Statement`, `Decision Drivers`, `Considered Options`, `Decision Outcome`, `Consequences`).
3. **Registry**: Refer to `docs/adr/` directory for the full historical registry of accepted architectural decision records.

---

## 4. Git Commit Guidelines & Conventions

Frequent, atomic, and clear Git commits are mandatory for this repository.

### Commit Policy:
1. **Regular Milestone Commits**: Make a commit after completing every functional module, dataset update, control plane enhancement, or documentation file.
2. **Conventional Commit Syntax**:
   - `feat(...)`: New system features, control plane logic, or API endpoints.
   - `docs(...)`: Requirement updates, ADR additions, or architectural diagrams.
   - `fix(...)`: Bug fixes, security patches, or regex adjustments.
   - `test(...)`: Automated unit tests or guardrail stress test vectors.
   - `chore(...)`: Configuration updates, dependencies, or `.gitignore` changes.

---

## 5. Dual-Language README Maintenance Policy

To accommodate both international developers and Japanese management/reporting lines:
1. **README Dual Maintenance**: Dual-language documentation (English and Japanese) is maintained **EXCLUSIVELY in the README files** ([`README.md`](README.md) for English and [`README_JA.md`](README_JA.md) for Japanese).
2. **Synchronization Rule**: Whenever new features, system architecture changes, guardrail rules, or directory layout modifications occur, developers and AI agents MUST update both [`README.md`](README.md) and [`README_JA.md`](README_JA.md) in sync.
3. **Scope Limit**: Internal design specifications, ADRs (`docs/adr/`), and code comments are not required to be translated into dual languages; dual-language maintenance applies strictly and only to the README files.

---

## 6. System Directory Layout Overview

```
bank-ai-chat/
├── GEMINI.md                         # Overarching project concept, rules, & guidelines
├── README.md                         # English README (Primary documentation)
├── README_JA.md                      # Japanese README (日本語ドキュメント)
├── data/                             # Production synthetic bank accounts & Rakuten FAQ JSON
├── docs/                             # Requirements, AWS design, CI/CD, Costs, & adr/
├── scripts/                          # FAQ ingestion & data tools
├── src/                              # backend, control_plane, llm, rag, frontend
└── tests/                            # Automated unit tests for guardrails, RAG, and schemas
```

