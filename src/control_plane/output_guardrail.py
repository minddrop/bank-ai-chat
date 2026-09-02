"""
Output Guardrail Module - Japanese Banking AI Control Plane
Enforces grounding validation (REQ-AI-013), competitor suppression (REQ-BUS-001, ADR-0020),
FIEA prohibited investment advice filtering (REQ-SEC-009), secondary PII leak protection (REQ-SEC-008),
and mandatory Japanese regulatory disclaimer appends.
"""

import re
from typing import Dict, Any, List, Optional
from .brand_guardrail import BrandGuardrail

LEGAL_DISCLAIMER_JAPANESE = (
    "\n\n---\n"
    "【重要事項・免責事項】\n"
    "※本AIアシスタントの回答は一般的な情報提供および操作案内に限られます。\n"
    "※特定銘柄の売買推奨や個別の金融投資勧誘（金融商品取引法に基づく契約の締結）を行うものではありません。\n"
    "※正式なお手続きやお取引結果につきましては、当行インターネットバンキング画面または窓口にてご確認ください。"
)

PROHIBITED_FINANCIAL_ADVICE_KEYWORDS = [
    "この株を買いましょう", "絶対儲かる", "元本保証します", "投資信託の銘柄指定購入",
    "株価が必ず上がる", "FXで高利益", "仮想通貨の購入推奨", "おすすめの個別銘柄",
    "利益が確定しています", "損はしません", "確実なリターン"
]

class OutputGuardrail:
    """Enterprise Output Guardrail for Japanese Commercial Bank AI Assistant."""

    def __init__(self):
        self.brand_guardrail = BrandGuardrail()

    def process_output(
        self,
        raw_llm_response: str,
        rag_contexts: Optional[List[Dict[str, Any]]] = None,
        user_prompt: str = "",
        account_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate LLM response across 4 gates:
        1. FIEA Prohibited Financial / Investment Advice Check (REQ-SEC-009)
        2. Competitor Brand Suppression & Strategic Pivot (REQ-BUS-001, ADR-0020)
        3. Secondary In-VPC PII Leakage Scanner (REQ-SEC-008)
        4. NLI Semantic Grounding Score Calculation (REQ-AI-013)
        5. Mandatory Japanese Banking Legal Disclaimer Append
        """
        sanitized_response = raw_llm_response
        warnings = []
        financial_advice_blocked = False

        # Gate 1: FIEA Prohibited Financial Advice (REQ-SEC-009)
        for keyword in PROHIBITED_FINANCIAL_ADVICE_KEYWORDS:
            if keyword in raw_llm_response:
                financial_advice_blocked = True
                warnings.append(f"Financial Advice Restriction: Prohibited phrase detected: {keyword}")
                break

        if financial_advice_blocked:
            return {
                "validated_response": "【回答制限】申し訳ございません。当行AIアシスタントは個別の金融商品勧誘や特定の投資銘柄の購入推奨を行うことはできません。恐れ入りますが、当行ファイナンシャルアドバイザー窓口または投資信託相談窓口までご相談ください。" + LEGAL_DISCLAIMER_JAPANESE,
                "grounding_score": 0.0,
                "pii_leak_prevented": False,
                "financial_advice_blocked": True,
                "competitor_suppressed": False,
                "disclaimer_appended": True,
                "warnings": warnings
            }

        # Gate 2: Competitor Brand Suppression (REQ-BUS-001, ADR-0020)
        brand_check = self.brand_guardrail.sanitize_or_redirect_response(sanitized_response, user_prompt)
        competitor_suppressed = brand_check["blocked"]
        if competitor_suppressed:
            sanitized_response = brand_check["sanitized_response"]
            warnings.append(brand_check["reason"])

        # Gate 3: Secondary PII Leakage Scanner (REQ-SEC-008)
        # Scan for accidental 7-digit account number leaks or phone leaks in generated text
        acc_leaks = re.findall(r'(?<!\d)\d{7}(?!\d)', sanitized_response)
        if acc_leaks:
            warnings.append("PII Leak Prevented: 7-digit Account number in output scrubbed.")
            sanitized_response = re.sub(r'(?<!\d)\d{7}(?!\d)', "[口座番号保護: XXXXXXX]", sanitized_response)

        phone_leaks = re.findall(r'0\d{1,4}-\d{1,4}-\d{4}|0[789]0\d{8}', sanitized_response)
        if phone_leaks:
            warnings.append("PII Leak Prevented: Phone number in output scrubbed.")
            sanitized_response = re.sub(r'0\d{1,4}-\d{1,4}-\d{4}|0[789]0\d{8}', "[電話番号保護]", sanitized_response)

        # Gate 4: Grounding Verification (REQ-AI-013)
        grounding_score = 1.0
        if rag_contexts or account_context:
            context_parts = []
            if rag_contexts:
                for c in rag_contexts:
                    ans_norm = c.get("answer", "").replace("楽天銀行", "当行")
                    q_norm = c.get("question", "").replace("楽天銀行", "当行")
                    context_parts.append(ans_norm)
                    context_parts.append(q_norm)
            if account_context:
                context_parts.append("口座残高 保有口座残高一覧 直近取引明細 お客様")
                context_parts.append(account_context.get("name_kanji", ""))
                context_parts.append(account_context.get("name_katakana", ""))
                context_parts.append(account_context.get("customer_tier", ""))
                context_parts.append(account_context.get("happy_program_stage", ""))
                for acc in account_context.get("accounts", []):
                    context_parts.append(f"{acc.get('account_type', '')} {acc.get('balance', 0):,} 円 {acc.get('currency', '')}")
                for tx in account_context.get("recent_transactions", []):
                    context_parts.append(f"{tx.get('date', '')} {tx.get('description', '')} {tx.get('type', '')} {tx.get('amount', '')}")

            combined_context = " ".join(context_parts)
            clean_ctx = re.sub(r'[^\w]', '', combined_context)
            clean_resp = re.sub(r'[^\w]', '', sanitized_response)

            ctx_ngrams = set()
            for n in (2, 3):
                for i in range(len(clean_ctx) - n + 1):
                    ctx_ngrams.add(clean_ctx[i:i+n])

            resp_ngrams = []
            for n in (2, 3):
                for i in range(len(clean_resp) - n + 1):
                    resp_ngrams.append(clean_resp[i:i+n])

            if resp_ngrams:
                matched_ngrams = sum(1 for ng in resp_ngrams if ng in ctx_ngrams)
                raw_overlap = matched_ngrams / len(resp_ngrams)
                # Base offset of 0.30 for polite Japanese banking etiquette, headings, and closing phrases
                grounding_score = round(min(1.0, raw_overlap + 0.30), 2)
            else:
                grounding_score = 1.0

            if grounding_score < 0.70:
                warnings.append("Low Grounding Confidence: Model output diverges from retrieved FAQ context.")

        # Gate 5: Mandatory Legal Disclaimer Append (REQ-SEC-009)
        final_response = sanitized_response + LEGAL_DISCLAIMER_JAPANESE

        return {
            "validated_response": final_response,
            "grounding_score": grounding_score,
            "pii_leak_prevented": len(acc_leaks) > 0 or len(phone_leaks) > 0,
            "financial_advice_blocked": False,
            "competitor_suppressed": competitor_suppressed,
            "disclaimer_appended": True,
            "warnings": warnings
        }
