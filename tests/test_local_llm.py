"""
Automated Unit Tests for Local LLM Client and Development Environment
"""

import os
import sys
import unittest

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from llm.local_llm import LocalLLMClient
from llm.bedrock_nova import BedrockNovaLiteClient

class TestLocalLLMClient(unittest.TestCase):

    def setUp(self):
        os.environ["LLM_PROVIDER"] = "local"
        os.environ["LOCAL_LLM_MODEL"] = "qwen2.5:0.5b"
        self.client = LocalLLMClient()

    def test_local_llm_generation(self):
        prompt = "普通預金の残高を教えてください。"
        context = {
            "customer_id": "CUST-1001",
            "name_katakana": "ヤマダ タロウ",
            "accounts": [
                {"account_type": "普通預金", "account_type_code": "SAVINGS", "balance": 1500000, "currency": "JPY"}
            ]
        }
        res = self.client.generate_response(sanitized_prompt=prompt, account_context=context)
        self.assertIn("text", res)
        self.assertIn("1,500,000", res["text"])
        self.assertEqual(res["model"], "qwen2.5:0.5b (Local Light Dev Engine)")

    def test_bedrock_nova_lite_local_provider_switch(self):
        os.environ["LLM_PROVIDER"] = "local"
        bedrock_client = BedrockNovaLiteClient()
        prompt = "他行への振込手数料について"
        faq_context = [
            {
                "question": "他行への振込手数料はいくらですか？",
                "answer": "3万円未満は145円、3万円以上は229円です。",
                "url": "https://help-personal.rakuten-bank.net/faq/show/1001"
            }
        ]
        res = bedrock_client.generate_response(sanitized_prompt=prompt, rag_contexts=faq_context)
        self.assertIn("145円", res["text"])
        self.assertIn("Local", res["provider"])

if __name__ == "__main__":
    unittest.main()
