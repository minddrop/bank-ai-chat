# ADR 0019: Local LLM Provider & Local Light Development Engine Architecture

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Lead AI Architect, Principal Software Engineer, Security & Compliance Lead

---

## Context & Problem Statement

Development and automated integration testing of the Japanese Major Bank AI Customer Assistant system traditionally required active connections to AWS Bedrock (`amazon.nova-lite-v1:0`) in `ap-northeast-1`. 

However, forcing developers to rely exclusively on AWS Bedrock for local offline coding, frontend UI iteration, prompt pipeline debugging, and CI/CD unit testing creates several challenges:
1. **Cloud Dependency & Cost**: Local testing generates unnecessary AWS API cost and requires developer workstations to hold live AWS IAM credentials.
2. **Offline Workflow**: Developers working without Internet access or AWS sandbox connectivity cannot run the local backend server (`src/backend/app.py` or `src/backend/server.py`).
3. **Test Automation Speed**: Remote API calls introduce network latency and external rate-limiting into automated unit tests.

We require a lightweight, zero-cloud-dependency **Local LLM Development Environment** that integrates seamlessly into the existing control planes and backend service stack while maintaining strict compliance isolation.

---

## Decision Drivers

1. **Developer Velocity & Offline Capability**: Ability to start and test the full application stack (`app.py`, control planes, RAG vector search, core banking APIs) without AWS credentials or Internet connectivity.
2. **Standard API Parity**: Identical client interfaces (`generate_response`) and data formats (`text`, `model`, `provider`, `latency_ms`, `tokens`) across AWS Bedrock (`BedrockNovaLiteClient`) and Local LLM (`LocalLLMClient`).
3. **Zero Security/Guardrail Compromise**: The In-VPC Control Plane (Input Guardrail PII scrubbing, Prompt Injection filtering, Output Guardrail grounding verification, and FISC Audit Logger) MUST execute with 100% functional parity regardless of the underlying LLM provider.
4. **Zero Production Risk**: Guarantee that local LLM libraries and configurations are used **EXCLUSIVELY** for developer environments and unit tests, and can NEVER leak into production AWS ECS Fargate deployments.

---

## Considered Options

1. **Require Live AWS Credentials for All Development Environments**:
   - Force developers to configure AWS SSO/IAM credentials and run against live Bedrock endpoints for all local work.
   - *Drawback*: High friction, network dependency, cost accumulation, and inability to work offline.

2. **Static Mock Responses in Backend Handlers**:
   - Hardcode static JSON responses inside FastAPI endpoints when running locally.
   - *Drawback*: Lacks dynamic reasoning, context synthesis, prompt testing capability, and realistic guardrail evaluation.

3. **Dual Provider Strategy with Local LLM Client & Local Light Development Engine Fallback (Chosen Option)**:
   - Introduce `LocalLLMClient` (`src/llm/local_llm.py`) supporting local LLM HTTP endpoints (e.g. Ollama `qwen2.5:0.5b`, `qwen2.5:1.5b`, `gemma:2b` via `/v1/chat/completions`).
   - Include an internal **Local Light Development Engine** fallback that emulates high-fidelity Japanese banking responses offline without any third-party model server running.
   - Unify client instantiation using an environment variable (`LLM_PROVIDER=local` vs default `LLM_PROVIDER=bedrock`).

---

## Decision Outcome

Chosen Option: **Option 3 (Dual Provider Strategy with Local LLM Client & Local Light Development Engine Fallback)**.

### Architecture Topology & Execution Matrix

```
                          ┌───────────────────────────────────────────────┐
                          │         FastAPI Backend Application           │
                          │   (src/backend/app.py / server.py)            │
                          └──────────────────────┬────────────────────────┘
                                                 │
                                         get_llm_client()
                                                 │
                        ┌────────────────────────┴────────────────────────┐
                        │                                                 │
                        ▼                                                 ▼
            [ LLM_PROVIDER=bedrock ]                           [ LLM_PROVIDER=local ]
         ┌──────────────────────────────┐                   ┌──────────────────────────────┐
         │     BedrockNovaLiteClient    │                   │        LocalLLMClient        │
         │  (amazon.nova-lite-v1:0)     │                   │  (src/llm/local_llm.py)      │
         └──────────────┬───────────────┘                   └──────────────┬───────────────┘
                        │                                                  │
                        ▼                                                  ├──────────────────────────┐
            AWS Bedrock Endpoint                                           ▼                          ▼
         (ap-northeast-1 FISC Prod)                               Local LLM Server             Local Development
                                                                  (Ollama / vLLM)             Light Engine (Offline)
                                                                 http://localhost:11434       (Zero dependency)
```

---

## Consequences

### Positive:
- **Zero Cloud Friction**: Developers can run `LLM_PROVIDER=local python3 src/backend/app.py` and test full chat and control plane workflows without AWS credentials.
- **Fast Unit Testing**: Automated test suites (`tests/test_local_llm.py`, `tests/test_guardrails.py`) execute in milliseconds locally.
- **Guardrail Verification Parity**: Input Guardrail (PII masking), Output Guardrail (grounding verification), and FISC Audit Logger operate identically across all LLM providers.
- **Clear Production Isolation**: Production AWS ECS Fargate tasks enforce `LLM_PROVIDER=bedrock` via environment variables and IAM role restrictions.

### Negative / Risks:
- **Model Divergence**: Local light models (e.g. `0.5B` / `1.5B`) have different context window sizes and reasoning capabilities compared to `Amazon Nova Lite`.
- **Developer Documentation Overhead**: Requires documentation maintenance across dual-language READMEs and RDs to clearly separate local dev instructions from production deployment specs.
