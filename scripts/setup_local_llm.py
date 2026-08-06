#!/usr/bin/env python3
"""
Local LLM Setup & Test Script - Local Development Environment
Helper utility to configure and test a lightweight local LLM (e.g., Ollama qwen2.5:0.5b / qwen2.5:1.5b)
for local offline development without AWS Bedrock or external cloud calls.
Note: This local setup is for local development only and will NOT be deployed.
"""

import os
import sys
import argparse
import urllib.request
import json

# Add src directory to path
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from llm.local_llm import LocalLLMClient

def check_ollama():
    url = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1").rstrip("/")
    models_endpoint = f"{url}/models"
    print(f"Checking Local LLM server status at {models_endpoint}...")
    try:
        req = urllib.request.Request(models_endpoint, headers={"User-Agent": "BankAiDevCheck/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("id") for m in data.get("data", [])]
                print(f"✅ Local LLM server is ONLINE!")
                print(f"   Available Local Models: {models}")
                return True
    except Exception as e:
        print(f"ℹ️  No external local HTTP server found ({e}).")
        print("   Local Development Engine fallback will be used automatically.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Japanese Bank AI Assistant - Local LLM Dev Setup")
    parser.add_argument("--model", type=str, default="qwen2.5:0.5b", help="Lightweight local model name (e.g. qwen2.5:0.5b, qwen2.5:1.5b, gemma:2b)")
    parser.add_argument("--url", type=str, default="http://localhost:11434/v1", help="Local LLM HTTP endpoint base URL")
    args = parser.parse_args()

    os.environ["LLM_PROVIDER"] = "local"
    os.environ["LOCAL_LLM_MODEL"] = args.model
    os.environ["LOCAL_LLM_URL"] = args.url

    print("==========================================================")
    print(" 🏦 Japanese Bank AI Portal - Local LLM Development Setup")
    print("==========================================================")
    print(f" Target Light Model : {args.model}")
    print(f" Base Endpoint URL  : {args.url}")
    print(" Deployment Scope   : LOCAL DEVELOPMENT ONLY (Not Deployed)")
    print("----------------------------------------------------------")

    server_online = check_ollama()
    if not server_online:
        print("\n💡 Recommendation for Lightweight Local Model setup (Ollama):")
        print("   1. Install Ollama: https://ollama.com")
        print(f"   2. Run command: ollama pull {args.model}")
        print("   3. Start server: ollama serve")

    print("\nExecuting test generation via LocalLLMClient...")
    client = LocalLLMClient(base_url=args.url, model_name=args.model)

    sample_prompt = "他行への振込手数料と普通預金の残高について教えてください。"
    sample_context = {
        "customer_id": "CUST-1001",
        "name_kanji": "山田 太郎",
        "name_katakana": "ヤマダ タロウ",
        "accounts": [
            {"account_type": "普通預金", "account_type_code": "SAVINGS", "balance": 2450000, "currency": "JPY"}
        ]
    }
    sample_faq = [
        {
            "question": "他行への振込手数料はいくらですか？",
            "answer": "楽天銀行から他行口座への振込手数料は、3万円未満は145円（税込）、3万円以上は229円（税込）です。",
            "url": "https://help-personal.rakuten-bank.net/faq/show/1001"
        }
    ]

    res = client.generate_response(
        sanitized_prompt=sample_prompt,
        account_context=sample_context,
        rag_contexts=sample_faq
    )

    print("\n------------------ Response Result ------------------")
    print(f"Provider : {res.get('provider')}")
    print(f"Model    : {res.get('model')}")
    print(f"Latency  : {res.get('latency_ms')} ms")
    print(f"Text Out :\n{res.get('text')}")
    print("-----------------------------------------------------")
    print("✅ Local LLM environment is ready for offline development!")

if __name__ == "__main__":
    main()
