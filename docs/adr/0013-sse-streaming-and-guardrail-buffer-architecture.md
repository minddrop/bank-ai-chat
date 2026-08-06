# ADR 0013: Server-Sent Events (SSE) Protocol and Guardrail Streaming Architecture

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Technical Architect, Senior Lead Engineer, Banking UX Lead

---

## Context & Problem Statement

Retail banking customers expect real-time, low-latency responsiveness when interacting with an AI Customer Assistant. Amazon Bedrock Nova Lite (`amazon.nova-lite-v1:0`) generates responses token-by-token. However, Japanese financial compliance standards (FSA Guidelines, FIEA Article 38, FISC Security Standards) require that AI outputs undergo **Output Guardrail Verification**—including NLI entailment grounding verification (ensuring answers are grounded in Rakuten Bank FAQ context with score >= 0.85), FIEA investment advice screening, and mandatory legal disclaimer appends (`【重要事項・免責事項】`).

We must establish an HTTP Server-Sent Events (SSE) streaming protocol and dynamic output buffering mechanism that delivers real-time token rendering to the customer UI without violating security control boundaries or timing out under proxy limits.

---

## Decision Drivers

1. **Low Time-To-First-Token (TTFT)**: Deliver initial tokens to customer browsers within < 350ms (P95).
2. **Evasion of Proxy Timeouts**: Avoid the 29-second hard proxy timeout imposed by AWS API Gateway and ALB default idle timeouts.
3. **Outbound Guardrail Enforcement**: Validate generated outputs against NLI grounding entailment thresholds before completing session state.
4. **Structured Client Event Protocols**: Provide clear, deterministic event channels (`event: metadata`, `event: token`, `event: guardrail`, `event: done`, `event: error`).

---

## Considered Options

1. **ALB + FastAPI ECS Fargate Server-Sent Events (SSE) with Sliding Window Output Guardrail (Chosen Option)**:
   - Use native HTTP/1.1 and HTTP/2 SSE streaming over continuous ALB connections.
   - Stream tokens immediately to the client as `event: token` frames while maintaining a sliding text buffer in Fargate memory.
   - Run Output Guardrail evaluation asynchronously over the accumulated text, emitting an `event: guardrail` status frame prior to `event: done`.
2. **Synchronous Full-Response Buffering**:
   - Wait for Bedrock to complete generating the full response, execute Output Guardrails, then return a single JSON HTTP 200 payload.
   - *Drawback*: Destroys real-time UX, pushing Time-To-First-Token from 350ms to 2.5s–4s.
3. **WebSockets (Bi-directional Protocol)**:
   - Full duplex WebSocket connection for chat interactions.
   - *Drawback*: Adds complex connection state management and ALB stickiness overhead without providing benefits over unidirectional SSE for simple chat streaming.

---

## Decision Outcome

Chosen Option: **Option 1 (ALB + FastAPI SSE with Sliding Window Output Guardrail)**.

### SSE Protocol & Packet Structure:

| Event Type | Packet Payload Description | Example Payload Data |
|---|---|---|
| `event: metadata` | Emitted immediately after input guardrail validation | `{"session_id": "...", "pii_masked": true}` |
| `event: token` | Real-time text token delta from Bedrock | `{"delta": "ヤマダ タロウ様、"}` |
| `event: guardrail` | Post-generation NLI grounding & disclaimer status | `{"grounding_score": 0.96, "disclaimer_appended": true}` |
| `event: done` | End of stream signal with total metrics | `{"status": "COMPLETED", "latency_ms": 520}` |
| `event: error` | Standardized error payload | `{"code": "ERR-LLM-003", "message": "..."}` |
| `:ping` | Heartbeat keep-alive frame sent every 15s | `:ping` |

---

## Consequences

### Positive:
- **Superior UX**: First token arrives in < 350ms (P95), delivering fluid Japanese typing animation.
- **Robust Against Timeouts**: `:ping` heartbeats and ALB 300s idle timeout configuration eliminate proxy drops.
- **Strict Compliance**: The client UI holds final rendering authorization until receiving `event: guardrail` verification.

### Negative / Risks:
- **Client Processing Responsibility**: Customer browser applications must implement proper EventSource / fetch stream handlers to parse multi-event SSE streams cleanly.
