#!/usr/bin/env python3
"""
Standard Library HTTP Server - Japanese Major Bank AI Customer Portal
Provides native REST endpoints for /api/chat, /api/customers, /api/faq/search, /api/control-plane/logs
and serves static web frontend files (index.html, styles.css, app.js).
"""

import json
import os
import sys
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Add src directory to path
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from control_plane.input_guardrail import InputGuardrail
from control_plane.output_guardrail import OutputGuardrail
from control_plane.audit_logger import AuditLogger
from rag.vector_store import VectorStore
from llm import get_llm_client
from core_banking.service import CoreBankingService
from core_banking.client import CoreBankingClient

PORT = 8000
FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
ACCOUNTS_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_bank_accounts.json"))

# Initialize components
input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()
audit_logger = AuditLogger()
vector_store = VectorStore()
llm_client = get_llm_client()
core_banking_service = CoreBankingService()
core_banking_client = CoreBankingClient(service=core_banking_service)

def get_account_data(customer_id: str):
    profile = core_banking_service.get_customer_profile(customer_id)
    if profile:
        return profile
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for cust in data.get("customers", []):
                if cust.get("customer_id") == customer_id:
                    return cust
    return None

class BankPortalRequestHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query = urllib.parse.parse_qs(parsed_path.query)

        if path == "/api/health":
            provider_type = os.environ.get("LLM_PROVIDER", "bedrock").lower()
            model_name = getattr(llm_client, "model_name", "amazon.nova-lite-v1:0")
            self._send_json({
                "status": "ONLINE",
                "region": "ap-northeast-1",
                "fisc_compliance": True,
                "llm_provider": provider_type,
                "llm_model": model_name,
                "core_banking_status": "CONNECTED"
            })
            return

        if path in ("/api/customers", "/api/core/customers"):
            self._send_json(core_banking_service.get_all_customers())
            return

        # Route pattern: /api/core/customers/{customer_id} or /api/core/customers/{customer_id}/accounts or /api/core/customers/{customer_id}/transactions
        if path.startswith("/api/core/customers/"):
            parts = path.strip("/").split("/")
            # parts: ['api', 'core', 'customers', '<customer_id>', ?'<subpath>']
            if len(parts) == 4:
                customer_id = parts[3]
                profile = core_banking_service.get_customer_profile(customer_id)
                if profile:
                    self._send_json(profile)
                else:
                    self._send_json({"error": "Customer not found"}, status=404)
                return
            elif len(parts) == 5:
                customer_id = parts[3]
                sub = parts[4]
                if sub == "accounts":
                    self._send_json(core_banking_service.get_account_balances(customer_id))
                    return
                elif sub == "transactions":
                    acc_id = query.get("account_id", [None])[0]
                    lim = int(query.get("limit", [20])[0])
                    self._send_json(core_banking_service.get_transaction_history(customer_id, account_id=acc_id, limit=lim))
                    return

        if path == "/api/faq/search":
            q = query.get("q", [""])[0]
            results = vector_store.search(query=q, top_k=5)
            self._send_json(results)
            return

        if path == "/api/control-plane/logs":
            logs = audit_logger.get_recent_logs(limit=25)
            self._send_json(logs)
            return

        # Default static file handler
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/core/extract-account-info":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except Exception:
                self._send_json({"error": "Invalid JSON"}, status=400)
                return
            customer_id = data.get("customer_id", "CUST-1001")
            info = core_banking_client.extract_account_info(customer_id)
            self._send_json(info)
            return

        if self.path == "/api/chat":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except Exception:
                self._send_json({"error": "Invalid JSON"}, status=400)
                return

            session_id = data.get("session_id", "SESS-88001")
            customer_id = data.get("customer_id", "CUST-1001")
            message = data.get("message", "")

            # 1. Input Guardrail Execution
            in_eval = input_guardrail.process_input(message)
            if not in_eval["allowed"]:
                out_blocked = {
                    "validated_response": f"【セキュリティ制御】{in_eval.get('reason')}。当行のセキュリティ規約に基づき処理を停止いたしました。",
                    "grounding_score": 0.0,
                    "pii_leak_prevented": False,
                    "financial_advice_blocked": False,
                    "disclaimer_appended": True,
                    "warnings": ["Prompt Injection Attempt Blocked by Input Guardrail"]
                }
                audit_logger.log_event(
                    session_id=session_id,
                    customer_id=customer_id,
                    input_guardrail_result=in_eval,
                    output_guardrail_result=out_blocked,
                    rag_context_ids=[],
                    model_name="amazon.nova-lite-v1:0",
                    latency_ms=10,
                    token_usage={"input": len(message), "output": 0}
                )
                self._send_json({
                    "reply": out_blocked["validated_response"],
                    "control_plane": {
                        "input_guardrail": in_eval,
                        "output_guardrail": out_blocked,
                        "rag_contexts": []
                    }
                })
                return

            # 2. Context Retrieval via Core Banking Service
            customer_account = core_banking_service.get_customer_profile(customer_id)
            rag_matches = vector_store.search(in_eval["sanitized_prompt"], top_k=2)
            rag_context_ids = [m.get("id") for m in rag_matches]

            # 3. LLM Generation (Bedrock Nova Lite or Local LLM Client)
            llm_res = llm_client.generate_response(
                sanitized_prompt=in_eval["sanitized_prompt"],
                account_context=customer_account,
                rag_contexts=rag_matches
            )

            # 4. Output Guardrail Execution
            out_eval = output_guardrail.process_output(
                raw_llm_response=llm_res["text"],
                rag_contexts=rag_matches
            )

            # 5. FISC Audit Logging
            audit_logger.log_event(
                session_id=session_id,
                customer_id=customer_id,
                input_guardrail_result=in_eval,
                output_guardrail_result=out_eval,
                rag_context_ids=rag_context_ids,
                model_name=llm_res["model"],
                latency_ms=llm_res["latency_ms"],
                token_usage=llm_res["tokens"]
            )

            self._send_json({
                "reply": out_eval["validated_response"],
                "control_plane": {
                    "input_guardrail": in_eval,
                    "output_guardrail": out_eval,
                    "rag_contexts": rag_matches,
                    "llm_metadata": {
                        "model": llm_res["model"],
                        "provider": llm_res["provider"],
                        "latency_ms": llm_res["latency_ms"]
                    }
                }
            })
            return

        self._send_json({"error": "Not Found"}, status=404)

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

def main():
    print(f"Starting Japanese Bank AI Portal Server on http://localhost:{PORT}...")
    server = HTTPServer(('0.0.0.0', PORT), BankPortalRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    main()
