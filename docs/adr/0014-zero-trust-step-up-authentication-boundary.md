# ADR 0014: Zero-Trust Step-Up Authentication Boundary for Banking Operations

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Technical Architect, Chief Risk Officer, Banking Act Legal Counsel

---

## Context & Problem Statement

Under the Japanese Banking Act (銀行法 - Ginkō Hō) and FSA regulatory guidelines, automated conversational AI systems operate strictly as **informational advisory tools**. They do not possess the legal authorization or authentication strength to execute binding core banking transactions—such as fund transfers (`振込・送金`), loan disbursements (`カードローン借入`), PIN modifications (`暗証番号変更`), or account closures (`口座解約`)—directly within an unauthenticated or standard session chat interface.

We must formally define the Zero-Trust architectural boundary separating **informational AI assistant interactions** (permitted in conversational chat) from **actionable banking operations** (prohibited in chat, requiring step-up Multi-Factor Authentication via official Direct Banking portals).

---

## Decision Drivers

1. **Banking Act Regulatory Compliance**: Ensure strict compliance with Ginkō Hō rules governing electronic banking contract execution and intent verification.
2. **Fraud & Unauthorized Transfer Defense**: Prevent prompt injection attacks or session hijacking from executing financial transactions.
3. **Deterministic Operational Boundary**: Eliminate developer ambiguity regarding which features may be handled by the AI vs. redirected to Direct Banking.
4. **Seamless Customer Handoff**: Provide direct, secure deep-link redirection to Internet Banking when transactional intent is detected.

---

## Considered Options

1. **Strict Conversational Informational Boundary with Direct Banking Step-Up MFA Linkage (Chosen Option)**:
   - The AI Assistant handles 100% of read-only informational requests (balance inquiries, transaction history, fee calculations, FAQ assistance).
   - If the intent classifier detects actionable transactional intent (`振込`, `送金`, `解約`, `暗証番号変更`), the AI assistant halts execution and displays a standardized Keigo step-up authorization notice with a secure deep link to Internet Banking.
2. **In-Chat Step-Up MFA via OTP Input**:
   - Prompt the user for an One-Time Password (OTP) or PIN inside the chat window to execute transfers directly within the AI conversation.
   - *Drawback*: Exposes core banking transaction APIs to LLM prompt injection risks, violates FISC isolation standards, and breaches FSA AI contract rules.

---

## Decision Outcome

Chosen Option: **Option 1 (Strict Conversational Informational Boundary with Direct Banking Step-Up MFA Linkage)**.

### Permitted vs. Prohibited Operational Matrix:

| Category | Operation Type | Conversational AI Handling | Enforcement Mechanism |
|---|---|---|---|
| **Informational** | Account Balance View (普通/定期/外貨) | **Allowed** | Read-only synthetic / core banking lookup after PII masking. |
| **Informational** | Transaction History Search (明細照会) | **Allowed** | Filtered query against transaction database. |
| **Informational** | FAQ Search (振込手数料・口座開設) | **Allowed** | Rakuten Bank FAQ vector RAG retrieval. |
| **Informational** | Loyalty Tier Delta Calculation | **Allowed** | In-memory balance threshold calculation & Keigo explanation. |
| **Actionable** | Fund Transfer / Remittance (振込・送金) | **PROHIBITED** | Intercept intent -> Return MFA step-up link to Direct Banking. |
| **Actionable** | Account Closure / PIN Change (解約・PIN) | **PROHIBITED** | Intercept intent -> Return security portal link. |
| **Actionable** | Credit Limit Increase (増額申請) | **PROHIBITED** | Intercept intent -> Return loan application portal link. |

---

## Consequences

### Positive:
- **Zero Financial Transaction Risk**: No money movement capability exists within the LLM control plane, completely insulating the system against financial fraud via prompt injection.
- **100% Ginkō Hō Compliance**: Satisfies legal requirements for non-binding informational assistance.
- **Clear Engineering Scope**: Developers have an absolute, non-negotiable rule set for feature inclusion.

### Negative / Risks:
- **UX Handoff Step**: Customers attempting to execute transfers must transition from the chat assistant to the Direct Banking portal.
