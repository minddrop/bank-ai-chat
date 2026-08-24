# [REQ-SEC-010] FISC安全対策基準 適合性要件定義書 (FISC Security Standards)
## 日本のメガバンク AIカスタマーアシスタント システム要件定義

- **文書番号**: REQ-SEC-010
- **版数**: 第1.0版 (2026-08-21)
- **対象システム**: Bank AI Chat Assistant (AWS Tokyo `ap-northeast-1`)
- **準拠規格**:
  - 金融情報システムセンター (FISC)「金融機関等コンピュータシステムの安全対策基準・解説書（第9版）」
  - 金融庁「主要行等向けの総合的な監督指針」
  - ISO/IEC 27001 (ISMS) / ISO/IEC 27017 (クラウドセキュリティ)
- **関連ADR**:
  - [ADR-0005: Hybrid Cloud & AWS PoC Architecture](../../adr/0005-hybrid-cloud-and-aws-poc-architecture.md)
  - [ADR-0017: Enterprise IAM Least-Privilege Access & KMS Key Policy Topology](../../adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md)
- **実装マッピング**:
  - AWS IAM ECS TaskRole / ExecutionRole 設定
  - AWS KMS Customer Managed Keys (CMK)
  - Amazon S3 Object Lock (`COMPLIANCE` モード)

---

## 1. FISC安全対策基準 統制マッピング概要

金融情報システムセンター（FISC）第9版基準に基づく主要な統制項目と、本システムのAWSアーキテクチャ実装とのマッピングです。

| FISC統制項目 (統制番号) | FISC要求基準の要点 | 本システムの実装・適合仕様 (AWS Tokyo `ap-northeast-1`) |
|---|---|---|
| **統制項目 1.1: 設備安全・データ主権** | 重要データの国内リージョン保管および主権保護 | 全コンピュート (ECS)、ストレージ (S3/OpenSearch)、推論 (Bedrock) を **AWS東京リージョン (`ap-northeast-1`) に完全限定**。海外リージョンへのデータ越境移転をIAMおよびSCPで禁止。 |
| **統制項目 2.1: ネットワーク分離** | 多層防御および外部ネットワークからの分離 | **3層VPC構成 (Public ALB, Private ECS App, Isolated OpenSearch/DB)**。全通信はVPC Endpoint (AWS PrivateLink) 経由で完結し、パブリックインターネットを経由しない。 |
| **統制項目 3.2: データ暗号化 (保存時)** | 保管時データの高強度暗号化 | **AWS KMS CMK (AES-256)** による二重暗号化 (S3バケット暗号化、OpenSearch Serverless、DynamoDB/EFS)。年次キーローテーションを強制。 |
| **統制項目 3.3: データ暗号化 (転送時)** | 通信経路上での盗聴・改ざん防止 | ALBおよび内部マイクロサービス間通信において **TLS 1.3** を強制（弱い暗号スイート TLS 1.0/1.1/1.2 CBCは完全無効化）。 |
| **統制項目 4.1: アクセス制御・最小特権** | 特権ID管理および最小権限の原則 | **ECS TaskRole と ExecutionRole の分離**。推論用TaskRoleはBedrock `InvokeModelWithResponseStream` のみ許可、S3バケットへの直接アクセスは監査ロガー専用Roleのみに限定。 |
| **統制項目 5.3: ログ取得・改ざん防止** | 監査証跡の完全性および長期保管 | 監査ログは **Amazon S3 Object Lock (COMPLIANCEモード)** により 10年間削除・上書き禁止（WORM特性）。各ログエントリに **SHA-256 ハッシュ署名** を付与。 |

### 1.1 グローバル金融基準・国際規格適合マトリクス (Global Compliance Traceability)

| 規格・法規制フレームワーク | 対象条項・コントロール | システム実装アーキテクチャ & 防御仕様 | 検証方式・準拠ADR |
|---|---|---|---|
| **PCI-DSS 4.0** | Req 3.3/3.4 (PANマスク), Req 6.4 (Web防御), Req 10.2 (ログ完全性) | 16桁クレジットカード番号の正規表現検知・トークン化、WAF OWASPルール適用、SHA-256改ざん防止監査ログ。 | [ADR-0009](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **GLBA (米国グラム・リーチ・ブライリー法)** | § 314.4(c)(1) (NPI暗号化), § 314.4(e) (監査証跡) | 非公開個人情報 (NPI) のAWS KMS AES-256暗号化、ゼロトラストセッションコンテキスト分離。 | [ADR-0017](../../adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) |
| **CFPB AI ガイダンス** | 2023年ガイダンス (正確性・非欺瞞・有人エスカレーション) | NLIグラウンディング検証による幻覚防止、AIアシスタントの明示およびワンクリック有人エスカレーション。 | [ADR-0009](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md), [ADR-0010](../../adr/0010-personalized-account-tier-reasoning.md) |
| **SR 11-7 / OCC 2011-12** | モデルリスク管理 (概念的妥当性・結果分析) | CloudWatch Telemetryによるモデルドリフト、拒否率、ガードレール発動率、P95遅延の定常監視。 | [ADR-0018](../../adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| **ISO/IEC 42001 / AIUC-1** | A.6 (AI攻撃リスク), A.8 (検証), A.9 (挙動制限) | プロンプトインジェクション検知スキャナー、Unicode正規化、決定論的Fail-Closedサーキットブレーカー。 | [ADR-0001](../../adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0009](../../adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **NYDFS Part 500** | 500.06 (監査証跡), 500.12 (MFA), 500.15 (暗号化) | 10年間WORM保管監査ログ、重要取引境界におけるステップアップ認証、TLS 1.3/KMS暗号化。 | [ADR-0014](../../adr/0014-zero-trust-step-up-authentication-boundary.md), [ADR-0017](../../adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) |

---

## 2. ネットワークトポロジーと境界分離 (In-VPC Isolation)

```mermaid
graph TD
    INTERNET["インターネット / 顧客ブラウザ"] -->|TLS 1.3 (HTTPS)| ALB["Public Subnet: Application Load Balancer"]
    
    subgraph VPC["AWS VPC (10.0.0.0/16) - Tokyo Region (ap-northeast-1)"]
        ALB -->|HTTPS (Internal)| ECS["Private App Subnet: ECS Fargate Containers (Dual Control Plane)"]
        
        subgraph ISOLATED["Private Isolated Data Subnet"]
            VPCE_BEDROCK["VPC Endpoint: Amazon Bedrock"]
            VPCE_AOSS["VPC Endpoint: OpenSearch Serverless"]
            VPCE_S3["VPC Endpoint: Amazon S3"]
            VPCE_KMS["VPC Endpoint: AWS KMS"]
        end
        
        ECS --> VPCE_BEDROCK
        ECS --> VPCE_AOSS
        ECS --> VPCE_S3
        ECS --> VPCE_KMS
    end
```

---

## 3. 暗号鍵管理仕様 (AWS KMS CMK Key Policy)

1. **暗号化アルゴリズム**: AES-GCM 256-bit (FIPS 140-3 レベル3適合HSM)
2. **キーポリシー原則**:
   - ルートアカウントや管理者であっても、暗号化データの平文復号権限を直接付与しない（Separation of Duties）。
   - キーの年次自動ローテーション（Automatic Annual Rotation）を有効化。
3. **キー別用途定義**:
   - `alias/bank-ai-audit-log-key`: 監査ログS3バケット専用
   - `alias/bank-ai-vector-db-key`: OpenSearch Serverlessコレクション専用
   - `alias/bank-ai-token-vault-key`: In-VPC PIIソルト暗号化専用

---

## 4. 受入テスト検証基準 (Acceptance Criteria)

- [x] AWS Security Hub / AWS Config による FISC コンプライアンスパック評価スコア 100% 達成。
- [x] S3監査ログバケットに対し、管理者権限であってもオブジェクトの削除 (`s3:DeleteObject`) がS3 Object Lockにより拒絶されること。
- [x] 全外部エンドポイント通信がTLS 1.3のみを受理すること（SSL Labs A+ 判定）。
