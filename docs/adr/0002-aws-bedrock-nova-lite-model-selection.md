# ADR 0002: AWS Bedrock & Amazon Nova Lite Model Selection

* **Status**: Accepted
* **Date**: 2026-08-04
* **Deciders**: AI Bank Engineering Team, Cloud Infrastructure Lead

## Context & Problem Statement
The AI Customer Assistant requires a modern LLM that supports fluent, polite Japanese business language (敬語・丁寧語), delivers low latency for interactive chat, ensures data sovereignty within Japan, and minimizes operational token cost.

## Decision Drivers
* Native support for Japanese language nuance and banking customer service tone.
* Compliance with FISC data residency requirements (AWS Tokyo region `ap-northeast-1`).
* Cost efficiency for high-volume customer service queries.
* Enterprise security guarantees (no customer data used for model fine-tuning).

## Considered Options
1. OpenAI GPT-4o via US endpoints (Rejected - Violates FISC in-country data processing guidelines).
2. Amazon Bedrock - Claude 3.5 Sonnet (Considered - High quality but higher cost for simple FAQ/account queries).
3. Amazon Bedrock - Amazon Nova Lite (`amazon.nova-lite-v1:0`) (Chosen).

## Decision Outcome
Chosen Option: **Option 3 (Amazon Bedrock - Amazon Nova Lite)**.

### Rationale:
* **Cost & Speed**: Amazon Nova Lite offers extremely low latency and low token costs, ideal for high-concurrency banking support.
* **Compliance**: Fully hosted on Amazon Bedrock in Tokyo (`ap-northeast-1`), guaranteeing FISC data sovereignty.
* **Fallback & Emulator**: A Bedrock-compatible local mock provider is provided in dev/test environments when cloud API credentials are not active.

## Consequences
* **Positive**: Fast response times, low operational cost, complete alignment with Japanese regulatory requirements.
* **Negative**: Requires system prompt optimization to ensure strict adherence to Japanese banking etiquette.
