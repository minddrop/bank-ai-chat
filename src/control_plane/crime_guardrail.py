"""
Anti-Financial Crime (AML/CFT) & Fraud Guardrail - Japanese Banking AI Control Plane
Detects and blocks money laundering, mule account exploitation, cash structuring, and financial fraud incitement.
Grounded in REQ-BUS-001, REQ-SEC-010, ADR-0018, and Act on Prevention of Transfer of Criminal Proceeds (犯罪収益移転防止法).
"""

import re
from typing import Dict, Any, List

FINANCIAL_CRIME_PATTERNS = [
    # Money Laundering & Structuring (資金洗浄 / 分割入金 / 報告回避)
    r'(マネーロンダリング|マネロン|資金洗浄|マネー・ロンダリング)',
    r'(100万|百万円).*(小分け|分割|バレずに|税務署|報告|回避|監視されない)',
    r'(税務署|警察|金融庁).*(バレない|見つからない|捕捉されない).*(送金|入金|口座)',
    
    # Account Muling / Illicit Account Trading (口座売買 / 闇バイト / 名義貸し)
    r'(口座|通帳|キャッシュカード).*(売買|買い取り|買い取って|譲渡|名義貸し|貸して|売る|売りたい)',
    r'(闇バイト|トクリュウ|高額バイト).*(送金|口座|出し子|受け子)',
    
    # Phishing & Fraud Template Generation
    r'(フィッシング|架空請求|還付金詐欺|オレオレ詐欺).*(メール|サイト|文面|テンプレート|作成)',
    r'(不正送金|他人の口座|不正アクセス|暗証番号抜き取り).*(方法|やり方|手口)'
]

CRIME_BLOCK_RESPONSE = (
    "【セキュリティ制御】ご入力いただいた内容は、法令（犯罪収益移転防止法・銀行法）および当行利用規約に抵触する恐れがあるため、"
    "お取り扱いできません。当行ではマネー・ロンダリングや特殊詐欺等の金融犯罪防止のため、アクセスログを適切に記録・管理しております。"
)

class CrimeGuardrail:
    """Guardrail to intercept financial crime solicitation, money laundering, and fraud patterns."""

    def __init__(self):
        self.crime_regexes = [re.compile(p, re.IGNORECASE) for p in FINANCIAL_CRIME_PATTERNS]

    def evaluate_crime_risk(self, user_prompt: str) -> Dict[str, Any]:
        """
        Evaluate if prompt contains malicious financial crime, AML structuring, or fraud incitement.
        """
        matched_indicators = []
        for regex in self.crime_regexes:
            match = regex.search(user_prompt)
            if match:
                matched_indicators.append(match.group(0))

        if matched_indicators:
            return {
                "allowed": False,
                "financial_crime_blocked": True,
                "matched_indicators": matched_indicators,
                "block_message": CRIME_BLOCK_RESPONSE,
                "severity": "CRITICAL_P1",
                "cloudwatch_alarm": "SecurityAlarms/FinancialCrimeAttempt",
                "reason": f"Financial crime / AML policy violation detected: {', '.join(matched_indicators)}"
            }

        return {
            "allowed": True,
            "financial_crime_blocked": False,
            "matched_indicators": [],
            "block_message": "",
            "severity": "NONE",
            "reason": "OK"
        }
