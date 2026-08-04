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
from llm.bedrock_nova import BedrockNovaLiteClient

app = FastAPI(
    title="Japanese Major Bank AI Assistant API",
    description="FISC and APPI Compliant Japanese Banking AI Assistant with In-VPC Control Planes",
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
bedrock_client = BedrockNovaLiteClient()

# Load mock accounts data
ACCOUNTS_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_bank_accounts.json"))

def get_account_data(customer_id: str) -> Optional[Dict[str, Any]]:
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

@app.get("/api/health")
def health_check():
    return {
        "status": "ONLINE",
        "region": "ap-northeast-1",
        "fisc_compliance": True,
        "llm_model": "amazon.nova-lite-v1:0 (Bedrock)"
    }

@app.get("/api/customers")
def list_customers():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("customers", [])
    return []

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
    2. Context Retrieval (Mock Account + Rakuten Bank FAQ RAG Vector Search)
    3. Bedrock Amazon Nova Lite LLM Execution
    4. Output Guardrail (Grounding check, PII leak scan, Disclaimer append)
    5. FISC Audit Logger recording
    """
    # Step 1: Input Guardrail Execution
    in_eval = input_guardrail.process_input(req.message)
    if not in_eval["allowed"]:
        # Blocked at Input Control Plane
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

    # Step 2: Context Retrieval
    customer_account = get_account_data(req.customer_id)
    rag_matches = vector_store.search(in_eval["sanitized_prompt"], top_k=2)
    rag_context_ids = [m.get("id") for m in rag_matches]

    # Step 3: LLM Generation via Amazon Bedrock (Nova Lite)
    llm_res = bedrock_client.generate_response(
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

# Serve static frontend files
FRONTEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
