# [REQ-IF-015] API・外部インターフェース仕様書 (API Specifications)
## 日本のメガバンク AIカスタマーアシスタント システム要件定義

- **文書番号**: REQ-IF-015
- **版数**: 第1.0版 (2026-08-21)
- **対象システム**: Bank AI Chat Assistant (AWS Tokyo `ap-northeast-1`)
- **準拠規格**:
  - OpenAPI Specification (OAS) 3.1.0
  - W3C Server-Sent Events (SSE) Protocol
  - RFC 7519 (JSON Web Token - JWT)
- **関連ADR**:
  - [ADR-0008: Decoupled Core Banking Database & API](../../adr/0008-decoupled-core-banking-database-and-api.md)
  - [ADR-0013: SSE Streaming & Guardrail Buffer Architecture](../../adr/0013-sse-streaming-and-guardrail-buffer-architecture.md)
- **ベースライン文書**: 
  - [`docs/requirements_definition.md`](../requirements_definition.md) (Sec 6)
  - [`docs/aws_architecture.md`](../aws_architecture.md)
- **実装マッピング**:
  - [`src/backend/app.py`](file:///home/joe/src/bank-ai-chat/src/backend/app.py)
  - [`src/backend/server.py`](file:///home/joe/src/bank-ai-chat/src/backend/server.py)

---

## 1. REST & Streaming エンドポイント一覧 (API Endpoints Overview)

| メソッド | パス | 説明 | 認証要否 | 戻り値形式 |
|---|---|---|---|---|
| `POST` | `/api/chat` | AIチャット対話エンドポイント (同期JSON返却) | ◯ (JWT) | `application/json` |
| `POST` | `/api/chat/stream` | AIチャット対話エンドポイント (リアルタイムSSE) | ◯ (JWT) | `text/event-stream` |
| `GET` | `/api/customers` | 顧客一覧取得 (シミュレーター・テスト用) | ◯ | `application/json` |
| `GET` | `/api/customers/{customer_id}` | 顧客プロファイル・口座残高照会 | ◯ | `application/json` |
| `GET` | `/api/transactions` | 直近取引明細一覧取得 | ◯ | `application/json` |
| `GET` | `/api/audit-logs` | 改ざん防止監査ログ一覧照会 | ◯ (Admin) | `application/json` |
| `POST` | `/api/step-up-auth` | ステップアップMFA要求検証・誘導 | ◯ | `application/json` |
| `GET` | `/api/health` | コンテナヘルスチェックエンドポイント | 不要 | `application/json` |

---

## 2. 主要エンドポイント詳細仕様 (OAS 3.1)

### 2.1 `/api/chat/stream` (SSEストリーミング)
- **Content-Type**: `application/json` (Request) / `text/event-stream` (Response)
- **Request Body**:
```json
{
  "session_id": "SESS-20260821-001",
  "customer_id": "CUST-0001",
  "message": "現在の普通預金残高と会員ランクを教えてください。"
}
```

- **SSE Stream Data Chunks**:
```text
data: {"type": "guardrail_status", "input_guardrail": {"allowed": true, "pii_scrubbed": []}}

data: {"type": "content_chunk", "delta": "山田 太郎様、"}

data: {"type": "content_chunk", "delta": "現在の普通預金残高は 2,450,000円でございます。"}

data: {"type": "content_chunk", "delta": "現在の会員ステージは「スーパーVIP」となっております。"}

data: {"type": "completion", "grounding_score": 0.98, "audit_id": "AUDIT-20260821-8899"}
```

---

### 2.2 `/api/chat` (同期JSON対話)
- **Response Payload**:
```json
{
  "session_id": "SESS-20260821-001",
  "customer_id": "CUST-0001",
  "response": "山田 太郎様、現在の普通預金残高は 2,450,000円でございます。\n現在の会員ステージは「スーパーVIP」となっております。\n\n---\n【重要事項・免責事項】\n※本AIアシスタントの回答は一般的な情報提供および操作案内に限られます。",
  "input_guardrail": {
    "allowed": true,
    "pii_detected": false,
    "pii_tokens_scrubbed": []
  },
  "output_guardrail": {
    "grounding_score": 0.98,
    "pii_leak_prevented": false,
    "financial_advice_blocked": false,
    "disclaimer_appended": true
  },
  "audit_log_id": "AUDIT-20260821-8899"
}
```

---

## 3. エラーコード定義 (Standard HTTP Error Codes)

| HTTPステータス | エラーコード | 説明 / 原因 |
|---|---|---|
| `400 Bad Request` | `INVALID_PAYLOAD` | 必須フィールド（`customer_id`, `message`）の欠落 |
| `401 Unauthorized` | `AUTH_EXPIRED` | JWTトークン期限切れ、または署名不一致 |
| `403 Forbidden` | `STEP_UP_REQUIRED` | チャット外でのMFA取引認証が必要な操作を検知 |
| `422 Unprocessable` | `SECURITY_BLOCKED` | プロンプトインジェクションまたは重大な規約違反 |
| `503 Service Unavailable` | `CORE_BANKING_TIMEOUT` | 勘定系ゲートウェイ応答遅延（サーキットブレーカー発火） |

---

## 4. 受入テスト検証基準 (Acceptance Criteria)

- [x] OpenAPI 3.1 仕様書に対し、FastAPIの自動生成 `/docs` スキーマが 100% 整合すること。
- [x] `/api/chat/stream` がストリーミング接続を中断することなく最後まで送信完了すること。
