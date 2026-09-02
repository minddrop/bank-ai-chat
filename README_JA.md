# 邦客大手銀行 AIカスタマーアシスタント（AWS本番アーキテクチャ）

[![Language: English](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![Language: 日本語](https://img.shields.io/badge/Language-日本語-red.svg)](README_JA.md)

> **言語切り替え / Language Switch**: [English](README.md) | [日本語 (Japanese)](README_JA.md)

本プロジェクトは、AWS東京リージョン（`ap-northeast-1`）上に構築された、日本の個人向けデジタルバンキング顧客対応用のエンタープライズAIチャットシステムです。Amazon Bedrock (Amazon Nova Lite `amazon.nova-lite-v1:0`)、Amazon OpenSearch ServiceによるRAG検索、In-VPCデュアルコントロールプレーンガードレール、高耐障害性の勘定系サーキットブレーカー、および決定論的Terraform IaC構成を活用しています。

---

## 🌟 主な機能と特徴

1. **銀行員としての高度な敬語・丁寧語対応**
   - 信頼性の高い顧客対応を実現するため、自然で丁寧な日本語敬語（丁寧語・尊敬語・謙譲語）で一貫して応答します。

2. **In-VPC デュアルコントロールプレーン（入力＆出力ガードレール）**
   - **入力ガードレール**: 個人情報保護法（APPI）に基づき、7桁の口座番号、顧客氏名（カタカナ・漢字）、店番号、暗証番号、電話番号等の個人情報（PII）をプロンプト構築前に自動マスキング。プロンプトインジェクションやジェイルブレイク攻撃を遮断します。
   - **出力ガードレール**: N-gram意味的含意によるグラウンディングスコア検証（REQ-AI-013）、金融商品取引法（金商法第38条）・金融庁ガイドラインに基づく個別の投資助言・銘柄推奨の厳格な制限、競合他行への言及抑止と自行サービスへの誘導、法的な免責事項の自動付加を行います。

3. **リアルタイム W3C Server-Sent Events (SSE) ストリーミング (REQ-IF-015, ADR-0013)**
   - サブセカンドの高速ストリーミングチャットエンドポイント（`POST /api/chat/stream`）を実装。コントロールプレーンのリアルタイム判定ステータス、タイピングチャンク、および完了テレメトリを順次配信します。

4. **ゼロトラスト認証＆ステップアップ多要素認証 (REQ-FUN-005, ADR-0014)**
   - RFC 7519準拠の純Python JWT認証エンジンを実装。KMS動的秘密鍵による署名検証、インメモリブラックリストによるトークン失効、および資金移動（振込・送金）・暗証番号変更・口座解約などの重要操作に対する自動ステップアップMFA誘導カード表示をサポートします。

5. **勘定系コアバンキングの耐障害性＆3ステート・サーキットブレーカー (REQ-FUN-004, ADR-0008)**
   - FISC安全対策基準に準拠した3ステート（`CLOSED`・`OPEN`・`HALF_OPEN`）サーキットブレーカーを搭載。60秒のインメモリキャッシュTTL、1.5秒の実行タイムアウト、および勘定系障害時の丁寧な日本語縮退案内（フォールバック）を自動実行します。

6. **決定論的 Infrastructure as Code (Terraform) (REQ-OPS-017, ADR-0016)**
   - マルチAZ 3層VPC（`10.100.0.0/16`）、AWS KMS CMK AES-256、最小特権IAMロール、OpenSearch Serverlessベクトルコレクション（1024次元 Titan v2）、TLS 1.3対応ALB、AWS WAF v2マネージドルール、ECS Fargateクラスターのモジュール構成を完備。

7. **FISC安全対策基準準拠のセキュリティ＆改ざん防止監査**
   - AWS KMS (AES-256) 暗号化、S3 Object Lock（10年WORM保持）、およびSHA-256ハッシュ署名付きの改ざん防止監査ログをAWS東京リージョン内に保持。

8. **広域ディザスタリカバリ (DR) ＆ 銀行本丸機能の非停止性保証 (REQ-OPS-017, ADR-0022)**
   - **ゼロ影響・完全疎結合保証**: AIチャットの全コンポーネントが完全停止・ハングアップした場合でも、銀行本体の振込・入出金・ATM・ネットバンキング取引機能は1ミリ秒も停止せず、0%の影響で正常稼働を継続します。
   - **国内完結型DRトポロジ (東京 $\rightarrow$ 大阪)**: FISC・個人情報保護法のデータ主権に基づき、国内地理的分散拠点として **AWS大阪 (`ap-northeast-3`)** パイロットライト待機、Route 53 ARC自動DNS切替、KMSマルチリージョンキー (`mrk-`)、およびS3 Cross-Region Replication (CRR) 非同期監査ログ複製を配備。

9. **カオスエンジニアリング＆FISCレジリエンス検証フレームワーク (FISC第9版, ADR-0023)**
   - **In-VPC 障害注入サブシステム (`src/chaos/`)**: 勘定系1.5秒タイムアウト、DB接続断、Amazon Bedrock 429レート制限・500リージョン障害、および監査ログストレージ障害時のインメモリバッファ退避を自動注入。
   - **定常状態不変条件（Steady-State Invariants）の常時評価**: 個人情報保護法（APPI）に基づくPII漏洩ゼロ、RFC 7807適合、およびSHA-256改ざん検知署名保全を自動検査。
   - **GameDay運用手順書＆AWS FIS連携**: 災害対策訓練手順書（`docs/operations/chaos_gameday_runbook.md`）、AWS Fault Injection Service (FIS) テンプレート（`terraform/modules/chaos/`, `docs/chaos/`）、およびCLI実行ツール（`scripts/run_chaos_experiment.py`）を完備。

---

## 📁 ディレクトリ構造

```
bank-ai-chat/
├── GEMINI.md                         # ガバナンス・アーキテクチャ規定・開発ガイドライン
├── README.md                         # 英語版 README（プライマリ）
├── README_JA.md                      # 日本語版 README
├── data/                             # 合成口座データ & FAQデータセット
├── docs/                             # AWSアーキテクチャ・詳細設計書・CI/CD・コスト試算・ADR
│   ├── adr/                          # 建築決定記録 (ADR-0001 - ADR-0023)
│   ├── chaos/                        # AWS Fault Injection Service (FIS) 実験テンプレート
│   ├── operations/                   # GameDay災害対策運用手順書 (chaos_gameday_runbook.md)
│   └── requirements/                 # エンタープライズ要件定義スイート (18仕様書)
├── scripts/                          # FAQクローラー & グラウンディング評価・カオスCLI
│   ├── evaluate_grounding.py         # 100件ゴールデンFAQデータセット評価スクリプト
│   └── run_chaos_experiment.py       # カオスエンジニアリング＆GameDay訓練実行CLI
├── src/                              # バックエンド・カオス・コントロールプレーン・勘定系・フロントエンド・LLM・RAG
│   ├── backend/                      # FastAPI, SSEストリーミング, JWT認証＆MFA, RFC 7807, カオスAPI
│   ├── chaos/                        # 障害注入エンジン, 不変条件評価, マネージャー, ミドルウェア
│   ├── control_plane/                # In-VPC 入出力ガードレール, ブランド保護, AML, 監査ログ
│   ├── core_banking/                 # 勘定系合成DB & サーキットブレーカー付き耐障害クライアント
│   ├── frontend/                     # シミュレータUI & 顧客ポータル (SSE & MFAカード対応)
│   ├── llm/                          # Bedrock Nova Lite & ローカルLLMエンジン (カオスフック付き)
│   └── rag/                          # 事前インデックス済みTF-IDF / OpenSearchベクトル検索
├── terraform/                        # 決定論的Terraform IaC構成スイート (REQ-OPS-017)
│   ├── environments/                 # 環境ルート定義 (dev, prod, dr-osaka) & S3リモートステート
│   └── modules/                      # 再利用可能モジュール (vpc, security, alb, waf, opensearch, ecs, chaos)
└── tests/                            # 76件の自動単体・統合・カオスレジリエンステストスイート
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

---

### 🌐 Webフロントエンド画面の表示
サーバー起動後、ブラウザで以下のURLにアクセスします:
- **シミュレータ＆コントロールプレーン監視**: **`http://localhost:8000`**
- **顧客専用ダイレクトバンキングポータル**: **`http://localhost:8000/user/`**

提供機能:
- W3C Server-Sent Events (SSE) によるリアルタイムタイピング配信
- 重要取引操作時の公式インターネットバンキング多要素認証（MFA）誘導カード
- 顧客プロフィールの切り替えデモ（`山田 太郎`、`佐藤 花子` 等）
- In-VPC コントロールプレーン監視ダッシュボード（入出力ガードレール状態、グラウンディング計器、FISC監査ログビューア）

---

### 🧪 自動テストの実行
コントロールプレーン、RAGエンジン、サーキットブレーカー、SSEストリーミング、およびカオス工学耐性を含む全76件の自動テストを実行します:
```bash
uv run pytest
# または仮想環境のpytest直接実行:
PYTHONPATH=src ./.venv/bin/pytest tests/ -v
```

### 🌪️ カオスエンジニアリング＆FISC耐障害性訓練の実行
計画的な障害注入訓練（GameDay）および定常状態不変条件の自動検証を実行します:
```bash
# 1. カオス工学自動テストスイートの実行（16テスト）
./.venv/bin/pytest tests/test_chaos_engineering.py -v

# 2. ローカルまたはステージング環境に対するGameDay訓練CLIの実行
./.venv/bin/python3 scripts/run_chaos_experiment.py --scenario all

# 3. カタログ化された全12のFISCカオスシナリオ一覧を表示
./.venv/bin/python3 scripts/run_chaos_experiment.py --list
```

### 📊 グラウンディング評価ベンチマークの実行 (REQ-AI-013)
100件のゴールデンFAQデータセットに対する自動評価ベンチマークを実行します:
```bash
./.venv/bin/python3 scripts/evaluate_grounding.py --limit 100
```

---

## ⚖️ 準拠法規制・セキュリティ基準

- **個人情報保護法（APPI）**: 外部LLMエンドポイントへの生PII送信ゼロポリシーを厳格遵守。
- **金融庁AIガイドライン＆金融商品取引法（金商法第38条）**: 自動グラウンディング検証および個別投資助言の禁止措置。
- **FISC安全対策基準（第9版）**: 改ざん防止監査証跡の保存、KMS暗号化、および3層VPC分離。
- **グローバル金融セキュリティ規格**: **PCI-DSS 4.0**, **GLBA**, **CFPB AI Guidance**, **SR 11-7**, **ISO 42001/AIUC-1**, **NYDFS Part 500** への完全なトレーサビリティを確保。詳細は [セキュリティ・コンプライアンス要件定義書](docs/requirements/04_security_and_compliance/08_appi_pii_dlp_requirements.md) および [ADR 0009](docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) を参照。
- **コンピュートアーキテクチャ＆ストリーミングガバナンス**: AWS ECS Fargate による非途絶SSE応答ストリーミング、29秒タイムアウト回避、コールドスタートゼロ、およびFISC準拠3層VPC統合。詳細は [ADR 0011](docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) および [ADR 0013](docs/adr/0013-sse-streaming-and-guardrail-buffer-architecture.md) を参照。
- **In-VPC Salted PII トークン化＆ステップアップ認証**: APPI準拠のPIIボールティング ([ADR 0012](docs/adr/0012-in-vpc-salted-tokenization-vault.md)) および銀行法第13条の2に基づく法的取引境界の確立 ([ADR 0014](docs/adr/0014-zero-trust-step-up-authentication-boundary.md))。
- **ブランド防衛・AML（マネロン防止）・スコープ制御**: 35以上の国内競合金融機関に対する言及抑止、犯罪収益移転防止法準拠のAML検知、およびプロンプトインジェクション防御 ([ADR 0020](docs/adr/0020-brand-protection-anti-financial-crime-and-scope-guardrails.md))。
- **決定論的インフラ構成と本番運用性**: OpenSearch Serverless ネットワーク分離ポリシー＆1024次元 Titan v2 ベクトル埋め込み ([ADR 0015](docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md))、決定論的Terraform IaCリモートステート管理 ([ADR 0016](docs/adr/0016-deterministic-terraform-iac-architecture-and-remote-state-management.md))、エンタープライズ最小特権IAMロール定義 ([ADR 0017](docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md))、および本番CloudWatchメトリクス・アラーム構成 ([ADR 0018](docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md))。全18件の要件仕様書は [エンタープライズ要件定義スイート一覧](docs/requirements/README.md) を参照。

---

## 📝 ドキュメント保守ポリシー

[`GEMINI.md`](GEMINI.md) に規定されている通り、**日英2言語（English / 日本語）によるドキュメントの同期保守は README ファイル（`README.md` および `README_JA.md`）に限定**されています。その他の内部設計書や ADR 群はそれぞれの指定言語にて管理されます。
