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
- **実装マッピング**:
  - Terraform IaC モジュール定義
  - [`Dockerfile`](file:///home/joe/src/bank-ai-chat/Dockerfile)

---

## 1. 3層VPCネットワーク構成仕様 (3-Tier VPC Architecture)

本システムは、AWS東京リージョン (`ap-northeast-1`) 内に **3層サブネット構造（Public / Private App / Isolated Data）** をMulti-AZ（`ap-northeast-1a`, `ap-northeast-1c`）で展開します。

```mermaid
graph TD
    subgraph VPC["AWS VPC (10.100.0.0/16) - Tokyo Region (ap-northeast-1)"]
        subgraph PUBLIC["Tier 1: Public Subnets (10.100.1.0/24, 10.100.2.0/24)"]
            ALB["Application Load Balancer (Dual-AZ / TLS 1.3 / WAF v2)"]
            NAT["NAT Gateways (AZ-a, AZ-c)"]
        end

        subgraph PRIVATE_APP["Tier 2: Private App Subnets (10.100.11.0/24, 10.100.12.0/24)"]
            ECS_1["ECS Fargate Task (AZ-a)"]
            ECS_2["ECS Fargate Task (AZ-c)"]
        end

        subgraph ISOLATED_DATA["Tier 3: Isolated Data Subnets (10.100.21.0/24, 10.100.22.0/24)"]
            AOSS["Amazon OpenSearch Serverless (VPC Endpoint)"]
            S3_VPCE["Gateway VPC Endpoint (Amazon S3)"]
            KMS_VPCE["Interface VPC Endpoint (AWS KMS)"]
            BEDROCK_VPCE["Interface VPC Endpoint (Amazon Bedrock)"]
        end

        ALB -->|Port 8000 (Internal)| ECS_1 & ECS_2
        ECS_1 & ECS_2 --> AOSS & S3_VPCE & KMS_VPCE & BEDROCK_VPCE
    end
```

### 1.1 VPC IPv4 アドレス設計表 (Subnet Address Plan)

| サブネット論理名 | CIDRブロック | アベイラビリティゾーン | ルーティング・ゲートウェイ | 配置リソース |
|---|---|---|---|---|
| `public-subnet-1a` | `10.100.1.0/24` | `ap-northeast-1a` | Internet Gateway (IGW) | ALB (AZ-a), NAT Gateway-a |
| `public-subnet-1c` | `10.100.2.0/24` | `ap-northeast-1c` | Internet Gateway (IGW) | ALB (AZ-c), NAT Gateway-c |
| `app-private-subnet-1a` | `10.100.11.0/24` | `ap-northeast-1a` | NAT Gateway-a (Egress専用) | ECS Fargate Tasks (AZ-a) |
| `app-private-subnet-1c` | `10.100.12.0/24` | `ap-northeast-1c` | NAT Gateway-c (Egress専用) | ECS Fargate Tasks (AZ-c) |
| `data-isolated-subnet-1a`| `10.100.21.0/24` | `ap-northeast-1a` | 隔離 (No Internet Route) | AOSS, KMS, Bedrock VPCE |
| `data-isolated-subnet-1c`| `10.100.22.0/24` | `ap-northeast-1c` | 隔離 (No Internet Route) | AOSS, KMS, Bedrock VPCE |

### 1.2 セキュリティグループ通信制御マトリクス (Security Group Ingress/Egress)

| セキュリティグループ名 | 種別 | 通信方向 | 送信元 / 送信先 | プロトコル / ポート | 用途・認可理由 |
|---|---|---|---|---|---|
| `sg_bank_ai_alb` | Ingress | 受信 | `0.0.0.0/0` | TCP 443 (HTTPS) | エンドユーザーからのHTTPS通信 |
| `sg_bank_ai_alb` | Egress | 送信 | `sg_bank_ai_ecs` | TCP 8000 | ECSコンテナへのリバースプロキシ |
| `sg_bank_ai_ecs` | Ingress | 受信 | `sg_bank_ai_alb` | TCP 8000 | ALBからのリクエスト転送のみ許可 |
| `sg_bank_ai_ecs` | Egress | 送信 | `sg_bank_ai_vpce` | TCP 443 (HTTPS) | Bedrock / KMS / S3 VPCエンドポイント通信 |
| `sg_bank_ai_ecs` | Egress | 送信 | `sg_bank_ai_opensearch`| TCP 443 (HTTPS) | OpenSearch Serverlessクエリ |
| `sg_bank_ai_opensearch`| Ingress | 受信 | `sg_bank_ai_ecs` | TCP 443 (HTTPS) | ECSタスクからのベクトル検索のみ許可 |
| `sg_bank_ai_vpce` | Ingress | 受信 | `sg_bank_ai_ecs` | TCP 443 (HTTPS) | ECSタスクからのAWSサービスAPI呼出 |

---

## 2. Terraform IaC設計規約 & リソース仕様 (ADR-0016準拠)

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

### 2.3 ECS Fargate タスク定義仕様
- **Task CPU**: `2048` (2 vCPU)
- **Task Memory**: `4096` (4 GB)
- **Container Port**: `8000` (FastAPI / SSE streaming)
- **Health Check**: `curl -f http://localhost:8000/health || exit 1` (Interval: 15s, Timeout: 5s, Retries: 3)
- **IAM Task Role**: `BankAiEcsTaskRole` (KMS `kms:Decrypt`/`kms:GenerateDataKey`, Bedrock `bedrock:InvokeModelWithResponseStream`, AOSS `aoss:APIAccessAll` 最小権限)

### 2.4 OpenSearch Serverless & S3 監査バケットポリシー
- **暗号化ポリシー (`aoss-security-policy-encryption`)**: 専用KMS CMKによる保存時暗号化。
- **ネットワークポリシー (`aoss-security-policy-network`)**: `AllowFromPublic: false`、指定VPCエンドポイントからのみアクセス許可。
- **データアクセスポリシー (`aoss-access-policy`)**: `BankAiEcsTaskRole` に対するインデックスCRUD権限付与。
- **S3 監査バケットポリシー**: 非暗号化オブジェクトのPut拒否、および TLS 1.3 未満の接続拒否。

---

## 3. CI/CD パイプライン・品質ゲート & ライフサイクル管理要件

### 3.1 パイプラインステージ定義
1. **Stage 1: コード品質 & 単体テスト (CI Gate)**:
   - `uv run pytest` による単体・結合テスト実行（全15テストパス必須）。
2. **Stage 2: セキュリティ & 静的解析 (FISC/APPI Gate)**:
   - `bandit -r src/ -x tests/` によるPython SAST検査。
   - `trivy` によるコンテナ脆弱性スキャン（CRITICAL / HIGH 脆弱性ゼロ）。
   - `tfsec` / `tflint` によるIaCセキュリティチェック。
3. **Stage 3: マルチエンジンコンテナビルド & ECR登録**:
   - **GitHub Actions Native Docker**: 標準ランナーでの高速並行キャッシュビルド。
   - **AWS CodeBuild Privileged DinD (`bank-ai-image-builder`)**: Dockerデーモン非搭載環境またはVPC内隔離ビルド用のフォールバック。
   - ECRイミュータブルプッシュ（SHA-256ダイジェスト指定）。
4. **Stage 4: 本番デプロイ (CD Gate)**:
   - ECS FargateへのBlue/Greenローリングアップデート（無中断SSEストリーミング維持）。

### 3.2 自動リソース破棄・クリーンアップワークフロー (`undeploy.yml`)
一時検証環境やPRプレビュー環境のコスト最適化およびセキュリティ衛生のため、以下の順序で自動アンデプロイを実行：
1. App Runner削除 / ECS Fargateタスク数を0にスケールイン
2. 一時ECRイメージのパージ
3. S3ビルドステージングバケットの空化および削除
4. 一時デプロイ用IAMロールのデタッチおよび削除

---

## 4. 受入テスト検証基準 (Acceptance Criteria)

- [x] `terraform plan` においてエラーおよび想定外のリソース差分が発生しないこと。
- [x] すべてのセキュリティグループが最小権限（Least Privilege）で厳格にポート制限されていること。
- [x] CI/CDパイプラインにおいて全15テストおよびセキュリティスキャンがパスすること。
