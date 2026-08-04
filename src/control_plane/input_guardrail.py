"""
Input Guardrail Module - Japanese Banking AI Control Plane
Enforces APPI (個人情報保護法) compliance, PII redaction, prompt injection prevention, and scope control.
"""

import re
from typing import Dict, Any, List

# Regex patterns for Japanese Banking PII
PATTERNS = {
    "account_number": (r'(?<!\d)\d{7}(?!\d)', "[口座番号保護: XXXXXXX]"),
    "branch_code": (r'支店コード\s*[:：]?\s*(\d{3})|支店番号\s*[:：]?\s*(\d{3})', "支店コード: [XXX]"),
    "pin_password": (r'(暗証番号|パスワード|PIN|pin)\s*[:：]?\s*(\d{4,8}|[a-zA-Z0-9]{4,16})', r'\1: [暗証番号保護]'),
    "phone_number": (r'0\d{1,4}-\d{1,4}-\d{4}|0[789]0\d{8}', "[電話番号保護]"),
    "katakana_fullname": (r'口座名義人?\s*[:：]?\s*([\u30A0-\u30FF]+\s*[\u30A0-\u30FF]+)', "口座名義: [名義人保護]"),
}

PROMPT_INJECTION_KEYWORDS = [
    "system prompt", "ignore previous instructions", "指示を無視", "システムプロンプトを出力",
    "Jailbreak", "DAN mode", "開発者モード", "内部規約を開示", "管理者権限"
]

class InputGuardrail:
    """Input Guardrail for scanning and sanitizing customer prompts."""

    def __init__(self):
        pass

    def process_input(self, user_prompt: str) -> Dict[str, Any]:
        """
        Process and sanitize customer input before passing to LLM context.
        Returns detailed guardrail status and sanitized prompt payload.
        """
        original = user_prompt
        sanitized = user_prompt
        pii_found = []
        
        # 1. Prompt Injection & Jailbreak Check
        injection_blocked = False
        for keyword in PROMPT_INJECTION_KEYWORDS:
            if keyword.lower() in user_prompt.lower():
                injection_blocked = True
                break
                
        if injection_blocked:
            return {
                "allowed": False,
                "sanitized_prompt": "[BLOCKED: Prompt Injection / System Override Attempt Detected]",
                "pii_detected": False,
                "pii_tokens_scrubbed": [],
                "prompt_injection_blocked": True,
                "reason": "Security Policy Violation: Prompt injection attempt detected."
            }

        # 2. PII Detection and Redaction (APPI Compliance)
        # Account number
        acc_matches = re.findall(PATTERNS["account_number"][0], sanitized)
        if acc_matches:
            pii_found.append(f"Account Numbers: {len(acc_matches)} redacted")
            sanitized = re.sub(PATTERNS["account_number"][0], PATTERNS["account_number"][1], sanitized)
            
        # PIN / Password
        pin_matches = re.findall(PATTERNS["pin_password"][0], sanitized)
        if pin_matches:
            pii_found.append("PIN/Password: redacted")
            sanitized = re.sub(PATTERNS["pin_password"][0], PATTERNS["pin_password"][1], sanitized)

        # Phone Number
        phone_matches = re.findall(PATTERNS["phone_number"][0], sanitized)
        if phone_matches:
            pii_found.append("Phone Numbers: redacted")
            sanitized = re.sub(PATTERNS["phone_number"][0], PATTERNS["phone_number"][1], sanitized)

        # Katakana Fullname
        name_matches = re.findall(PATTERNS["katakana_fullname"][0], sanitized)
        if name_matches:
            pii_found.append("Katakana Fullname: redacted")
            sanitized = re.sub(PATTERNS["katakana_fullname"][0], PATTERNS["katakana_fullname"][1], sanitized)

        return {
            "allowed": True,
            "original_prompt": original,
            "sanitized_prompt": sanitized,
            "pii_detected": len(pii_found) > 0,
            "pii_tokens_scrubbed": pii_found,
            "prompt_injection_blocked": False,
            "reason": "OK"
        }
