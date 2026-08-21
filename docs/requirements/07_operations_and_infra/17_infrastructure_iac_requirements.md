# [REQ-OPS-017] インフラストラクチャ・IaC要件定義書 (Infrastructure & IaC Requirements)
## 日本のメガバンク AIカスタマーアシスタント システム要件定義

- **文書番号**: REQ-OPS-017
- **版数**: 第1.0版 (2026-08-21)
- **対象システム**: Bank AI Chat Assistant (AWS Tokyo `ap-northeast-1`)
- **準拠規格**:
  - FISC安全対策基準 第9版「クラウド基盤安全管理」
  - CIS AWS Foundations Benchmark v3.0
  - AWS Well-Architected Framework
- **関連ADR**:
  - [ADR-0007: Production AWS Detailed Design Specification](../../adr/0007-production-aws-detailed-design-specification.md)
  - [ADR-0016: Deterministic Terraform IaC Architecture & Remote State Management](../../adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md)
- **ベースライン文書**: 
  - [`docs/aws_architecture.md`](../aws_architecture.md)
  - [`docs/aws_detailed_design_specification.md`](../aws_detailed_design_specification.md)
  - [`docs/cicd_pipeline.md`](../cicd_pipeline.md)
- **実装マッピング**:
  - Terraform IaC モジュール定義
  - [`Dockerfile`](file:///home/joe/src/bank-ai-chat/Dockerfile)

---

## 1. 3層VPCネットワーク構成仕様 (3-Tier VPC Architecture)

本システムは、AWS東京リージョン (`ap-northeast-1`) 内に **3層サブネット構造（Public / Private App / Isolated Data）** をMulti-AZ（`ap-northeast-1a`, `ap-northeast-1c`）で展開します。

```mermaid
graph TD
    subgraph VPC["AWS VPC (10.0.0.0/16) - Tokyo Region (ap-northeast-1)"]
        subgraph PUBLIC["Tier 1: Public Subnets (10.0.1.0/24, 10.0.2.0/24)"]
            ALB["Application Load Balancer (Dual-AZ / TLS 1.3 / WAF v2)"]
            NAT["NAT Gateways"]
        end

        subgraph PRIVATE_APP["Tier 2: Private App Subnets (10.0.11.0/24, 10.0.12.0/24)"]
            ECS_1["ECS Fargate Task (AZ-a)"]
            ECS_2["ECS Fargate Task (AZ-c)"]
        end

        subgraph ISOLATED_DATA["Tier 3: Isolated Data Subnets (10.0.21.0/24, 10.0.22.0/24)"]
            AOSS["Amazon OpenSearch Serverless (VPC Endpoint)"]
            S3_VPCE["Gateway VPC Endpoint (Amazon S3)"]
            KMS_VPCE["Interface VPC Endpoint (AWS KMS)"]
            BEDROCK_VPCE["Interface VPC Endpoint (Amazon Bedrock)"]
        end

        ALB -->|Port 8000 (Internal)| ECS_1 & ECS_2
        ECS_1 & ECS_2 --> AOSS & S3_VPCE & KMS_VPCE & BEDROCK_VPCE
    end
```

---

## 2. Terraform IaC設計規約 (ADR-0016準拠)

すべてのAWSリソースは100% Terraformコードとして管理され、AWSマネジメントコンソールからの手動変更（ClickOps）はSCP（Service Control Policy）で禁止されます。

### 2.1 リモートステート管理
- **State S3 Bucket**: `bank-ai-tfstate-apne1-prod` (AES-256暗号化、バージョン管理有効、パブリックアクセスブロック)
- **Lock DynamoDB Table**: `bank-ai-tflocks-prod` (排他ロックによる競合防止)

### 2.2 モジュールディレクトリ構造
```
terraform/
├── environments/
│   ├── dev/
│   ├── stg/
│   └── prod/
└── modules/
    ├── vpc/             # 3-Tier VPC, Subnets, Route Tables, NAT
    ├── security/        # Security Groups, KMS CMK, IAM Roles
    ├── ecs/             # ECS Cluster, Fargate Task Definition, Service
    ├── opensearch/      # OpenSearch Serverless Collection, Access Policies
    ├── alb/             # ALB, Target Groups, ACM Certificates
    └── waf/             # AWS WAF v2 Managed Rule Sets
```

---

## 3. CI/CD パイプライン要件 (`docs/cicd_pipeline.md` 準拠)

1. **プルリクエスト時（CI Gate）**:
   - `uv run pytest` による単体・結合テスト実行（全15テストパス必須）。
   - `trivy` によるコンテナ脆弱性スキャン（CRITICAL / HIGH 脆弱性ゼロ）。
   - `tfsec` / `tflint` によるIaCセキュリティチェック。
2. **本番デプロイ時（CD Gate）**:
   - ECRへのイミュータブルイメージプッシュ（SHA-256ダイジェスト指定）。
   - ECS FargateへのBlue/Greenローリングアップデート。

---

## 4. 受入テスト検証基準 (Acceptance Criteria)

- [x] `terraform plan` においてエラーおよび想定外のリソース差分が発生しないこと。
- [x] すべてのセキュリティグループが最小権限（Least Privilege）で厳格にポート制限されていること。
