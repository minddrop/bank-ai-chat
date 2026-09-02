"""
Local LLM Module - Local Development Environment for Japanese Major Bank AI Portal
Designed strictly for local offline development using light local LLM models (e.g. Ollama, LM Studio, vLLM, or Transformers).
Note: This local LLM provider is for local developer workflows only and will NOT be deployed to AWS production.
"""

import json
import os
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

SYSTEM_PROMPT_JAPANESE_BANK = (
    "あなたは日本の大手メガバンク「メガバンク日本銀行」の公式AIカスタマーアシスタントです。\n"
    "【行動指針】\n"
    "1. 丁寧で親切な日本語（敬語・丁寧語）で回答してください。\n"
    "2. 提供された「口座情報」および「FAQ参照ナレッジ」に基づいて正確に回答してください。\n"
    "3. 個別の株式や投資信託の銘柄購入を推奨する金融商品勧誘行為は絶対に行わないでください。\n"
    "4. 個人情報（口座番号、暗証番号等）の入力は求めず、保護されたコンテキストのみを参照してください。"
)

class LocalLLMClient:
    """
    Client for running local light LLM models during development.
    Supports Ollama API, OpenAI-compatible local endpoints, and offline fallback.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: int = 10
    ):
        self.base_url = base_url or os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1")
        self.model_name = model_name or os.environ.get("LOCAL_LLM_MODEL", "qwen2.5:0.5b")
        self.timeout = timeout

    def is_local_server_available(self) -> bool:
        """Check if local LLM server (e.g. Ollama / LM Studio) is running."""
        try:
            # Test endpoint health or models list
            url = f"{self.base_url.rstrip('/')}/models"
            req = urllib.request.Request(url, headers={"User-Agent": "BankAiLocalDev/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate_response(
        self,
        sanitized_prompt: str,
        account_context: Optional[Dict[str, Any]] = None,
        rag_contexts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate Japanese response using local light LLM model or high-fidelity local emulator.
        """
        start_time = time.time()

        # Construct system and user prompt context
        context_str = ""
        if account_context:
            context_str += f"\n【お客様口座情報 (マスキング済)】\n顧客ID: {account_context.get('customer_id')}\n名義: {account_context.get('name_kanji')} ({account_context.get('name_katakana')})\n"
            acc_list = account_context.get('accounts', [])
            for acc in acc_list:
                curr = acc.get('currency', 'JPY')
                bal = acc.get('balance', 0)
                bal_str = f"{bal:,.2f} {curr}" if curr != "JPY" else f"{bal:,} 円"
                context_str += f"- {acc.get('account_type')}: 残高 {bal_str}\n"

            if account_context.get('recent_transactions'):
                context_str += "直近取引明細:\n"
                for tx in account_context['recent_transactions'][:4]:
                    amt_val = tx.get('amount', 0)
                    amt_str = f"{amt_val:,}円" if tx.get('currency', 'JPY') == "JPY" else f"{amt_val} {tx.get('currency')}"
                    context_str += f"  - {tx.get('date')} [{tx.get('type')}] {amt_str} ({tx.get('description')}) -> 差引残高: {tx.get('balance_after', 0):,}円\n"

        if rag_contexts:
            context_str += "\n【行内FAQ参照ナレッジ】\n"
            for idx, ctx in enumerate(rag_contexts, 1):
                context_str += f"[{idx}] {ctx.get('question')}\n回答: {ctx.get('answer')}\n"

        full_user_content = f"{context_str}\n【お客様からの質問】\n{sanitized_prompt}"

        # 1. Attempt generation via local HTTP LLM Server (Ollama / OpenAI-compatible v1/chat/completions API)
        if self.is_local_server_available():
            try:
                chat_url = f"{self.base_url.rstrip('/')}/chat/completions"
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_JAPANESE_BANK},
                        {"role": "user", "content": full_user_content}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 512
                }
                data_bytes = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    chat_url,
                    data=data_bytes,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        text_out = res_json["choices"][0]["message"]["content"]
                        latency = int((time.time() - start_time) * 1000)
                        return {
                            "text": text_out,
                            "model": self.model_name,
                            "provider": f"Local LLM Server ({self.model_name})",
                            "latency_ms": latency,
                            "tokens": {"input": len(full_user_content), "output": len(text_out)}
                        }
            except Exception as e:
                print(f"[Local LLM] Server invocation error: {e}. Falling back to Local Development Engine.")

        # 2. Local Light Development Engine Fallback (Zero external dependency offline generation)
        latency = int((time.time() - start_time) * 1000) + 45
        text_out = self._local_development_generate(sanitized_prompt, account_context, rag_contexts)

        return {
            "text": text_out,
            "model": f"{self.model_name} (Local Light Dev Engine)",
            "provider": "Local Development Light LLM",
            "latency_ms": latency,
            "tokens": {"input": len(full_user_content), "output": len(text_out)}
        }

    def _local_development_generate(
        self,
        prompt: str,
        account_context: Optional[Dict[str, Any]],
        rag_contexts: Optional[List[Dict[str, Any]]]
    ) -> str:
        """High-fidelity local Japanese banking response emulator for rapid offline development."""
        p_lower = prompt.lower()

        # Stage Upgrade / Balance Delta Intent
        if any(w in p_lower for w in ["ランク", "ステージ", "スーパーvip", "vip", "ハッピープログラム", "あといくら", "ランクアップ", "条件"]):
            if account_context:
                name = account_context.get('name_katakana', '様')
                accs = account_context.get("accounts", [])
                savings_bal = 0
                for acc in accs:
                    if acc.get("account_type_code") == "SAVINGS" or "普通預金" in acc.get("account_type", ""):
                        savings_bal = acc.get("balance", 0)
                        break

                # Determine current stage and next tier target dynamically
                if savings_bal >= 3000000:
                    current_stage = "スーパーVIP"
                    next_stage = None
                    target_threshold = 3000000
                    delta = 0
                elif savings_bal >= 1000000:
                    current_stage = "VIP"
                    next_stage = "スーパーVIP"
                    target_threshold = 3000000
                    delta = target_threshold - savings_bal
                elif savings_bal >= 500000:
                    current_stage = "プレミアム"
                    next_stage = "VIP"
                    target_threshold = 1000000
                    delta = target_threshold - savings_bal
                elif savings_bal >= 100000:
                    current_stage = "アドバンス"
                    next_stage = "プレミアム"
                    target_threshold = 500000
                    delta = target_threshold - savings_bal
                else:
                    current_stage = "ベーシック"
                    next_stage = "アドバンス"
                    target_threshold = 100000
                    delta = target_threshold - savings_bal

                res = f"いつもメガバンク日本銀行をご利用いただきありがとうございます。\n"
                res += f"{name}様の現在の普通預金残高は【{savings_bal:,.1f} 円】（現在のステージ：『{current_stage}』）です。\n\n"
                if next_stage and delta > 0:
                    res += f"上位ステージ『{next_stage}』（普通預金残高{target_threshold:,}円以上）を達成するには、あと【{delta:,.1f} 円】のご預金が必要です。\n\n"
                    res += f"【{next_stage}達成時の主な優遇特典】\n"
                    if next_stage == "スーパーVIP":
                        res += "・他行振込手数料：毎月3回まで無料\n・ATM利用手数料：毎月7回まで無料\n・ポイント獲得倍率：3倍\n\n"
                    elif next_stage == "VIP":
                        res += "・他行振込手数料：毎月3回まで無料\n・ATM利用手数料：毎月5回まで無料\n\n"
                    elif next_stage == "プレミアム":
                        res += "・他行振込手数料：毎月2回まで無料\n・ATM利用手数料：毎月5回まで無料\n\n"
                    else:
                        res += "・他行振込手数料：毎月1回まで無料\n・ATM利用手数料：毎月2回まで無料\n\n"
                    res += f"あと {delta:,.1f} 円をご入金いただくか、他行からの振込受取等を組み合わせることで、翌月より自動的に{next_stage}ステージへランクアップいたします。"
                else:
                    res += "現在、すでに最高位ステージ『スーパーVIP』の条件を達成されています！\n"
                    res += "他行振込手数料月3回無料・ATM利用手数料月7回無料の優遇特典をご利用いただけます。"
                return res

        # Account Balance & Transactions Intent
        if any(w in p_lower for w in ["残高", "口座", "いくら", "明細", "取引"]):
            if account_context:
                name = account_context.get('name_katakana', '様')
                accs = account_context.get("accounts", [])
                txns = account_context.get("recent_transactions", [])
                res = f"いつもメガバンク日本銀行をご利用いただきありがとうございます。\n"
                res += f"お客様（{name}様）の口座残高および直近の取引明細は以下の通りです。\n\n"
                res += "【保有口座残高一覧】\n"
                for acc in accs:
                    curr = acc.get('currency', 'JPY')
                    bal = acc.get('balance', 0)
                    bal_str = f"{bal:,.2f} {curr}" if curr != "JPY" else f"{bal:,} 円"
                    res += f"・{acc.get('account_type')}: {bal_str}\n"

                if txns:
                    res += "\n【直近取引明細】\n"
                    for tx in txns[:4]:
                        amt = tx.get('amount', 0)
                        is_neg = amt < 0
                        amt_formatted = f"-¥{abs(amt):,}" if is_neg else f"+¥{amt:,}"
                        res += f"・{tx.get('date')} | {tx.get('type')} | {amt_formatted} ({tx.get('description')})\n"
                return res
            return "恐れ入ります。口座情報をご参照いただくには、ログインの上カスタマーIDをご確認ください。"

        # RAG FAQ Guidance Intent
        if rag_contexts:
            top_faq = rag_contexts[0]
            ans_text = top_faq.get('answer', '').replace("楽天銀行", "当行")
            res = f"お問合せいただきました「{top_faq.get('question')}」につきまして、以下の通りご案内いたします。\n\n"
            res += f"{ans_text}\n\n"
            res += f"詳細につきましては、当行公式Webサイト（{top_faq.get('url')}）をご確認ください。"
            return res

        # Default Polite Japanese Banking Greeting
        return (
            "お問合せいただきありがとうございます。メガバンク日本銀行ローカル開発用AIアシスタントです。\n"
            "当行の口座残高照会、振込手続き、ATM手数料、定期預金のご案内など、各種サービスについてお気軽にお尋ねください。"
        )
