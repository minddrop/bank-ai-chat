# [REQ-NFR-007] IPA非機能要求グレード準拠 非機能要件定義書 (Non-Functional Requirements)
## 日本のメガバンク AIカスタマーアシスタント システム要件定義

- **文書番号**: REQ-NFR-007
- **版数**: 第1.0版 (2026-08-21)
- **対象システム**: Bank AI Chat Assistant (AWS Tokyo `ap-northeast-1`)
- **準拠規格**:
  - 独立行政法人情報処理推進機構 (IPA)「非機能要求グレード（2018年版）」
  - FISC安全対策基準 第9版「システム信頼性・キャパシティ管理基準」
  - AWS Well-Architected Framework (信頼性の柱・パフォーマンス効率の柱)
- **関連ADR**:
  - [ADR-0007: Production AWS Detailed Design Specification](../../adr/0007-production-aws-detailed-design-specification.md)
  - [ADR-0011: Compute Architecture Re-evaluation (ECS vs Lambda)](../../adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md)
  - [ADR-0022: Cross-Region DR, Fault Tolerance & Main Banking Independence](../../adr/0022-cross-region-disaster-recovery-and-fault-tolerance-architecture.md)
- **実装マッピング**:
  - [`Dockerfile`](file:///home/joe/src/bank-ai-chat/Dockerfile)
  - [`docker-compose.yml`](file:///home/joe/src/bank-ai-chat/docker-compose.yml)
  - [`terraform/environments/prod/`](file:///home/joe/src/bank-ai-chat/terraform/environments/prod/)

---

## 1. IPA非機能要求グレード 6大メジャードメイン要件

```mermaid
mindmap
  root((IPA 非機能要求))
    可用性
      稼働率 99.95%
      Multi-AZ 冗長化
      国内DR (AWS Osaka ap-northeast-3)
      目標復旧時間 RTO < 15分 (地域災害時)
      目標復旧時点 RPO < 1分 (地域災害時) / RPO = 0 (通常時)
    性能・拡張性
      通常 50 TPS / ピーク 1,000 TPS
      P95 応答時間 < 2.0秒
      初回SSEトークン < 800ms
      ECS Fargate オートスケーリング
    運用・保守性
      Blue/Green 無停止デプロイ
      ヘルスチェック自動復旧 (Liveness / Readiness 分離)
      年次BCP災害復旧訓練 & カオス工学
    移行性
      合成データによる事前検証
      東京・大阪リージョン IaC 互換
    セキュリティ
      FISC適合 / APPI準拠
      KMS AES-256 / TLS 1.3
      S3 WORM 10年保存 & CRR
    システム環境
      AWS Tokyo (Primary) / AWS Osaka (Secondary DR)
      3層VPC完全隔離
```

---

## 2. 詳細非機能仕様マトリクス

| ドメイン | 項目 | 目標仕様値 | 実装アーキテクチャ & 根拠 (ADR-0022準拠) |
|---|---|---|---|
| **可用性** | 月間サービス稼働率 | **99.95% 以上** | Dual-AZ ECS Fargate、ALB、Multi-AZ OpenSearch Serverless |
| **可用性 (AZ)** | AZ障害時復旧目標 | **RTO < 1分 / RPO = 0** | Dual-AZ自動フェイルオーバー、ALBターゲットグループ即時切替 |
| **可用性 (DR)** | 広域広域災害復旧目標 (DR) | **RTO < 15分 / RPO < 1分** | **AWS大阪 (`ap-northeast-3`)** パイロットライト待機、Route 53 ARC切替 |
| **可用性 (勘定系)**| 勘定系停止時可用性 | **RTO = 0 (即時縮退)** | 3ステート・サーキットブレーカーによるFAQ継続提供 (無停止) |
| **データ保全** | 監査ログ損失目標 (RPO) | **RPO = 0** (即時永続化) | S3 Object Lock (COMPLIANCE) & 大阪リージョン非同期CRR複製 |
| **性能** | 定常スループット | **50 TPS** | 2 vCPU, 4GB RAM x 2タスク構成 |
| **性能** | ピークスループット | **1,000 TPS** | CPU使用率 70% トリガーによる最大10タスク自動スケールアウト |
| **性能** | エンドツーエンドP95応答時間 | **2.0 秒未満** (目標 630 ms) | Amazon Nova Lite高速推論 & 最適化インメモリベクトル検索 |
| **性能** | 初回SSEトークン描画遅延 | **800 ms 未満** | チャンクバッファリング最適化 (ADR-0013) |
| **運用性** | デプロイ方式 | **Blue/Green 無停止デプロイ** | AWS CodeDeploy / ECSローリングアップデート (Zero Downtime) |
| **保守性** | コンテナ起動時間 | **10秒以内 (Zero Cold Start)** | 常時起動Fargateコンテナ (Lambdaのコールドスタート問題を回避) |
| **環境** | データ主権 (Sovereignty) | **日本国内限定 (東京・大阪)** | FISC基準に基づき海外リージョン移転禁止、国内完結DR |

### 2.1 マイクロサービス別レイテンシ予算配分表 (P95 $630\text{ ms}$ Target)

| 処理フェーズ | 対象コンポーネント | P50 目標 | P95 上限 | フェイルセーフ動作 (Failure Mode) |
|---|---|---|---|---|
| **Phase 1: Inbound DLP** | 正規表現 + PIIトークン化 + Injection検知 | 15 ms | **45 ms** | **FAIL CLOSED**: 100msタイムアウト時遮断 |
| **Phase 2: RAG Retrieval** | OpenSearch Serverless ベクトル検索 | 40 ms | **85 ms** | **DEGRADE**: キーワード完全一致へ自動縮退 |
| **Phase 3: LLM Inference** | Bedrock Nova Lite (`ap-northeast-1`) TTFT | 250 ms | **450 ms** | **DEGRADE**: ローカル軽量推論へフォールバック |
| **Phase 4: Outbound DLP** | Grounding判定 + PII漏洩検知 + 金商法スキャン | 20 ms | **50 ms** | **FAIL CLOSED**: スコア<0.85時出力破棄 |
| **Phase 5: FISC Audit Logger** | 非同期SHA-256署名 & S3/CloudWatch送信 | 5 ms | **12 ms (非同期)** | **BUFFER**: コンテナ内キューに蓄積し再送 |
| **合計クライアントSLA** | エンドツーエンド全経路 | **360 ms** | **630 ms** (P99: 1,045 ms) | |

---

## 3. ECS Fargate コンピュート & オートスケーリング最適化 (ADR-0011準拠)

AWS Lambda（サーバレス）ではなく **AWS ECS Fargate（コンテナ）** を採用することにより、以下の非機能的優位性を達成します：
1. **ストリーミング長寿命コネクションの保証**: API Gatewayの29秒ハードリミットを回避し、ALB経由で安定した長文SSEストリーミングを完走。
2. **コールドスタートの完全排除**: 金融取引において致命的な初回アクセス時の遅延（5〜10秒）をゼロ化。
3. **In-VPCコントロールプレーンの高速ローカル実行**: Python正規表現エンジンおよびトークン化ヴォールトを同一コンテナメモリ内でナノ秒単位で実行。

### 3.1 ECS Step-Scaling Policy 詳細仕様
- **Target Tracking Policy**: 平均CPU使用率 70% を維持（最小 2 タスク、最大 10 タスク）。
- **Step-Scaling Trigger 1 (急増時)**: CPU使用率が 70% を超過し60秒継続時、即座に `+3 タスク` 追加。
- **Step-Scaling Trigger 2 (スパイク時)**: CPU使用率が 85% を超過時、即座に `+5 タスク` を追加し急激なトラフィック集中（五十日・給与振込日）を吸収。
- **Scale-in Cooldown**: 300秒（不要なタスク頻繁破棄・スラッシングを防止）。

### 3.2 障害・災害レベル別 SLA & 復旧自動化マトリクス (ADR-0022準拠)

| 障害Tier | 対象・障害シナリオ | 目標復旧時間 (RTO) | 目標復旧時点 (RPO) | 自動アクション / 運用手順 |
|---|---|---|---|---|
| **Tier 1: プロセス障害** | 個別ECSタスク異常終了 | **< 30秒** | RPO = 0 | ECSサービスによるタスク自動再起動、ALB正常確認 |
| **Tier 2: 勘定系停止** | 勘定系API遅延・メンテナンス | **即時 (0秒)** | RPO = 0 | 3ステート・サーキットブレーカー作動、FAQ縮退案内へ移行 |
| **Tier 3: 単一AZ障害** | 東京1a AZ全損 / 瞬断 | **< 1分** | RPO = 0 | ALBターゲットグループによる生存AZ (1c) への自動切替 |
| **Tier 4: モデル遅延** | Bedrock Nova Lite スロットリング | **即時 (0秒)** | RPO = 0 | In-VPC Local LLM / ルールベース推論エンジンへの自動切替 |
| **Tier 5: 地域災害 (DR)** | 東京リージョン全損 (大規模地震等) | **< 15分** | **< 1分** | Route 53 ARC切替、**AWS大阪 (`ap-northeast-3`)** パイロットライト昇格 |

### 3.3 FISC安全対策基準 適合 BCP災害訓練 & カオス工学検証基準

1. **年次BCP災害復旧訓練 (FISC第9版 5.3項)**:
   - 最低年1回、東京リージョンからのトラフィック遮断および大阪DR環境へのRoute 53 ARCフェイルオーバー訓練を実施し、RTO < 15分が達成されることを記録・監査証跡化。
2. **AWS Fault Injection Simulator (FIS) カオス試験**:
   - ステージング環境において、勘定系通信遅延（1,500ms超）およびパケット損失を人工的に注入し、サーキットブレーカーが正しく `OPEN` に遷移することをCIゲートで定期検証。

---

## 4. 受入テスト検証基準 (Acceptance Criteria)

- [x] 負荷テスト（Locust / JMeter）において、100 TPS負荷下でのP95レスポンスタイムが2.0秒以内であること。
- [x] いずれか1つのアベイラビリティゾーン（AZ）を意図的に遮断した場合でも、サービス断なく対話が継続できること。
- [x] 勘定系APIタイムアウト時に即座にサーキットブレーカーが作動し、FAQ回答が継続できること (`tests/test_circuit_breaker.py`)。
- [x] 東京リージョン遮断シナリオにおいて、大阪リージョン（`ap-northeast-3`）へのフェイルオーバー手順およびS3 WORM監査ログCRR複製が確認されていること。
- [x] カオスエンジニアリング自動検証スイート（`tests/test_chaos_engineering.py`）により、勘定系障害・Bedrock 429・監査ログストレージ障害時の定常状態不変条件（Zero PII、RFC 7807、署名保全）が100%パスすること。

---

## 5. カオスエンジニアリング検証仕様 & 不変条件 (Chaos Engineering Specifications)

FISC安全対策基準 第9版「実効性あるコンティンジェンシープラン策定基準」に基づき、以下の不変条件（Steady-State Invariants）をカオス条件下で常時検証します：

| 不変条件 (Invariant) | 準拠法令・基準 | 判定基準 | 障害時の振る舞い |
|---|---|---|---|
| **Zero PII Leakage** | 個人情報保護法 (APPI) 第23条 | 顧客口座番号（7桁）・暗証番号・氏名漏洩ゼロ | 障害時も必ずマスキングトークン化または遮断 |
| **RFC 7807 Error Standard** | RFC 7807 / REQ-IF-015 | 内部スタックトレースやファイルパスの露出ゼロ | `application/problem+json` 形式で安全な通知 |
| **Audit Trail Integrity** | FISC監査基準 §7.1 | SHA-256改ざん検知署名生成率 100% | ストレージ障害時はメモリ内バッファ（1,000件）へ退避 |
| **Circuit Breaker Trip** | FISCシステム信頼性基準 §3.2 | 勘定系連続3回失敗または1.5sタイムアウト | 即時 `OPEN` 遷移し、二次障害（リソース枯渇）を防止 |
| **Graceful Degradation** | 金融庁AI活用指針 §3.1 | 口座照会不可時も一般FAQ案内を継続 | 「ただいまシステムメンテナンス中」の標準縮退文面付与 |

