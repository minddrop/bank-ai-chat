# Enterprise Requirements Definition & Specification
## Japanese Major Bank AI Customer Assistant System

---

## 1. Overview & Business Objectives

This document establishes the comprehensive functional, non-functional, security, data schema, architectural, CI/CD, wireframe, and cost estimation requirements for the **AI Customer Assistant System** of a major Japanese commercial bank (メガバンク).

The system serves as a 24/7/365 digital banking portal assistant, handling customer account inquiries, transaction history searches, and general banking FAQ guidance while ensuring 100% compliance with Japanese legal regulations, Financial Services Agency (FSA) guidelines, and FISC security standards.

---

## 2. Regulatory & Legal Framework

### 2.1 Act on the Protection of Personal Information (個人情報保護法 - APPI)
- **Data Anonymization Policy**: Absolutely no raw PII (Personally Identifiable Information) may leave the in-VPC Control Plane boundaries or be passed to external LLM endpoints.
- **PII Scrubbing Categories**:
  - Full Kanji / Katakana Names (`口座名義人`: `ヤマダ タロウ`)
  - Account Numbers (`口座番号`: 7-digit `\d{7}`)
  - Branch Codes (`支店コード`: 3-digit `\d{3}`)
  - Passwords, PINs, Security Card Coordinates (`暗証番号`, `PIN`)
  - Phone Numbers (`電話番号`), Email Addresses, Physical Addresses
- **Enforcement**: In-VPC Input Guardrail intercepts and redacts PII using tokenized replacement (e.g. `[口座番号保護: XXXXXXX]`).

### 2.2 Financial Services Agency (FSA) AI Guidelines (金融庁ガイドライン)
- **AI Explainability & Governance**: Traceable audit logging for all AI responses, input scrubbed tokens, retrieved RAG contexts, and confidence scores.
- **Financial Instruments and Exchange Act (金融商品取引法 - FIEA)**: Prohibits un-licensed investment solicitation or specific stock/fund purchase recommendations.
- **Mandatory Disclaimers**: Automatic injection of legal notices stating that AI answers provide general information only and do not form binding financial advice or contracts.

### 2.3 FISC Security Guidelines for Financial Information Systems (FISC安全対策基準)
- **Data Sovereignty**: Infrastructure and LLM processing (Amazon Bedrock) strictly restricted to AWS Tokyo (`ap-northeast-1`) or Osaka (`ap-northeast-2`) regions.
- **Encryption**: AES-256 (KMS CMK) for data at rest; TLS 1.3 for data in transit.
- **Audit Retention**: Immutable, tamper-evident log streams with SHA-256 signature verification retained for 10 years per banking regulations.

### 2.4 Banking Act (銀行法 - Ginkō Hō)
- **Contract Boundary**: AI responses are informational. Actionable operations (fund transfers 振込, PIN resets, account closures) require step-up Multi-Factor Authentication (MFA) via official Internet Banking.

---

## 3. Mock Data Definitions & Schemas

To fulfill full-scale POC standards while protecting customer privacy under APPI, realistic synthetic datasets are defined.

### 3.1 Customer Profile Schema (`CustomerProfile`)
| Field Name | Type | Constraint | Description | Example |
|---|---|---|---|---|
| `customer_id` | String | Unique Key (`CUST-\d{4}`) | Synthetic Customer Identifier | `"CUST-1001"` |
| `name_kanji` | String | UTF-8 Kanji | Customer Name in Kanji | `"山田 太郎"` |
| `name_katakana` | String | UTF-8 Full Katakana | Customer Name in Katakana | `"ヤマダ タロウ"` |
| `birth_date` | String | YYYY-MM-DD | Date of Birth | `"1985-04-12"` |
| `branch_code` | String | 3-digit numeric | Japanese Bank Branch Code | `"001"` |
| `branch_name` | String | UTF-8 String | Japanese Bank Branch Name | `"本店営業部"` |
| `account_number` | String | 7-digit numeric | Main Savings Account Number | `"1234567"` |
| `customer_tier` | Enum | `SUPER_VIP`, `VIP`, `PREMIUM`, `REGULAR` | Customer Loyalty Tier | `"SUPER_VIP"` |
| `happy_program_stage`| String | UTF-8 Description | Fee Waiver Status Stage | `"スーパーVIP (他行振込手数料3回無料)"` |

### 3.2 Account Schema (`BankAccount`)
| Field Name | Type | Constraint | Description | Example |
|---|---|---|---|---|
| `account_id` | String | Unique Key (`ACC-\d{4}-\w+`) | Sub-Account Identifier | `"ACC-1001-SAV"` |
| `account_type` | String | UTF-8 String | Account Type Label | `"普通預金"` |
| `account_type_code`| Enum | `SAVINGS`, `TIME_DEPOSIT`, `FOREIGN_USD`, `CARD_LOAN` | Internal Type Code | `"SAVINGS"` |
| `balance` | Number | Integer (JPY) or Float (USD) | Available Balance | `2450000` |
| `currency` | Enum | `JPY`, `USD`, `EUR` | Currency Code | `"JPY"` |
| `interest_rate` | String | Percentage | Annual Interest Rate | `"0.02%"` |
| `maturity_date` | String | YYYY-MM-DD (Optional) | Maturity Date for Time Deposit | `"2027-03-31"` |

### 3.3 Transaction History Schema (`BankTransaction`)
| Field Name | Type | Constraint | Description | Example |
|---|---|---|---|---|
| `transaction_id` | String | Unique Key (`TXN-\d{5}`) | Transaction Record ID | `"TXN-90812"` |
| `date` | String | YYYY-MM-DD | Transaction Execution Date | `"2026-08-01"` |
| `type` | String | UTF-8 String | Transaction Category | `"振込入金"`, `"ATM出金"`, `"デビット決済"` |
| `amount` | Number | Signed Integer | Amount (+ for Credit, - for Debit)| `420000` |
| `currency` | Enum | `JPY`, `USD` | Transaction Currency | `"JPY"` |
| `description` | String | UTF-8 Description | Counterparty / Merchant Memo | `"給与振込 カブシキガイシャABC"` |
| `balance_after` | Number | Integer (JPY) | Account Balance Post-Transaction | `2450000` |

### 3.4 FAQ Knowledge Schema (`FAQItem`)
| Field Name | Type | Description | Example |
|---|---|---|---|
| `id` | String | Unique FAQ Code | `"FAQ-RB-1001"` |
| `category` | String | Major Category | `"振込・送金"` |
| `question` | String | Customer Question Text | `"他行への振込手数料はいくらですか？"` |
| `answer` | String | Ground Truth Answer Text | `"楽天銀行から他行口座への振込手数料は..."` |
| `url` | String | Help Portal URL | `"https://help-personal.rakuten-bank.net/faq/show/1001"` |

---

## 4. Functional Features List

| ID | Feature Name | Detailed Description | Priority |
|---|---|---|---|
| **FR-01** | Account Balance Inquiry | Retrieve current balance across Ordinary Savings, Time Deposits, and Foreign Currency accounts after PII masking. | High |
| **FR-02** | Transaction History View | Display multi-month transaction history (salary, ATM, debit card, direct debits) sorted by date. | High |
| **FR-03** | Rakuten FAQ RAG Search | Semantic vector search over complete Rakuten Bank FAQ database returning top grounded answers. | High |
| **FR-04** | Input PII Redaction | Automatically scrub 7-digit account numbers, Katakana names, branch codes, PINs, and phone numbers. | High |
| **FR-05** | Prompt Injection Filter | Detect and block prompt injections, system prompt extraction, or jailbreak attempts. | High |
| **FR-06** | Output PII Leak Detector | Scan generated LLM output for accidental PII reflection and scrub matched patterns. | High |
| **FR-07** | RAG Grounding Verification | Compute relevance score between retrieved FAQ context and generated LLM response. | High |
| **FR-08** | Investment Advice Limitation | Block requests asking for stock recommendations or guaranteed investment fund returns per FIEA. | High |
| **FR-09** | Disclaimer Injection | Append mandatory Japanese banking legal disclaimers to every AI response. | High |
| **FR-10** | FISC Audit Logger | Record session ID, timestamp, sanitized query, guardrail status, latency, and SHA-256 hash. | High |
| **FR-11** | Customer Profile Switcher | Interactive simulator allowing swappable customer profiles (山田 太郎, 佐藤 花子, etc.). | High |
| **FR-12** | Live Control Plane Dashboard| Visual panel displaying real-time Input Guardrail status, grounding score, and audit log stream. | High |
| **FR-13** | Multi-account Type Support | Handle Ordinary Savings (普通預金), Time Deposit (定期預金), Foreign Currency (外貨預金), and Card Loans. | Medium |
| **FR-14** | Step-Up Auth Warning | Direct customers to authenticated Direct Banking for high-security operations (振込・解約). | Medium |
| **FR-15** | Quick Sample Prompts | Provide one-click sample chips (Balance check, FAQ search, PII masking test, Injection test). | Medium |

---

## 5. Non-Functional Features List (NFR)

| ID | Category | Requirement Specification | Standard / Target |
|---|---|---|---|
| **NFR-01** | **Availability** | System Uptime SLA of 99.99% for backend API and Control Planes. | Multi-AZ AWS Deployment |
| **NFR-02** | **Latency** | End-to-end response time < 800ms (P95 < 1,200ms) including Control Planes & Bedrock Nova Lite. | Performance SLA |
| **NFR-03** | **Throughput** | Peak processing capability of 1,000 Transactions Per Second (TPS). | Auto-scaling ECS Fargate |
| **NFR-04** | **Data Sovereignty** | 100% of LLM inference, data storage, and audit logs executed in AWS Tokyo (`ap-northeast-1`). | FISC Compliance |
| **NFR-05** | **Encryption at Rest** | AES-256 encryption via AWS KMS Customer Managed Keys (CMK) for S3 and OpenSearch. | FISC / APPI Compliance |
| **NFR-06** | **Encryption in Transit** | Enforce TLS 1.3 for all internal microservices and external browser endpoints. | Security Standard |
| **NFR-07** | **Audit Trail Retention** | Retain encrypted, tamper-evident audit logs in S3 for 10 years with Object Lock enabled. | Banking Law Requirement |
| **NFR-08** | **Disaster Recovery** | RPO = 0 (No data loss for audit logs), RTO < 15 minutes via Multi-Region AWS Backup. | Business Continuity |
| **NFR-09** | **DDoS & Web Security** | Managed AWS WAF with rate limiting, OWASP Top 10 rules, and AWS Shield Standard. | Infrastructure Security |
| **NFR-10** | **Browser Support** | Modern Japanese desktop & mobile browsers (Chrome, Edge, Safari, iOS/Android WebViews). | Accessibility |

---

## 6. Workflows & Screen Wireframes

### 6.1 End-to-End Customer Chat & Control Plane Workflow

```
Customer Input Payload (Browser / Mobile Portal)
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 1: Inbound Control Plane & DLP (FastAPI / ECS Fargate)             │
│  - Unicode NFC Normalization & Zero-Width (`U+200B`) / Cipher Stripper  │
│  - Direct & Indirect Prompt Injection Classifier (OWASP LLM01/LLM02)    │
│  - PII Masking & KMS Salted Token Vault (`[TOKEN_ACCT_a1b2c3d4]`)       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Sanitized Prompt Payload [P95 <= 45ms]
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 2: RAG Context & Core Banking Retrieval                            │
│  - OpenSearch Serverless Vector Store Query (Tier-Based RBAC Metadata)  │
│  - Read-Only Core Banking Account Lookup (OAuth 2.0 mTLS)               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Context Payload [P95 <= 85ms]
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 3: Amazon Bedrock Inference (ap-northeast-1)                       │
│  - Model: Amazon Nova Lite (`amazon.nova-lite-v1:0`) via PrivateLink    │
│  - System Prompt: Japanese Bank Keigo Business Persona (Read-Only)      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Raw Generated Response [P95 <= 450ms]
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 4: Outbound Control Plane & Post-DLP                               │
│  - NLI Entailment Grounding Verification (Entailment Score >= 0.85)     │
│  - Outbound PII Reflection Scanner & Financial Numeric Cross-Check      │
│  - FIEA Article 38 Prohibited Investment Advice Filter                  │
│  - Mandatory Japanese Banking Legal Disclaimer Injection                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Validated Response Payload [P95 <= 50ms]
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 5: FISC Audit Logger & Telemetry                                   │
│  - SHA-256 Tamper-Evident Hashing & Metric Streaming to CloudWatch Logs │
│  - Async Write to S3 Bucket with Object Lock (10-Year WORM Compliance)  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Total Client Latency [P95 <= 630ms]
                                     ▼
Render Response & Live Control Plane Metrics in UI
```

### 6.2 UI Wireframe Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ メガバンク日本銀行 | AI Customer Banking Portal (FISC & APPI Guarded)                        │
│ [AWS ap-northeast-1]  [Bedrock Amazon Nova Lite]  [FISC安全対策基準 適合]                   │
├──────────────────────────┬─────────────────────────────────────┬─────────────────────────────┤
│ 口座シミュレーター (APPI) │ 💬 AI 行内カスタマーサポート          │ 🛡️ 統制面 (Control Plane)    │
│ [ ヤマダ タロウ ▼ ]      │                                     │                             │
│ ┌──────────────────────┐ │ 🤖 AI: いらっしゃいませ。           │ [Input Guardrail: PASSED]   │
│ │ 普通預金 (スーパーVIP)│ │ 口座残高やお振込手数料について      │ [Grounding Score: 95%]      │
│ │ 口座番号: 001-1234567│ │ お気軽にご質問ください。          │                             │
│ │ 残高: ¥2,450,000     │ │                                     │ ──────── 入力データ監視 ─── │
│ └──────────────────────┘ │ 👤 客: 普通預金の残高と直近の出金   │ [Sanitized]: 口座番号 [保護]│
│                          │ 履歴を教えてください。              │                             │
│ ── 直近取引明細 ──────── │                                     │ ──────── RAG 参照ナレッジ ───│
│ • 08/01 給与振込 +420,000│ 🤖 AI: ヤマダ タロウ様の普通預金    │ • [振込] 他行振込手数料     │
│ • 07/28 デビット -15,400 │ 現在残高は 2,450,000円です。        │                             │
│ • 07/25 振込出金 -88,000 │ 直近取引は 08/01 給与振込...        │ ──────── 出力検証 & 免責 ────│
│                          │ ----------------------------------  │ [免責事項]: 自動付与済      │
│ ── クイック質問サンプル ─│ 【重要事項・免責事項】              │                             │
│ [💰 残高・取引確認]      │ ※本AIの回答は一般的な情報提供に...  │ ── FISC 監査ログストリーム ──│
│ [💸 振込手数料FAQ]       │                                     │ [15:00:12] AUDIT-901 | HASH │
│ [🔒 PIIマスキングテスト] │ ┌─────────────────────────────────┐ │ [15:00:14] AUDIT-902 | HASH │
│ [⚠️ 攻撃検知テスト]      │ │ 質問を入力してください...  [送信]│ │                             │
└──────────────────────────┴─────────────────────────────────┴─────────────────────────────┘
```

---

## 7. CI/CD Plan & Workflow

### 7.1 CI/CD Architecture Overview

```
                  ┌──────────────────────────────┐
                  │ Git Push / Pull Request      │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│ GitHub Actions / AWS CodePipeline                                 │
│                                                                  │
│  ┌────────────────────┐    ┌──────────────────────────────────┐  │
│  │ 1. Code Quality    │    │ 2. Automated Test Suite          │  │
│  │  - Python Flake8   │───►│  - Unit Tests (Guardrails, RAG)  │  │
│  │  - ESLint / Prettier│   │  - Mock Account Schema Validation │  │
│  └────────────────────┘    └────────────────┬─────────────────┘  │
│                                             │                    │
│  ┌────────────────────┐    ┌────────────────▼─────────────────┐  │
│  │ 4. Security Scan   │    │ 3. Guardrail Stress Tests        │  │
│  │  - Bandit / Trivy  │◄───│  - PII Scrubbing Boundary Check  │  │
│  │  - OWASP Dependency│    │  - Prompt Injection Test Vectors │  │
│  └─────────┬──────────┘    └──────────────────────────────────┘  │
└────────────┼─────────────────────────────────────────────────────┘
             │ Build Approved
             ▼
┌──────────────────────────────────────────────────────────────────┐
│ Staging & Production Deployment                                  │
│                                                                  │
│  ┌────────────────────────┐        ┌──────────────────────────┐  │
│  │ AWS ECR Image Push     ├───────►│ AWS ECS Fargate          │  │
│  │ (Docker Container)     │        │ Blue/Green Canary Deploy │  │
│  └────────────────────────┘        └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 7.2 Automated Test Gates
1. **Linting & Code Quality**: `flake8 src/`, `black --check src/`.
2. **Unit Test Suite**: `python3 -m unittest discover -s tests -p "test_*.py"`.
3. **Guardrail Compliance Testing**:
   - PII Scrubbing accuracy checks for account numbers, Katakana names, phone numbers.
   - Injection Adversarial suite (100+ prompt injection payloads).
4. **Security Vulnerability Scan**: Container image vulnerability scanning via AWS ECR Inspector and Trivy.
5. **Deployment Strategy**: Zero-downtime Blue/Green Canary Deployment via AWS CodeDeploy.

---

## 8. Production AWS Environment Cost Estimation

Cost estimates for production deployment in **AWS Tokyo Region (`ap-northeast-1`)** supporting 1,000,000 monthly customer interactions (~33,000 interactions/day).

### 8.1 Monthly Cost Breakdown (AWS Tokyo Region)

| AWS Service | Configuration & Usage | Estimated Monthly Cost (USD) | Estimated Monthly Cost (JPY @ 150/$) |
|---|---|---|---|
| **Amazon Bedrock (Nova Lite)** | 1M Requests (Avg 500 input tokens, 300 output tokens / req) | $120.00 | ¥18,000 |
| **AWS ECS Fargate (Backend)** | 4 Tasks (2 vCPU, 4GB RAM) Multi-AZ Auto-scaling | $180.00 | ¥27,000 |
| **Amazon OpenSearch (RAG)** | 2 Nodes `t3.medium.search` Multi-AZ for Vector FAQ Store | $140.00 | ¥21,000 |
| **Amazon S3 (Audit Logs & Assets)** | Encrypted Bucket, 50GB storage + lifecycle retention | $15.00 | ¥2,250 |
| **AWS KMS (Customer Managed Key)** | 2 CMKs for log encryption & vector DB encryption | $2.00 | ¥300 |
| **AWS WAF & Shield Standard** | Managed Web ACL + OWASP Top 10 Security Rules | $35.00 | ¥5,250 |
| **Amazon CloudWatch** | Application metrics, log insights, alarms | $25.00 | ¥3,750 |
| **Application Load Balancer (ALB)**| Dual-AZ ALB with TLS 1.3 Certificate | $28.00 | ¥4,200 |
| **Total Estimated Monthly Cost** | | **$545.00 / month** | **¥81,750 / 月** |

### 8.2 Annual Production Cost Summary
- **Annual AWS Cloud Operations Cost**: **$6,540 USD / year** (approx. **¥981,000 JPY / 年**).
- **Cost Efficiency Advantage**: Amazon Nova Lite on Amazon Bedrock provides over **85% cost savings** compared to traditional enterprise LLM endpoints while fulfilling all FISC security and Tokyo data sovereignty guidelines.
