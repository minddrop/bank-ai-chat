# 邦客大手銀行 AIカスタマーアシスタント（AWS本番アーキテクチャ）

[![Language: English](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![Language: 日本語](https://img.shields.io/badge/Language-日本語-red.svg)](README_JA.md)

> **言語切り替え / Language Switch**: [English](README.md) | [日本語 (Japanese)](README_JA.md)

本プロジェクトは、AWS東京リージョン（`ap-northeast-1`）上に構築された、日本の個人向けデジタルバンキング顧客対応用のエンタープライズAIチャットシステムです。Amazon Bedrock (Amazon Nova Lite `amazon.nova-lite-v1:0`)、Amazon OpenSearch ServiceによるRAG検索、およびIn-VPCデュアルコントロールプレーンアーキテクチャを活用しています。

---

## 🌟 主な機能と特徴

1. **銀行員としての高度な敬語・丁寧語対応**
   - 信頼性の高い顧客対応を実現するため、自然で丁寧な日本語敬語（丁寧語・尊敬語・謙譲語）で一貫して応答します。

2. **In-VPC デュアルコントロールプレーン（入力＆出力ガードレール）**
   - **入力ガードレール**: 個人情報保護法（APPI）に基づき、7桁の口座番号、顧客氏名（カタカナ・漢字）、店番号、暗証番号、電話番号等の個人情報（PII）をプロンプト構築前に自動マスキング。プロンプトインジェクション攻撃を防御します。
   - **出力ガードレール**: 検索結果（RAG context）に対するグラウンディングスコアの検証、金融商品取引法・金融庁ガイドラインに基づく個別の投資助言・銘柄推奨の厳格な制限、法的な免責事項の自動付加を行います。

3. **RAGナレッジベース＆コアバンキング合成データ連携**
   - 楽天銀行のFAQデータベース等を活用した実用的なFAQ自動検索エンジン（RAG）を搭載。
   - 勘定系コアバンキング（普通預金、定期預金、外貨預金、直近取引明細）の合成口座データ参照に対応。

4. **FISC安全対策基準準拠のセキュリティ＆改ざん防止監査**
   - AWS KMS (AES-256) 暗号化、S3 Object Lock、およびSHA-256ハッシュ署名付きの改ざん防止監査ログをAWS東京リージョン内に保持。

---

## 📁 ディレクトリ構造

```
bank-ai-chat/
├── GEMINI.md                         # ガバナンス・アーキテクチャ規定・開発ガイドライン
├── README.md                         # 英語版 README（プライマリ）
├── README_JA.md                      # 日本語版 README
├── data/                             # 合成口座データ & FAQデータセット
├── docs/                             # AWSアーキテクチャ・詳細設計書・CI/CD・コスト試算・ADR
│   └── adr/                          # 建築決定記録 (Architectural Decision Records)
├── scripts/                          # FAQクローラー & データベース初期化スクリプト
├── src/                              # バックエンド・コントロールプレーン・勘定系・フロントエンド・LLM・RAG
└── tests/                            # ガードレール・RAG・スキーマ検証用自動テスト
```

---

## 🚀 セットアップとローカル起動方法

### 事前準備
- Python 3.10 以上
- [`uv`](https://docs.astral.sh/uv/)（高速Pythonパッケージ＆環境マネージャー）
- （任意）ローカルLLM推論用の Ollama や LM Studio (例: `ollama pull qwen2.5:0.5b`)

### インストール
1. リポジトリのクローンおよび `uv` による依存関係の同期:
   ```bash
   uv sync
   ```

### 💻 ローカルアプリケーションの起動 (`uv` 使用)

#### モード A: ローカルLLMプロバイダー（オフライン開発・AWSコスト0円推奨）
AWS認証情報なしで `uv` を使用して起動します。Ollamaが稼働していれば自動連携し、未起動の場合は組み込みの「ローカル開発ライトエンジン」に自動フォールバックします:
```bash
# ローカルLLMプロバイダー用の環境変数を設定
export LLM_PROVIDER=local
export LOCAL_LLM_MODEL=qwen2.5:0.5b   # 任意: qwen2.5:0.5b, qwen2.5:1.5b, gemma:2b
export LOCAL_LLM_URL=http://localhost:11434/v1 # 任意: Ollama/LM Studio エンドポイント

# uv を使用したバックエンドサーバーの起動
uv run python3 src/backend/app.py
```

#### モード B: AWS Bedrock プロバイダーモード（本番プレビュー）
AWS東京リージョン（`ap-northeast-1`）の Amazon Bedrock (`amazon.nova-lite-v1:0`) と連携して `uv` で起動します（有効なAWS IAM認証情報が必要です）:
```bash
export LLM_PROVIDER=bedrock
uv run python3 src/backend/app.py
```

#### モード C: 標準ライブラリ HTTP サーバー（外部フレームワークなし）
FastAPIを使わずに標準ライブラリの軽量HTTPサーバーを `uv` で起動することも可能です:
```bash
uv run python3 src/backend/server.py
```

#### モード D: コンテナ化スタック（Docker & Docker Compose）
Dockerコンテナ上でアプリケーションスタックを構築・起動します（AWS ECS Fargateトポロジのエミュレーション）:
```bash
docker-compose up --build
```


### 🌐 Webフロントエンド画面の表示
サーバー起動後、ブラウザで以下のURLにアクセスします:
**`http://localhost:8000`**

アクセスすると、以下の機能を備えたインタラクティブなバンキングAIポータル画面が起動します:
- 丁寧な日本語敬語（丁寧語）で応答するAIチャット
- 顧客プロフィールの切り替えデモ（`山田 太郎`、`佐藤 花子` 等）
- In-VPC コントロールプレーン リアルタイム監視ダッシュボード（入力/出力ガードレールステータス、グラウンディングスコアメーター、改ざん防止監査ログビューア）

### 🧪 自動テストとコンプライアンス検証の実行 (`uv` 使用)
コントロールプレーン、RAG検索、LLMプロバイダーの自動テストを `uv` で実行します:
```bash
uv run pytest
# または unittest discover:
uv run python3 -m unittest discover -s tests
# ローカルLLM動作検証スクリプトの実行:
uv run python3 scripts/setup_local_llm.py
```

---

## ⚖️ 関連規制・セキュリティ基準

- **個人情報保護法 (APPI)**: LLMモデルエンドポイントへの生のPII流出を完全遮断。
- **金融庁 (FSA) AIガイドライン & 金融商品取引法 (FIEA)**: 回答の根拠（Grounding）検証および投資助言行為の禁止。
- **FISC安全対策基準**: 改ざん防止監査ログおよびKMS暗号化の適用。
- **グローバル金融基準適合**: **PCI-DSS 4.0**、**GLBA**、**CFPB AI指導原則**、**SR 11-7**、**ISO 42001/AIUC-1**、**NYDFS Part 500** に対するトレサビリティを網羅。[セキュリティ・コンプライアンス要件定義書](docs/requirements/04_security_and_compliance/08_appi_pii_dlp_requirements.md) および [ADR 0009](docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) を参照。
- **コンピュート・アーキテクチャ & ストリーミングガバナンス**: AWS ECS FargateとAWS Lambdaの比較評価を実施し、SSEストリーミング応答の無中断提供、API Gatewayの29秒タイムアウト制限回避、コールドスタート排除、および3層VPC FISC安全対策基準への適合を検証。[ADR 0011](docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) および [ADR 0013](docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) を参照。
- **In-VPC PIIソルト付きトークン化 & ステップアップ認証境界**: 個人情報保護法に基づくPIIトークン化ヴォールト ([ADR 0012](docs/adr/0012-in-vpc-salted-tokenization-vault.md)) および 銀行法に基づくトランザクション型操作のステップアップ認証境界 ([ADR 0014](docs/adr/0014-zero-trust-step-up-authentication-boundary.md))。
- **インフラストラクチャコード化 & 本番運用準備**: OpenSearch Serverlessネットワーク隔離・1024次元Titan v2標準化 ([ADR 0015](docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md))、Terraform IaCリモートステート管理 ([ADR 0016](docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md))、最小権限IAMロール設計 ([ADR 0017](docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md))、本番CloudWatch監視アラート目標 ([ADR 0018](docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md))、およびローカルLLMプロバイダー＆開発用フォールバック構成 ([ADR 0019](docs/adr/0019-local-llm-provider-and-fallback-architecture.md))。詳細は [要件定義書体系ポータル (18ドキュメント)](docs/requirements/README.md) を参照。


---

## 📝 ドキュメント運用方針 (Documentation Policy)

[`GEMINI.md`](GEMINI.md) の規定に基づき、**英語 (`README.md`) と日本語 (`README_JA.md`) の2言語によるドキュメント維持管理は README ファイル限定で適用**されます。その他の内部ドキュメントおよびADRは規定の標準言語で管理されます。

