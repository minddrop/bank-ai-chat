# ADR 0023: Chaos Engineering & Resilience Verification Framework

* **Status**: Accepted
* **Date**: 2026-09-02
* **Deciders**: Principal Resilience Architect, Chief Information Security Officer, Head of Site Reliability Engineering (SRE), Lead AI Architect

---

## Context & Problem Statement

The **Japanese Major Bank AI Customer Assistant** is a mission-critical digital banking system deployed in AWS Tokyo (`ap-northeast-1`). The system interacts with distributed downstream dependencies including:
1. **Core Banking System (勘定系)**: Customer balance and transaction extraction APIs.
2. **Amazon Bedrock (Amazon Nova Lite)**: Cloud generative AI inference.
3. **OpenSearch Serverless (AOSS)**: FAQ RAG vector search knowledge base.
4. **AWS KMS & S3 Object Lock**: Cryptographic audit logging with WORM retention.

Under **FISC Safety Standards 第9版 (コンティンジェンシープラン策定基準・システム信頼性管理基準)** and **Financial Services Agency (FSA / 金融庁) AI Guidelines**, financial institutions are required to prove system recoverability, verify failover mechanisms under turbulence, and ensure zero data leakage or corruption during service degradation.

Prior to this ADR, resilience was tested through static mocks and unit tests, leaving the application without a structured method to simulate real-world chaotic conditions (e.g. Bedrock 429 throttling spikes, Core Banking database outages, single-AZ loss in `ap-northeast-1`, and audit log storage backpressure).

---

## Decision Drivers

1. **FISC Contingency Plan Standard (実効性あるコンティンジェンシープラン策定基準)**: Deterministic verification of recovery objectives (RTO < 15 minutes, RPO = 0).
2. **Dual Failure Strategy (Fail-Closed vs Graceful Degradation)**:
   - **Security & Compliance Gates** (PII masking, Prompt Injection, FISC Audit Logger, Step-Up MFA) must **FAIL CLOSED** to prevent regulatory violations.
   - **Intelligence & Data Context** (Core Banking extraction, Bedrock inference, FAQ RAG) must **DEGRADE GRACEFULLY** to maintain 24/7 customer service without internal error exposure.
3. **APPI Compliance under Turbulence**: Invariant guarantee of **Zero PII Leakage** into client responses, logs, or external endpoints even during severe system turbulence.
4. **RFC 7807 Standard Error Consistency**: All chaotic failures must yield standardized `application/problem+json` error responses rather than unhandled 500 stack traces.
5. **Continuous CI/CD & Production Safety**: Safe, thread-safe, and context-isolated fault injection capabilities guarded by blast radius controls (`CHAOS_ENGINEERING_ENABLED`).

---

## Considered Options

1. **External Third-Party Chaos Tooling Only (Gremlin / Chaos Mesh)**:
   - Deploy external agents into ECS containers.
   - *Drawback*: Introduces non-FISC-compliant third-party agent software, requires out-of-VPC telemetry, and lacks semantic awareness of banking-specific primitives (e.g., In-VPC Token Vault, Bedrock rate limits, and Core Banking circuit breakers).
2. **Infra-Only AWS Fault Injection Service (AWS FIS) Without Application-Level Injection**:
   - Only test container termination and network blackholes.
   - *Drawback*: Fails to test application-level circuit breakers, in-memory retry buffers, Bedrock 429 throttling, or output grounding score degradation.
3. **Hybrid Chaos Engineering Framework with In-App Modular Fault Injection & AWS FIS Templates (Chosen Option)**:
   - Implement an In-VPC Python Chaos Subsystem (`src/chaos/`):
     - `FaultInjector`: Context-scoped latency, exception, and data corruption injection.
     - `SteadyStateEvaluator`: Automated verification of Zero-PII, RFC 7807 compliance, and latency SLA budgets.
     - `ChaosManager`: Experiment lifecycle management, GameDay execution, and reporting.
     - `ChaosMiddleware`: Header-activated (`X-Chaos-Scenario`) per-request chaos in test environments.
   - Resilient subsystem hardening: In-memory FIFO queue for AuditLogger (`BUFFER: コンテナ内キューに蓄積し再送`) and Bedrock fallback apology handling.
   - Infrastructure-level AWS FIS experiment templates (`terraform/modules/chaos/`, `docs/chaos/`).

---

## Decision Outcome

Chosen Option: **Option 3 (Hybrid Chaos Engineering Framework with In-App Modular Fault Injection & AWS FIS Templates)**.

### Architectural Execution Matrix:

```
                                 [ Incoming Client Request ]
                                              │
                                 ┌────────────▼────────────┐
                                 │     ChaosMiddleware     │ ◄── Inspects X-Chaos-Scenario
                                 └────────────┬────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
          [ Normal Production Flow ]                       [ Chaos Injected Context ]
                     │                                                 │
      ┌──────────────┴──────────────┐                   ┌──────────────┴──────────────┐
      │  In-VPC Control Planes      │                   │  FaultInjector Hook Active   │
      │  Core Banking API           │                   │  - Injects Latency / 503     │
      │  Bedrock Nova Lite          │                   │  - Trips Circuit Breaker     │
      │  FISC Audit Logger          │                   │  - Buffers Audit Logs        │
      └──────────────┬──────────────┘                   └──────────────┬──────────────┘
                     │                                                 │
                     └────────────────────────┬────────────────────────┘
                                              │
                                ┌─────────────▼─────────────┐
                                │   SteadyStateEvaluator    │
                                ├───────────────────────────┤
                                │ 1. Zero PII Leakage Check │
                                │ 2. RFC 7807 Error Format  │
                                │ 3. P95 Latency SLA Budget │
                                │ 4. Circuit Breaker State  │
                                └───────────────────────────┘
```

### Chaos Experiment Scenario Catalog:

| Scenario ID | Target Component | Strategy | FISC Reference | Expected Behavior |
|---|---|---|---|---|
| `CORE_BANKING_TIMEOUT` | `CoreBankingClient` | `GRACEFUL_DEGRADE` | FISC安全対策基準 コンティンジェンシー §4.1 | 1.5s timeout, circuit breaker records failure, returns degraded maintenance message. |
| `CORE_BANKING_DB_CRASH` | `CoreBankingService` | `GRACEFUL_DEGRADE` | FISC安全対策基準 システム信頼性 §2.3 | Connection refused, serves cached balances or degraded message without crashing. |
| `CORE_BANKING_CIRCUIT_TRIP` | `CircuitBreaker` | `GRACEFUL_DEGRADE` | FISC安全対策基準 システム信頼性 §3.2 | Circuit forced to OPEN, fast-fails requests without overwhelming core banking. |
| `BEDROCK_429_THROTTLING` | `BedrockNovaLiteClient` | `GRACEFUL_DEGRADE` | FISC安全対策基準 クラウド利用基準 §5.2 | ThrottlingException caught, fails over to local model or polite Japanese apology. |
| `BEDROCK_OUTAGE_500` | `BedrockNovaLiteClient` | `GRACEFUL_DEGRADE` | FISC安全対策基準 コンティンジェンシー §6.1 | Regional 500 outage, returns courteous Japanese apology with telephone banking hotline. |
| `RAG_OPENSEARCH_TIMEOUT` | `VectorStore` | `GRACEFUL_DEGRADE` | 非機能要求グレード §2.1 Phase 2 SLA | Vector search delay, falls back to keyword matching without request stall. |
| `RAG_INDEX_CORRUPT` | `VectorStore` | `FAIL_CLOSED` | 金融庁AI活用指針 §3.1 (ハルシネーション抑止) | Empty retrieval, Output Guardrail rejects ungrounded generation (<0.85). |
| `AUDIT_STORAGE_FAILURE` | `AuditLogger` | `BUFFER_AND_RETRY` | FISC安全対策基準 監査追跡性 §7.1 | In-memory FIFO queue buffers logs; buffer overflow triggers fail-closed safety. |
| `GUARDRAIL_LATENCY_SPIKE` | `InputGuardrail` | `FAIL_CLOSED` | 個人情報保護法 (APPI) 準拠管理 §2.1 | Slow regex/tokenization triggers 100ms deadline fail-closed. |
| `AZ_PARTITION` | `AWS ECS Fargate` | `GRACEFUL_DEGRADE` | FISC安全対策基準 システム信頼性 §1.1 | Single-AZ loss (`ap-northeast-1a`), ALB routes to healthy AZ (`ap-northeast-1c`). |

---

## Consequences

### Positive:
- **Provable Regulatory Resilience**: Meets FISC 9th Edition contingency verification requirements with automated test evidence (`tests/test_chaos_engineering.py`).
- **Zero PII Invariant Guarantee**: Continuous evaluation proves that customer personal data is never leaked under failure conditions.
- **Cascading Failure Prevention**: Circuit breakers and in-memory retry buffers insulate Core Banking and Audit logging from systemic failure.
- **Automated GameDay Execution**: SRE teams can run disaster recovery drills on-demand via REST endpoints (`/api/chaos/simulate`) or CLI script (`scripts/run_chaos_experiment.py`).

### Negative / Operational Considerations:
- **Blast Radius Protection**: Strict environment validation (`CHAOS_ENGINEERING_ENABLED`) is required to prevent accidental chaos injection in live production.
- **Monitoring Maintenance**: CloudWatch alarm thresholds (ADR-0018) must be calibrated to distinguish scheduled GameDay drills from genuine production incidents.
