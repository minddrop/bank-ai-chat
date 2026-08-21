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
- **ベースライン文書**: 
  - [`docs/requirements_definition.md`](../requirements_definition.md) (Sec 2.3, 12)
  - [`docs/security_dlp_guardrails_requirements.md`](../security_dlp_guardrails_requirements.md) (Sec 4)
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
