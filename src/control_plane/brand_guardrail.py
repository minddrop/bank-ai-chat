"""
Brand Protection & Competitor Suppression Guardrail - Japanese Banking AI Control Plane
Prevents competitor bank promotion, brand erosion, and non-compliant comparative marketing.
Grounded in REQ-BUS-001, REQ-AI-012, and ADR-0020.
"""

import re
from typing import Dict, Any, List, Optional

# Comprehensive Competitor Recognition Dictionary (35+ Japanese Financial Institutions)
COMPETITOR_INSTITUTIONS = [
    # Megabanks & Major Banking Groups
    "三菱UFJ銀行", "三菱UFJ", "MUFG", "mufg", "三井住友銀行", "SMBC", "smbc",
    "みずほ銀行", "みずほ", "MIZUHO", "mizuho", "りそな銀行", "りそな", "埼玉りそな銀行",
    
    # Digital / Internet Net Banks
    "住信SBIネット銀行", "住信SBI", "SBIネット銀行", "ソニー銀行", "Sony Bank",
    "auじぶん銀行", "じぶん銀行", "PayPay銀行", "ジャパンネット銀行", "イオン銀行",
    "GMOあおぞらネット銀行", "GMOあおぞら", "みんなの銀行", "UI銀行", "東京スター銀行",
    "大和ネクスト銀行", "楽天銀行", # If self is generic or comparative
    
    # Major Trust Banks
    "三井住友信託銀行", "三菱UFJ信託銀行", "みずほ信託銀行", "SMBC信託銀行", "プレスティア", "PRESTIA",
    
    # Major Regional & Shinkin Banks
    "横浜銀行", "千葉銀行", "静岡銀行", "福岡銀行", "常陽銀行", "京都銀行", "西日本シティ銀行",
    
    # Major Fintechs & Non-Bank Payment Operators
    "PayPay", "LINE Pay", "メルペイ", "d払い", "au PAY", "Kyash"
]

# Comparative prompt triggers
COMPARATIVE_PATTERNS = [
    r'他行.*(おすすめ|比較|手数料が安い|金利が高い|乗り換え)',
    r'(どこ|どこの銀行).*(おすすめ|お得|良い|よい)',
    r'(他行|別の銀行).*(口座開設|使ったほうがいい)',
    r'(他行|競合).*(比較|勝っている|劣っている)'
]

class BrandGuardrail:
    """Guardrail for protecting banking brand identity and suppressing competitor recommendations."""

    def __init__(self):
        self.competitors = COMPETITOR_INSTITUTIONS
        # Compile pattern for high performance
        escaped_competitors = [re.escape(c) for c in self.competitors]
        self.competitor_regex = re.compile(r'(' + '|'.join(escaped_competitors) + r')', re.IGNORECASE)

    def evaluate_prompt(self, user_prompt: str) -> Dict[str, Any]:
        """
        Evaluate customer prompt for competitor mentions or comparative shopping intent.
        """
        competitor_matches = self.competitor_regex.findall(user_prompt)
        is_comparative = any(re.search(pat, user_prompt) for pat in COMPARATIVE_PATTERNS)
        
        # Deduplicate matches
        unique_matches = list(set(competitor_matches))
        
        return {
            "has_competitor_mention": len(unique_matches) > 0,
            "competitors_mentioned": unique_matches,
            "is_comparative_inquiry": is_comparative,
            "brand_risk_detected": len(unique_matches) > 0 or is_comparative
        }

    def sanitize_or_redirect_response(self, raw_response: str, user_prompt: str = "") -> Dict[str, Any]:
        """
        Scan LLM output for unauthorized competitor endorsements or favorable competitor mentions.
        If detected, rewrite or substitute with official brand-aligned benefit guidance.
        """
        output_matches = self.competitor_regex.findall(raw_response)
        unique_output_matches = list(set(output_matches))
        
        if unique_output_matches:
            # Output contains competitor mentions - rewrite or neutralize
            redirection_message = (
                "当行では、他行様の商品・サービスに関する個別のご案内や比較評価は差し控えさせていただいております。\n\n"
                "当行におきましては、優遇プログラム「ハッピープログラム」にて、会員ステージ（VIP・スーパーVIP等）に応じた"
                "他行宛振込手数料の無料特典（月最大3回〜7回）や提携ATM手数料無料サービス、好金利の定期預金・外貨預金キャンペーンを多数ご用意しております。\n"
                "当行の各種サービス詳細や優遇条件につきましては、当行ホームページまたは口座管理画面よりご確認いただけますと幸いでございます。"
            )
            return {
                "blocked": True,
                "sanitized_response": redirection_message,
                "competitors_scrubbed": unique_output_matches,
                "reason": f"Competitor institution mention suppressed: {', '.join(unique_output_matches)}"
            }
            
        return {
            "blocked": False,
            "sanitized_response": raw_response,
            "competitors_scrubbed": [],
            "reason": "OK"
        }
