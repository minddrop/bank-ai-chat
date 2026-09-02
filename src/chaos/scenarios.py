"""
Chaos Engineering Scenarios & Failure Mode Definitions
Compliant with FISC Safety Standards (FISC安全対策基準 第9版 コンティンジェンシープラン策定基準)
and AWS Well-Architected Framework Reliability Pillar.
"""

import enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


class FailureCategory(enum.Enum):
    """Categorization of failure injection domains."""
    CORE_BANKING = "CORE_BANKING"
    LLM_INFERENCE = "LLM_INFERENCE"
    RAG_KNOWLEDGE = "RAG_KNOWLEDGE"
    CONTROL_PLANE = "CONTROL_PLANE"
    INFRASTRUCTURE = "INFRASTRUCTURE"


class DegradationStrategy(enum.Enum):
    """Expected architectural behavior under injected failure."""
    FAIL_CLOSED = "FAIL_CLOSED"          # Security/compliance must reject or block
    GRACEFUL_DEGRADE = "GRACEFUL_DEGRADE"  # Intelligence/enrichment fallback
    BUFFER_AND_RETRY = "BUFFER_AND_RETRY"  # Non-blocking async queueing


@dataclass
class ChaosScenarioDefinition:
    """Specification of a chaos experiment scenario."""
    scenario_id: str
    name_ja: str
    name_en: str
    category: FailureCategory
    target_component: str
    strategy: DegradationStrategy
    description: str
    default_latency_ms: int = 0
    failure_rate: float = 1.0
    fisc_reference: str = "FISC-Contingency-Std-9"
    parameters: Dict[str, Any] = field(default_factory=dict)


class ChaosScenario(enum.Enum):
    """Supported Chaos Experiment Scenarios."""
    # 1. Core Banking (勘定系) Failures
    CORE_BANKING_TIMEOUT = "CORE_BANKING_TIMEOUT"
    CORE_BANKING_DB_CRASH = "CORE_BANKING_DB_CRASH"
    CORE_BANKING_CIRCUIT_TRIP = "CORE_BANKING_CIRCUIT_TRIP"

    # 2. LLM Inference (Bedrock / AI推論) Failures
    BEDROCK_429_THROTTLING = "BEDROCK_429_THROTTLING"
    BEDROCK_OUTAGE_500 = "BEDROCK_OUTAGE_500"
    BEDROCK_LATENCY_SPIKE = "BEDROCK_LATENCY_SPIKE"

    # 3. RAG / Vector Store (FAQナレッジベース) Failures
    RAG_OPENSEARCH_TIMEOUT = "RAG_OPENSEARCH_TIMEOUT"
    RAG_INDEX_CORRUPT = "RAG_INDEX_CORRUPT"

    # 4. Security & Control Plane (監査・ガードレール) Failures
    AUDIT_STORAGE_FAILURE = "AUDIT_STORAGE_FAILURE"
    GUARDRAIL_LATENCY_SPIKE = "GUARDRAIL_LATENCY_SPIKE"

    # 5. Infrastructure & Network (コンテナ・通信) Failures
    AZ_PARTITION = "AZ_PARTITION"
    HIGH_CONCURRENCY_SPIKE = "HIGH_CONCURRENCY_SPIKE"


# Catalog of scenario specifications
SCENARIO_CATALOG: Dict[ChaosScenario, ChaosScenarioDefinition] = {
    ChaosScenario.CORE_BANKING_TIMEOUT: ChaosScenarioDefinition(
        scenario_id="CORE_BANKING_TIMEOUT",
        name_ja="勘定系API応答遅延（1.5秒タイムアウト超過）",
        name_en="Core Banking API Latency Spike (>1.5s FISC Timeout)",
        category=FailureCategory.CORE_BANKING,
        target_component="core_banking.client.CoreBankingClient",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="勘定系APIへの問い合わせがFISC基準の1.5秒を超過した場合に、回路遮断（サーキットブレーカー）が作動し、縮退メッセージ（残高以外の照会継続）が正常に返却されるかを検証。",
        default_latency_ms=2000,
        fisc_reference="FISC安全対策基準 実効性あるコンティンジェンシープラン策定基準 §4.1 (勘定系接続冗長化)"
    ),
    ChaosScenario.CORE_BANKING_DB_CRASH: ChaosScenarioDefinition(
        scenario_id="CORE_BANKING_DB_CRASH",
        name_ja="勘定系データベース接続断（503異常）",
        name_en="Core Banking DB Connection Refused (503 Service Unavailable)",
        category=FailureCategory.CORE_BANKING,
        target_component="core_banking.service.CoreBankingService",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="勘定系DBへの接続が瞬断・拒否された場合に、キャッシュTTL内の直前データ再利用または縮退メンテナンス案内が返却され、システム全体が連鎖停止しないかを検証。",
        fisc_reference="FISC安全対策基準 システム信頼性・キャパシティ管理基準 §2.3 (データベース障害時隔離)"
    ),
    ChaosScenario.CORE_BANKING_CIRCUIT_TRIP: ChaosScenarioDefinition(
        scenario_id="CORE_BANKING_CIRCUIT_TRIP",
        name_ja="サーキットブレーカー強制OPEN状態",
        name_en="Forced Circuit Breaker OPEN State",
        category=FailureCategory.CORE_BANKING,
        target_component="core_banking.client.CircuitBreaker",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="連続3回のエラーにより回路がOPENになった際、勘定系への追加通信を即時遮断（Fail Fast）し、バックエンドリソースの枯渇を防ぐかを検証。",
        fisc_reference="FISC安全対策基準 システム信頼性・キャパシティ管理基準 §3.2 (過負荷遮断機構)"
    ),
    ChaosScenario.BEDROCK_429_THROTTLING: ChaosScenarioDefinition(
        scenario_id="BEDROCK_429_THROTTLING",
        name_ja="Amazon Bedrock API 429レート制限（ThrottlingException）",
        name_en="Amazon Bedrock 429 Rate Limiting (ThrottlingException)",
        category=FailureCategory.LLM_INFERENCE,
        target_component="llm.bedrock_nova.BedrockNovaLiteClient",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="ピーク時のBedrock割当上限超過（HTTP 429）をシミュレートし、指数バックオフ再試行およびローカル軽量推論エンジンへの自動フェイルオーバーが機能するかを検証。",
        fisc_reference="FISC安全対策基準 クラウド利用基準 §5.2 (マネージドAIサービス割当制限対策)"
    ),
    ChaosScenario.BEDROCK_OUTAGE_500: ChaosScenarioDefinition(
        scenario_id="BEDROCK_OUTAGE_500",
        name_ja="Amazon Bedrock リージョン障害・500内部エラー",
        name_en="Amazon Bedrock Regional Service Outage (HTTP 500/503)",
        category=FailureCategory.LLM_INFERENCE,
        target_component="llm.bedrock_nova.BedrockNovaLiteClient",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="Bedrockサービス停止時に、内部スタックトレースを顧客へ漏洩させず、安全かつ丁寧な日本語の案内メッセージ（電話窓口案内付き）を返却できるかを検証。",
        fisc_reference="FISC安全対策基準 コンティンジェンシープラン策定基準 §6.1 (外部AI基盤全系障害時対応)"
    ),
    ChaosScenario.BEDROCK_LATENCY_SPIKE: ChaosScenarioDefinition(
        scenario_id="BEDROCK_LATENCY_SPIKE",
        name_ja="Bedrock推論遅延（P95 2,000ms超過）",
        name_en="Bedrock Inference Latency Spike (>2000ms)",
        category=FailureCategory.LLM_INFERENCE,
        target_component="llm.bedrock_nova.BedrockNovaLiteClient",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="LLM推論が極端に遅延した場合のSSEストリーミング接続維持およびタイムアウトハンドリングを検証。",
        default_latency_ms=3000,
        fisc_reference="非機能要求グレード §2.1 (レイテンシSLA上限監視)"
    ),
    ChaosScenario.RAG_OPENSEARCH_TIMEOUT: ChaosScenarioDefinition(
        scenario_id="RAG_OPENSEARCH_TIMEOUT",
        name_ja="OpenSearch Serverless ベクトル検索タイムアウト",
        name_en="OpenSearch Serverless Vector Store Timeout",
        category=FailureCategory.RAG_KNOWLEDGE,
        target_component="rag.vector_store.VectorStore",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="ベクトル検索がタイムアウトした場合に、キーワード一致への自動縮退、あるいは一般的な口座案内への切り替えが行われるかを検証。",
        fisc_reference="非機能要求グレード §2.1 Phase 2 SLA (ベクトル検索縮退)"
    ),
    ChaosScenario.RAG_INDEX_CORRUPT: ChaosScenarioDefinition(
        scenario_id="RAG_INDEX_CORRUPT",
        name_ja="FAQナレッジインデックス破損・空応答",
        name_en="FAQ Knowledge Index Data Corruption / Empty Retrieval",
        category=FailureCategory.RAG_KNOWLEDGE,
        target_component="rag.vector_store.VectorStore",
        strategy=DegradationStrategy.FAIL_CLOSED,
        description="検索結果が空または破損した際に、Output Guardrail（根拠度スコア判定）が未根拠出力を阻止（Grounding Score < 0.85）し、誤情報を顧客へ提供しないかを検証。",
        fisc_reference="金融庁AI活用指針 §3.1 (ハルシネーション・誤情報抑止)"
    ),
    ChaosScenario.AUDIT_STORAGE_FAILURE: ChaosScenarioDefinition(
        scenario_id="AUDIT_STORAGE_FAILURE",
        name_ja="FISC監査ログストレージ書込障害（S3/Disk不可）",
        name_en="FISC Audit Logger Storage Write Failure",
        category=FailureCategory.CONTROL_PLANE,
        target_component="control_plane.audit_logger.AuditLogger",
        strategy=DegradationStrategy.BUFFER_AND_RETRY,
        description="監査ログ保存先（S3 WORM）が一時利用不可となった際、コンテナ内リングバッファに安全にキューイングされ、復旧時に自動再送されるか（満杯時はFail-Closed遮断）を検証。",
        fisc_reference="FISC安全対策基準 監査追跡性基準 §7.1 (監査ログ保全性保証)"
    ),
    ChaosScenario.GUARDRAIL_LATENCY_SPIKE: ChaosScenarioDefinition(
        scenario_id="GUARDRAIL_LATENCY_SPIKE",
        name_ja="Input Guardrail PIIスキャン遅延（100ms超過）",
        name_en="Input Guardrail Latency Spike (>100ms)",
        category=FailureCategory.CONTROL_PLANE,
        target_component="control_plane.input_guardrail.InputGuardrail",
        strategy=DegradationStrategy.FAIL_CLOSED,
        description="複雑な正規表現や入力過負荷によるReDoS発生時、100msでFail-Closed遮断し、PII漏洩をゼロに保つかを検証。",
        default_latency_ms=250,
        fisc_reference="個人情報保護法 (APPI) 準拠管理 §2.1"
    ),
    ChaosScenario.AZ_PARTITION: ChaosScenarioDefinition(
        scenario_id="AZ_PARTITION",
        name_ja="AWS東京 Single AZ遮断（ap-northeast-1a障害）",
        name_en="AWS Tokyo Single AZ Outage Simulation (ap-northeast-1a)",
        category=FailureCategory.INFRASTRUCTURE,
        target_component="aws.ecs.fargate",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="1つのAZのタスク群を遮断した場合に、ALBヘルスチェックにより生き残りAZ（ap-northeast-1c）へゼロダウンタイムでトラフィックが迂回されるかを検証。",
        fisc_reference="FISC安全対策基準 システム信頼性基準 §1.1 (Multi-AZ冗長化)"
    ),
    ChaosScenario.HIGH_CONCURRENCY_SPIKE: ChaosScenarioDefinition(
        scenario_id="HIGH_CONCURRENCY_SPIKE",
        name_ja="五十日・給与振込日 スパイク負荷（1,000 TPS突発）",
        name_en="High Concurrency Spike (1,000 TPS Flash Traffic)",
        category=FailureCategory.INFRASTRUCTURE,
        target_component="aws.ecs.fargate.autoscaling",
        strategy=DegradationStrategy.GRACEFUL_DEGRADE,
        description="急激なアクセス集中時に、ECS Step-ScalingおよびCore Bankingキャッシュがリソース枯渇を防ぐかを検証。",
        fisc_reference="非機能要求グレード §1 (ピークスループット1000TPS耐性)"
    ),
}
