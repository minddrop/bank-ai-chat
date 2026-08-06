"""
FastAPI Backend Application - Japanese Major Bank AI Customer Portal
Unites Customer Chat, Mock Account Service, FAQ RAG Engine, Control Planes, and FISC Audit Logger.
"""

import json
import os
import sys
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add src to python import path
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from control_plane.input_guardrail import InputGuardrail
from control_plane.output_guardrail import OutputGuardrail
from control_plane.audit_logger import AuditLogger
from rag.vector_store import VectorStore
from llm import get_llm_client
from core_banking.service import CoreBankingService
from core_banking.client import CoreBankingClient

app = FastAPI(
    title="Japanese Major Bank AI Assistant API",
    description="FISC and APPI Compliant Japanese Banking AI Assistant with Core Banking REST API",
    version="1.0.0"
)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()
audit_logger = AuditLogger()
vector_store = VectorStore()
llm_client = get_llm_client()
core_banking_service = CoreBankingService()
core_banking_client = CoreBankingClient(service=core_banking_service)

# Load mock accounts data file fallback
ACCOUNTS_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_bank_accounts.json"))

def get_account_data(customer_id: str) -> Optional[Dict[str, Any]]:
    # Use Core Banking Service SQLite query
    profile = core_banking_service.get_customer_profile(customer_id)
    if profile:
        return profile
    # Fallback to mock file if DB lookup returns None
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for cust in data.get("customers", []):
                if cust.get("customer_id") == customer_id:
                    return cust
    return None

class ChatRequest(BaseModel):
    session_id: str = "SESS-88001"
    customer_id: str = "CUST-1001"
    message: str

class ExtractionRequest(BaseModel):
    customer_id: str = "CUST-1001"

@app.get("/api/health")
def health_check():
    provider_type = os.environ.get("LLM_PROVIDER", "bedrock").lower()
    model_name = getattr(llm_client, "model_name", "amazon.nova-lite-v1:0")
    return {
        "status": "ONLINE",
        "region": "ap-northeast-1",
        "fisc_compliance": True,
        "llm_provider": provider_type,
        "llm_model": model_name,
        "core_banking_status": "CONNECTED"
    }

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
@app.get("/favicon.ico")
def suppress_dev_logs():
    return {}

@app.get("/api/customers")
def list_customers():
    return core_banking_service.get_all_customers()

# Core Banking System REST Endpoints
@app.get("/api/core/customers")
def core_list_customers():
    """List all customers registered in Core Banking DB."""
    return core_banking_service.get_all_customers()

@app.get("/api/core/customers/{customer_id}")
def core_get_customer_profile(customer_id: str):
    """Get detailed customer profile, account balances, and recent transactions."""
    profile = core_banking_service.get_customer_profile(customer_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Customer not found in Core Banking DB")
    return profile

@app.get("/api/core/customers/{customer_id}/accounts")
def core_get_account_balances(customer_id: str):
    """Get current balances for Ordinary Savings, Time Deposit, Foreign Currency accounts."""
    return core_banking_service.get_account_balances(customer_id)

@app.get("/api/core/customers/{customer_id}/transactions")
def core_get_transactions(customer_id: str, account_id: Optional[str] = None, limit: int = 20):
    """Get transaction history for customer."""
    return core_banking_service.get_transaction_history(customer_id, account_id=account_id, limit=limit)

@app.post("/api/core/extract-account-info")
def core_extract_account_info(req: ExtractionRequest):
    """
    Dedicated extraction API for AI Chat Bot / Microservices to extract
    current balance, account basic info, and transaction history context.
    """
    return core_banking_client.extract_account_info(req.customer_id)

@app.get("/api/faq/search")
def search_faq(q: str):
    return vector_store.search(query=q, top_k=5)

@app.get("/api/control-plane/logs")
def get_audit_logs():
    return audit_logger.get_recent_logs(limit=25)

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """
    Main Chat Endpoint executing the full Control Plane & RAG pipeline:
    1. Input Guardrail (PII Redaction & Prompt Injection Filter)
    2. Context Retrieval (Core Banking API Extraction + FAQ RAG Vector Search)
    3. Bedrock Amazon Nova Lite LLM Execution
    4. Output Guardrail (Grounding check, PII leak scan, Disclaimer append)
    5. FISC Audit Logger recording
    """
    # Step 1: Input Guardrail Execution
    in_eval = input_guardrail.process_input(req.message)
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
            session_id=req.session_id,
            customer_id=req.customer_id,
            input_guardrail_result=in_eval,
            output_guardrail_result=out_blocked,
            rag_context_ids=[],
            model_name="amazon.nova-lite-v1:0",
            latency_ms=10,
            token_usage={"input": len(req.message), "output": 0}
        )
        return {
            "reply": out_blocked["validated_response"],
            "control_plane": {
                "input_guardrail": in_eval,
                "output_guardrail": out_blocked,
                "rag_contexts": []
            }
        }

    # Step 2: Context Retrieval via Core Banking Extraction API Client
    customer_account = core_banking_service.get_customer_profile(req.customer_id)
    rag_matches = vector_store.search(in_eval["sanitized_prompt"], top_k=2)
    rag_context_ids = [m.get("id") for m in rag_matches]

    # Step 3: LLM Generation (Bedrock Nova Lite or Local LLM Client)
    llm_res = llm_client.generate_response(
        sanitized_prompt=in_eval["sanitized_prompt"],
        account_context=customer_account,
        rag_contexts=rag_matches
    )

    # Step 4: Output Guardrail Execution
    out_eval = output_guardrail.process_output(
        raw_llm_response=llm_res["text"],
        rag_contexts=rag_matches
    )

    # Step 5: FISC Audit Logging
    audit_logger.log_event(
        session_id=req.session_id,
        customer_id=req.customer_id,
        input_guardrail_result=in_eval,
        output_guardrail_result=out_eval,
        rag_context_ids=rag_context_ids,
        model_name=llm_res["model"],
        latency_ms=llm_res["latency_ms"],
        token_usage=llm_res["tokens"]
    )

    return {
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
    }

from fastapi.responses import FileResponse

# Serve static frontend files
FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
USER_FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend", "user"))

@app.get("/user")
def serve_user_app():
    user_index = os.path.join(USER_FRONTEND_DIR, "index.html")
    if os.path.exists(user_index):
        return FileResponse(user_index)
    raise HTTPException(status_code=404, detail="User application not found")

if os.path.exists(USER_FRONTEND_DIR):
    app.mount("/user", StaticFiles(directory=USER_FRONTEND_DIR, html=True), name="user_frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    print("Starting Japanese Bank AI Assistant FastAPI Server on http://localhost:8000 ...")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)

