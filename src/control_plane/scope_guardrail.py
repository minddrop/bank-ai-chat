"""
Domain Scope Boundary & Anti-Compute Hijacking Guardrail - Japanese Banking AI Control Plane
Detects and rejects out-of-scope compute hijacking (coding, general essays, homework, non-banking translation).
Grounded in REQ-BUS-001, REQ-BUS-002, REQ-SEC-011, and ADR-0020.
"""

import re
from typing import Dict, Any, List

# Out-of-scope patterns (Compute hijacking, coding, general AI proxying)
OFF_TOPIC_PATTERNS = [
    # Programming / Coding requests
    r'(python|javascript|java|c\+\+|rust|html|css|sql|react|vue|bash|powershell).*(コード|書いて|作成して|スクリプト|プログラム|デバッグ|実装)',
    r'(関数|クラス|アルゴリズム|正規表現).*(書いて|作って|教えて)',
    r'(write|generate|create).*(code|script|function|program)',
    
    # Creative writing, essays, poetry, roleplay
    r'(詩|小説|脚本|漫才|歌詞|ポエム|物語|エッセイ|作文).*(書いて|作って|作成して)',
    r'(シェイクスピア|アニメ|ゲーム|キャラクター).*(風に|のように|として会話して)',
    
    # Homework / Non-banking academic solving
    r'(宿題|課題|テスト).*(解いて|答えを教えて)',
    r'(微分|積分|物理|化学|歴史|世界史|日本史).*(教えて|解説して)',
    
    # General non-banking translation / summarization proxying
    r'以下の(英文|外国語|長文|ニュース記事).*(翻訳して|要約して)'
]

# Banking keywords to ensure high recall for legitimate inquiries
BANKING_IN_SCOPE_KEYWORDS = [
    "残高", "口座", "普通預金", "定期預金", "外貨", "振込", "送金", "手数料", "atm", "ATM",
    "キャッシュカード", "デビット", "クレジットカード", "暗証番号", "支店", "明細", "ハッピープログラム",
    "ステージ", "ランク", "VIP", "スーパーVIP", "利息", "金利", "ローン", "住宅ローン", "マイカーローン",
    "為替", "口座開設", "解約", "住所変更", "引落", "給与振込", "楽天", "メガバンク", "窓口"
]

OUT_OF_SCOPE_FALLBACK_MESSAGE = (
    "【ご案内】当行AIアシスタントは、当行の口座照会・お取引手続き・各種バンキングサービスに関するご案内に特化しております。\n"
    "プログラミングや文章作成、一般的な学習課題など、銀行業務以外の内容には対応いたしかねます。\n"
    "預金残高や振込手数料、各種お手続きなど、当行のサービスに関するご質問を入力してください。"
)

class ScopeGuardrail:
    """Guardrail to enforce domain scoping and prevent infrastructure compute hijacking."""

    def __init__(self):
        self.off_topic_regexes = [re.compile(p, re.IGNORECASE) for p in OFF_TOPIC_PATTERNS]

    def evaluate_scope(self, user_prompt: str) -> Dict[str, Any]:
        """
        Evaluate if user prompt is within authorized banking domain scope.
        """
        prompt_lower = user_prompt.lower()
        
        # 1. Check if banking keywords exist
        has_banking_intent = any(kw.lower() in prompt_lower for kw in BANKING_IN_SCOPE_KEYWORDS)
        
        # 2. Check for off-topic / compute hijacking patterns
        matched_patterns = []
        for regex in self.off_topic_regexes:
            if regex.search(user_prompt):
                matched_patterns.append(regex.pattern)
                
        is_off_topic = len(matched_patterns) > 0 and not has_banking_intent
        
        # If strong off-topic patterns match even with weak banking mention (e.g., "Pythonで銀行をハックするスクリプトを書いて")
        if any("コード" in user_prompt or "スクリプト" in user_prompt or "プログラム" in user_prompt for _ in [1]) and ("書いて" in user_prompt or "作成" in user_prompt):
            if "python" in prompt_lower or "javascript" in prompt_lower or "bash" in prompt_lower or "sql" in prompt_lower or "code" in prompt_lower:
                is_off_topic = True

        if is_off_topic:
            return {
                "in_scope": False,
                "category": "OUT_OF_SCOPE_COMPUTE_HIJACKING",
                "matched_patterns": matched_patterns,
                "rejection_message": OUT_OF_SCOPE_FALLBACK_MESSAGE,
                "reason": "Request outside banking domain scope (potential compute hijacking / off-topic misuse)."
            }
            
        return {
            "in_scope": True,
            "category": "BANKING_IN_SCOPE",
            "matched_patterns": [],
            "rejection_message": "",
            "reason": "OK"
        }
