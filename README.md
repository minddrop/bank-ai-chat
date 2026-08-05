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
- `pytest` for automated test execution

### Installation & Execution
1. Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run unit and compliance test suite:
   ```bash
   pytest tests/
   ```

---

## ⚖️ Regulatory & Security Standards

- **APPI (個人情報保護法)**: Zero PII transmission to external LLM endpoints.
- **FSA AI Guidelines & FIEA (金融商品取引法)**: Automated grounding checks and financial advice restrictions.
- **FISC Security Standards (FISC安全対策基準)**: Tamper-evident audit logging and KMS encryption.

---

## 📝 Documentation Maintenance Policy

As defined in [`GEMINI.md`](GEMINI.md), **dual-language (English & Japanese) documentation maintenance is specifically restricted to the README files** (`README.md` and `README_JA.md`). All other internal documentation and ADRs remain in their designated canonical languages.
