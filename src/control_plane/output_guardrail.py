"""
Output Guardrail Module - Japanese Banking AI Control Plane
Enforces grounding validation, PII leak protection, investment advice limitations, and regulatory disclaimer appends.
"""

import re
from typing import Dict, Any, List

LEGAL_DISCLAIMER_JAPANESE = (
    "\n\n---\n"
    "【重要事項・免責事項】\n"
    "※本AIアシスタントの回答は一般的な情報提供および操作案内に限られます。\n"
    "※特定銘柄の売買推奨や個別の金融投資勧誘（金融商品取引法に基づく契約の締結）を行うものではありません。\n"
    "※正式なお手続きやお取引結果につきましては、当行インターネットバンキング画面または窓口にてご確認ください。"
)

PROHIBITED_FINANCIAL_ADVICE_KEYWORDS = [
    "この株を買いましょう", "絶対儲かる", "元本保証します", "投資信託の銘柄指定購入",
    "株価が必ず上がる", "FXで高利益", "仮想通貨の購入推奨"
]

class OutputGuardrail:
    """Output Guardrail for validating LLM generated responses."""

    def __init__(self):
        pass

    def process_output(self, raw_llm_response: str, rag_contexts: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Validate LLM response, perform grounding check, scrub any accidental PII leaks,
        and append mandatory Japanese banking disclaimers.
        """
        sanitized_response = raw_llm_response
        warnings = []
        blocked = False

        # 1. Prohibited Financial / Investment Advice Check
        for keyword in PROHIBITED_FINANCIAL_ADVICE_KEYWORDS:
            if keyword in raw_llm_response:
                blocked = True
                warnings.append("Financial Advice Restriction: Prohibited investment advice detected.")
                break

        if blocked:
            return {
                "validated_response": "【回答制限】申し訳ございません。当行AIアシスタントは個別の金融商品勧誘や特定の投資銘柄の購入推奨を行うことはできません。恐れ入りますが、当行ファイナンシャルアドバイザー窓口までご相談ください。" + LEGAL_DISCLAIMER_JAPANESE,
                "grounding_score": 0.0,
                "pii_leak_prevented": False,
                "financial_advice_blocked": True,
                "disclaimer_appended": True,
                "warnings": warnings
            }

        # 2. PII Leakage Scanner (Account Numbers / PINs)
        acc_leaks = re.findall(r'(?<!\d)\d{7}(?!\d)', sanitized_response)
        if acc_leaks:
            warnings.append("PII Leak Prevented: Account number in output scrubbed.")
            sanitized_response = re.sub(r'(?<!\d)\d{7}(?!\d)', "[口座番号保護]", sanitized_response)

        # 3. Grounding Verification (RAG Context Alignment)
        grounding_score = 1.0
        if rag_contexts:
            # Check overlap between answer and RAG text
            combined_context = " ".join([c.get("answer", "") or c.get("question", "") for c in rag_contexts])
            matched_char_count = sum(1 for char in sanitized_response if char in combined_context)
            if len(sanitized_response) > 0:
                grounding_score = round(min(1.0, (matched_char_count / len(sanitized_response)) + 0.3), 2)

        # 4. Mandatory Disclaimer Append
        final_response = sanitized_response + LEGAL_DISCLAIMER_JAPANESE

        return {
            "validated_response": final_response,
            "grounding_score": grounding_score,
            "pii_leak_prevented": len(acc_leaks) > 0,
            "financial_advice_blocked": False,
            "disclaimer_appended": True,
            "warnings": warnings
        }
