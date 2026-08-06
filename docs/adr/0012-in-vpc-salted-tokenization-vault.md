# ADR 0012: In-VPC KMS CMK Salted Tokenization Vault for APPI Compliance

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Technical Architect, Lead Cybersecurity Architect, Compliance Officer

---

## Context & Problem Statement

Under Japan's Act on the Protection of Personal Information (APPI / 個人情報保護法), commercial banking applications cannot transmit raw Personally Identifiable Information (PII)—such as 7-digit account numbers (`\d{7}`), Katakana/Kanji customer names, branch codes (`\d{3}`), passwords/PINs, or phone numbers—to external LLM model endpoints or third-party cloud services.

In our AWS architecture for the Japanese Major Bank AI Customer Assistant, user inputs pass through an In-VPC Dual Control Plane prior to invoking Amazon Bedrock (Nova Lite `amazon.nova-lite-v1:0`). We require a deterministic, secure mechanism to intercept, redact, and tokenize PII within private VPC subnets (`10.100.0.0/16`), allowing the AI assistant to perform reasoning over token placeholders (`[ACCOUNT_MASKED: a1b2c3d4]`) while retaining the capability to safely re-hydrate or present responses to end-users without exposing unencrypted customer PII outside the VPC boundary.

---

## Decision Drivers

1. **APPI Zero-Leakage Compliance**: Guarantee 0% raw PII transmission to Amazon Bedrock or CloudWatch log streams.
2. **Cryptographic Salted Determinism**: Prevent rainbow table attacks on 7-digit account numbers or Katakana names by combining customer-specific context with an AWS KMS Customer Managed Key (CMK) secret salt.
3. **Low Latency Overhead**: PII regex detection and token vault storage must add < 45ms (P95) latency to the input guardrail execution pipeline.
4. **Tamper-Evident Ephemeral Lifecycle**: Token mappings must exist ephemerally in-memory during session execution with automated TTL expiration (15 minutes).

---

## Considered Options

1. **In-VPC Salted KMS CMK Tokenization Vault (Chosen Option)**:
   - Perform regex-based PII matching and unicode normalization in FastAPI ECS Fargate tasks.
   - Compute salted HMAC-SHA256 digests (`HMAC-SHA256(KMS_CMK_Salt, Raw_PII)`) truncated to an 8-character hex token (`[ACCOUNT_MASKED: a1b2c3d4]`).
   - Store temporary token-to-PII mapping in an encrypted in-memory LRU cache / Redis TTL table backed by AWS KMS CMK.
2. **Static One-Way Masking without Vaulting**:
   - Replace matching PII patterns with static generic placeholders (e.g. `[口座番号保護: XXXXXXX]`).
   - *Drawback*: Information loss prevents contextual re-hydration or multi-turn reasoning on multiple distinct account entities.
3. **AWS Comprehend Medical / Standard PII Entity Detection**:
   - Out-of-VPC API calls to AWS Comprehend for entity detection.
   - *Drawback*: Fails Japanese commercial banking regex precision for 7-digit account numbers and adds 150ms+ external network latency.

---

## Decision Outcome

Chosen Option: **Option 1 (In-VPC Salted KMS CMK Tokenization Vault)**.

### Architectural Rules & Implementation Principles:

1. **Pre-Ingestion PII Extraction**:
   - Inbound HTTP prompts are normalized (Unicode NFC, zero-width space `U+200B` stripped).
   - Regex engines scan for 7-digit account numbers (`^\d{7}$`), 3-digit branch codes (`^\d{3}$`), phone numbers, and Katakana/Kanji customer names.

2. **KMS CMK Salted Token Generation**:
   - Deterministic token format: `[CATEGORY_MASKED: <8-char-hex-hash>]`.
   - Token mapping stored in-memory within private app subnets, bound to `X-Session-ID`, and assigned a hard 15-minute TTL.

3. **Output Re-hydration Guardrail**:
   - Before response chunks are returned via Server-Sent Events (SSE), the outbound control plane scans for generated tokens and safely restores or masks them based on customer session authorization.

---

## Consequences

### Positive:
- **100% APPI Compliance**: Raw PII never leaves the VPC boundary or enters Bedrock prompt context.
- **Entity Identity Preserved**: Multi-turn dialogue can distinguish between multiple masked accounts or names via distinct token hashes.
- **Fast Execution**: In-memory token mapping achieves < 15ms P50 latency.

### Negative / Risks:
- **Stateful Memory Management**: Ephemeral token mappings require container memory management or Redis synchronization across multi-AZ ECS Fargate tasks.
