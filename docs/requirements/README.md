# メガバンク AIカスタマーアシスタント 要件定義書体系 (Enterprise Requirements Suite)
## Japanese Major Bank Enterprise AI Chat System - Requirements Portal

- **改定日**: 2026-08-21 (第1.0版)
- **対象環境**: AWS Tokyo Region (`ap-northeast-1`)
- **準拠法規制**: 個人情報保護法 (APPI), 金融庁AIガイドライン, 金融商品取引法第38条, FISC安全対策基準 第9版, 銀行法
- **アーキテクチャ統制**: [ADR-0001](../../adr/0001-japanese-banking-compliance-and-control-planes.md) 〜 [ADR-0019](../../adr/0019-local-llm-provider-and-fallback-architecture.md)

---

## 1. 要件定義書 ドキュメント構成マップ (Document Map)

本要件定義書体系は、金融機関のシステム監査およびコンプライアンス審査に完全適合するよう、**7つのドメイン・全18ドキュメント**で構成されています。

```
docs/requirements/
├── README.md                                             # 本総合インデックス & トレーサビリティ
│
├── 01_business/                                          # 【1. 業務要件ドメイン】
│   ├── 01_business_requirements.md                       # REQ-BUS-001: 業務要件定義書 (背景・目的・ROI)
│   └── 02_business_process_and_use_cases.md              # REQ-BUS-002: 業務フロー & ユースケース定義書
│
├── 02_functional/                                        # 【2. 機能要件ドメイン】
│   ├── 03_ai_and_rag_functional.md                       # REQ-FUN-003: AI対話・RAG機能要件定義書
│   ├── 04_core_banking_integration.md                    # REQ-FUN-004: 勘定系連携・トランザクション要件書
│   ├── 05_auth_and_session.md                            # REQ-FUN-005: 認証・認可・ステップアップMFA要件書
│   └── 06_frontend_and_uiux.md                           # REQ-FUN-006: UI/UX・画面表示要件定義書
│
├── 03_non_functional/                                    # 【3. 非機能要件ドメイン (IPA準拠)】
│   └── 07_non_functional_requirements.md                 # REQ-NFR-007: IPA非機能要求グレード要件定義書
│
├── 04_security_and_compliance/                           # 【4. セキュリティ & コンプライアンス】
│   ├── 08_appi_pii_dlp_requirements.md                   # REQ-SEC-008: 個人情報保護法 (APPI) 準拠要件書
│   ├── 09_fsa_and_legal_compliance.md                    # REQ-SEC-009: 金融庁 (FSA)・金商法コンプライアンス要件書
│   ├── 10_fisc_security_standards.md                     # REQ-SEC-010: FISC安全対策基準 適合性要件書
│   └── 11_prompt_injection_defense.md                    # REQ-SEC-011: 敵対的攻撃防御・ガードレール要件書
│
├── 05_ai_and_data/                                       # 【5. AIモデル & データ定義】
│   ├── 12_prompt_and_banking_persona.md                  # REQ-AI-012:  AIプロンプト・銀行敬語ペルソナ定義書
│   ├── 13_grounding_and_evaluation.md                    # REQ-AI-013:  AIモデル評価・グラウンディング判定基準書
│   └── 14_data_models_and_schemas.md                     # REQ-DAT-014: データモデル・スキーマ定義書
│
├── 06_interfaces/                                        # 【6. インターフェース定義】
│   ├── 15_api_specifications.md                          # REQ-IF-015:  API・外部インターフェース仕様書
│   └── 16_fallback_and_circuit_breaker.md                # REQ-IF-016:  エラーハンドリング・縮退運用要件書
│
└── 07_operations_and_infra/                              # 【7. インフラ & 運用保守】
    ├── 17_infrastructure_iac_requirements.md             # REQ-OPS-017: インフラストラクチャ・IaC要件書
    └── 18_audit_logging_and_monitoring.md                # REQ-OPS-018: 監査ログ・証跡管理・運用監視要件書
```

---

## 2. 要件定義書 マスター一覧 & トレーサビリティマトリクス

| No | 文書ID | 要件定義書名 | 主管標準 / 規制 | 関連ADR | 実装モジュール |
|---|---|---|---|---|---|
| **01** | `REQ-BUS-001` | [業務要件定義書 (総括)](01_business/01_business_requirements.md) | 銀行法, FSA AI指針 | [ADR-0001](../../adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0005](../../adr/0005-hybrid-cloud-and-aws-poc-architecture.md) | `src/backend/app.py` |
| **02** | `REQ-BUS-002` | [業務フロー・ユースケース定義書](01_business/02_business_process_and_use_cases.md) | 全銀協不正送金防止基準 | [ADR-0004](../../adr/0004-synthetic-japanese-account-schema.md), [ADR-0010](../../adr/0010-personalized-account-tier-reasoning.md) | `src/core_banking/service.py` |
| **03** | `REQ-FUN-003` | [AI対話・RAG機能要件定義書](02_functional/03_ai_and_rag_functional.md) | Bedrock Nova Lite, Titan v2 | [ADR-0002](../../adr/0002-aws-bedrock-nova-lite-model-selection.md), [ADR-0003](../../adr/0003-rakuten-bank-faq-rag-pipeline.md) | `src/rag/`, `src/llm/` |
| **04** | `REQ-FUN-004` | [勘定系連携・トランザクション要件書](02_functional/04_core_banking_integration.md) | 銀行法第13条 (Read-Only) | [ADR-0004](../../adr/0004-synthetic-japanese-account-schema.md), [ADR-0008](../../adr/0008-decoupled-core-banking-database-and-api.md) | `src/core_banking/` |
| **05** | `REQ-FUN-005` | [認証・認可・セッション管理要件書](02_functional/05_auth_and_session.md) | NIST SP 800-63B, Step-Up | [ADR-0014](../../adr/0014-zero-trust-step-up-authentication-boundary.md) | `src/backend/auth.py` |
| **06** | `REQ-FUN-006` | [UI/UX・画面表示要件定義書](02_functional/06_frontend_and_uiux.md) | JIS X 8341-3 AA, W3C SSE | [ADR-0013](../../adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) | `src/frontend/` |
| **07** | `REQ-NFR-007` | [IPA準拠 非機能要件定義書](03_non_functional/07_non_functional_requirements.md) | IPA非機能要求グレード (99.95%) | [ADR-0007](../../adr/0007-production-aws-detailed-design-specification.md), [ADR-0011](../../adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) | `Dockerfile`, ECS |
| **08** | `REQ-SEC-008` | [個人情報保護法 (APPI) 準拠要件書](04_security_and_compliance/08_appi_pii_dlp_requirements.md) | APPI 第20条/23条, PIIトークン化 | [ADR-0001](../../adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0012](../../adr/0012-in-vpc-salted-tokenization-vault.md) | `src/control_plane/` |
| **09** | `REQ-SEC-009` | [金融庁・金商法コンプライアンス要件書](04_security_and_compliance/09_fsa_and_legal_compliance.md) | 金商法第38条 (投資助言禁止) | [ADR-0009](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md) | `output_guardrail.py` |
| **10** | `REQ-SEC-010` | [FISC安全対策基準 適合性要件書](04_security_and_compliance/10_fisc_security_standards.md) | FISC 第9版 (東京限定/KMS AES-256) | [ADR-0005](../../adr/0005-hybrid-cloud-and-aws-poc-architecture.md), [ADR-0017](../../adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) | KMS / IAM / S3 Lock |
| **11** | `REQ-SEC-011` | [敵対的攻撃防御・ガードレール要件書](04_security_and_compliance/11_prompt_injection_defense.md) | OWASP Top 10 for LLM | [ADR-0001](../../adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0009](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md) | `input_guardrail.py` |
| **12** | `REQ-AI-012`  | [AIプロンプト・銀行敬語ペルソナ定義書](05_ai_and_data/12_prompt_and_banking_persona.md) | 文化庁「敬語の指針」 | [ADR-0001](../../adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0002](../../adr/0002-aws-bedrock-nova-lite-model-selection.md) | `bedrock_nova.py` |
| **13** | `REQ-AI-013`  | [AIモデル評価・グラウンディング判定基準書](05_ai_and_data/13_grounding_and_evaluation.md) | ISO/IEC 42001 (Grounding > 0.85) | [ADR-0009](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md) | `output_guardrail.py` |
| **14** | `REQ-DAT-014` | [データモデル・スキーマ定義書](05_ai_and_data/14_data_models_and_schemas.md) | 全銀協フォーマット, JSON Schema | [ADR-0004](../../adr/0004-synthetic-japanese-account-schema.md) | `src/core_banking/db` |
| **15** | `REQ-IF-015`  | [API・外部インターフェース仕様書](06_interfaces/15_api_specifications.md) | OpenAPI 3.1, W3C SSE | [ADR-0008](../../adr/0008-decoupled-core-banking-database-and-api.md), [ADR-0013](../../adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) | `src/backend/app.py` |
| **16** | `REQ-IF-016`  | [エラーハンドリング・縮退運用要件書](06_interfaces/16_fallback_and_circuit_breaker.md) | FISC障害対策, サーキットブレーカー | [ADR-0008](../../adr/0008-decoupled-core-banking-database-and-api.md), [ADR-0019](../../adr/0019-local-llm-provider-and-fallback-architecture.md) | `local_llm.py` |
| **17** | `REQ-OPS-017` | [インフラストラクチャ・IaC要件書](07_operations_and_infra/17_infrastructure_iac_requirements.md) | 3層VPC, Terraform 100% | [ADR-0007](../../adr/0007-production-aws-detailed-design-specification.md), [ADR-0016](../../adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md) | Terraform Modules |
| **18** | `REQ-OPS-018` | [監査ログ・証跡管理・運用監視要件書](07_operations_and_infra/18_audit_logging_and_monitoring.md) | S3 WORM 10年, SHA-256改ざん検知 | [ADR-0009](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0018](../../adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) | `audit_logger.py` |
