"""
FastAPI Backend Application - Japanese Major Bank AI Customer Portal
Unites Customer Chat, Mock Account Service, FAQ RAG Engine, In-VPC Control Planes,
Server-Sent Events (SSE) Streaming, Step-Up MFA, and FISC Audit Logger.
Compliant with REQ-BUS-001, REQ-FUN-003, REQ-FUN-004, REQ-FUN-005, REQ-FUN-006,
REQ-SEC-008, REQ-SEC-009, REQ-SEC-010, REQ-SEC-011, REQ-IF-015, and REQ-IF-016.
"""

import asyncio
import datetime
import json
import os
import sys
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Add src to python import path
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from control_plane.input_guardrail import InputGuardrail
from control_plane.output_guardrail import OutputGuardrail
from control_plane.audit_logger import AuditLogger
from rag.vector_store import VectorStore
from llm import get_llm_client
from core_banking.service import CoreBankingService
from core_banking.client import CoreBankingClient
from backend.auth import auth_manager, AuthManager

app = FastAPI(
    title="Japanese Major Bank AI Assistant API",
    description="FISC, APPI, and FSA Compliant Japanese Major Bank AI Customer Portal API with Real-time SSE Streaming",
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

# Initialize singletons
input_guardrail = InputGuardrail()
output_guardrail = OutputGuardrail()
audit_logger = AuditLogger()
vector_store = VectorStore()
llm_client = get_llm_client()
core_banking_service = CoreBankingService()
core_banking_client = CoreBankingClient(service=core_banking_service)

# Fallback mock accounts data file
ACCOUNTS_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_bank_accounts.json"))


# ==============================================================================
# RFC 7807 Problem Details Error Handling (REQ-IF-015 §3)
# ==============================================================================

class BankingProblemDetailException(Exception):
    """RFC 7807 Problem Details Standard Exception."""

    def __init__(self, status_code: int, code: str, title: str, detail: str, instance: str = ""):
        self.status_code = status_code
        self.code = code
        self.title = title
        self.detail = detail
        self.instance = instance


@app.exception_handler(BankingProblemDetailException)
async def problem_details_handler(request: Request, exc: BankingProblemDetailException):
    instance_path = exc.instance or request.url.path
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "type": f"https://api.megabank.co.jp/errors/{exc.code}",
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": instance_path,
        "code": exc.code,
        "timestamp": timestamp
    }
    return JSONResponse(status_code=exc.status_code, content=payload, media_type="application/problem+json")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "INVALID_PAYLOAD",
        401: "AUTH_EXPIRED",
        403: "STEP_UP_REQUIRED",
        404: "RESOURCE_NOT_FOUND",
        422: "SECURITY_BLOCKED",
        503: "CORE_BANKING_TIMEOUT"
    }
    code = code_map.get(exc.status_code, "BANK_API_ERROR")
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "type": f"https://api.megabank.co.jp/errors/{code}",
        "title": str(exc.detail),
        "status": exc.status_code,
        "detail": str(exc.detail),
        "instance": request.url.path,
        "code": code,
        "timestamp": timestamp
    }
    return JSONResponse(status_code=exc.status_code, content=payload, media_type="application/problem+json")


# ==============================================================================
# Request / Response Schemas
# ==============================================================================

class ChatRequest(BaseModel):
    session_id: str = Field(default="SESS-88001", description="Client session identifier")
    customer_id: str = Field(default="CUST-1001", description="Registered customer identifier")
    message: str = Field(..., min_length=1, description="Customer message or banking question")

class ExtractionRequest(BaseModel):
    customer_id: str = "CUST-1001"

class TokenRequest(BaseModel):
    customer_id: str = "CUST-1001"
    tier: Optional[str] = "STANDARD"

class StepUpRequest(BaseModel):
    session_id: str = "SESS-CURRENT"
    action_type: Optional[str] = "FUND_TRANSFER"
    message: Optional[str] = "振込取引手続き"


def verify_request_auth(authorization: Optional[str], require_auth: bool = False) -> Optional[Dict[str, Any]]:
    """Helper to validate JWT token when present or required."""
    if not authorization:
        if require_auth:
            raise BankingProblemDetailException(
                status_code=401,
                code="AUTH_EXPIRED",
                title="Authentication Required",
                detail="JWT token is missing, expired, or invalid. Please authenticate."
            )
        return None

    try:
        payload = auth_manager.verify_token(authorization)
        return payload
    except ValueError as e:
        raise BankingProblemDetailException(
            status_code=401,
            code="AUTH_EXPIRED",
            title="Unauthorized Token",
            detail=str(e)
        )


# ==============================================================================
# Core & Health Endpoints
# ==============================================================================

@app.get("/api/health")
def health_check():
    provider_type = os.environ.get("LLM_PROVIDER", "bedrock").lower()
    model_name = getattr(llm_client, "model_name", "amazon.nova-lite-v1:0")
    cb_state = core_banking_client.circuit_breaker.state.value
    return {
        "status": "ONLINE",
        "region": "ap-northeast-1",
        "fisc_compliance": True,
        "llm_provider": provider_type,
        "llm_model": model_name,
        "core_banking_status": "CONNECTED" if cb_state == "CLOSED" else f"CIRCUIT_{cb_state}",
        "circuit_breaker": cb_state
    }

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
@app.get("/favicon.ico")
def suppress_dev_logs():
    return {}

# ==============================================================================
# Auth & Step-Up Endpoints (REQ-FUN-005, ADR-0014)
# ==============================================================================

@app.post("/api/auth/token")
def issue_token(req: TokenRequest):
    """Generate RFC 7519 JSON Web Token for Level 1 Inquiry Session."""
    token = auth_manager.create_token(customer_id=req.customer_id, tier=req.tier)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 1800,
        "customer_id": req.customer_id,
        "tier": req.tier,
        "auth_level": "LEVEL_1_INQUIRY"
    }

@app.post("/api/step-up-auth")
def step_up_auth_endpoint(req: StepUpRequest):
    """
    Step-Up MFA Challenge Initiation Endpoint (REQ-FUN-005 §3).
    Returns formal MFA challenge response and redirection target for sensitive transactions.
    """
    detected = auth_manager.detect_step_up_intent(req.message or req.action_type or "", req.session_id)
    if detected:
        return detected

    redirect_url = f"https://ib.megabank.co.jp/banking/auth/step-up?session_id={req.session_id}&auth_flow=mfa_step_up"
    return {
        "status": "STEP_UP_REQUIRED",
        "action_type": req.action_type or "TRANSACTION",
        "message": "振込や暗証番号の変更などのお取引・お手続きは、セキュリティ確保のためインターネットバンキングの公式取引画面にて多要素認証（ワンタイムパスワード等）が必要です。",
        "redirect_url": redirect_url,
        "required_auth_level": "MFA_HARDWARE_OR_BIOMETRIC"
    }

# ==============================================================================
# Core Banking System REST Endpoints (REQ-FUN-004)
# ==============================================================================

@app.get("/api/customers")
@app.get("/api/core/customers")
def list_customers():
    """List all customers registered in Core Banking DB."""
    return core_banking_service.get_all_customers()

@app.get("/api/core/customers/{customer_id}")
def core_get_customer_profile(customer_id: str):
    """Get detailed customer profile, account balances, and recent transactions."""
    profile = core_banking_client.get_customer_summary(customer_id)
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
    """Dedicated extraction API for AI Chat Bot with caching and circuit breaker."""
    return core_banking_client.extract_account_info(req.customer_id)

@app.get("/api/faq/search")
def search_faq(q: str):
    """Hybrid vector search over Rakuten Bank FAQ knowledge base."""
    return vector_store.search(query=q, top_k=5)

@app.get("/api/control-plane/logs")
def get_audit_logs():
    """Retrieve immutable audit logs."""
    return audit_logger.get_recent_logs(limit=25)


# ==============================================================================
# AI Chat Endpoints: SSE Streaming & Synchronous (REQ-IF-015, REQ-FUN-006)
# ==============================================================================

@app.post("/api/chat/stream")
async def chat_stream_endpoint(
    req: ChatRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None)
):
    """
    W3C Server-Sent Events (SSE) AI Chat Streaming Endpoint.
    Grounded in REQ-IF-015, REQ-FUN-006, and ADR-0013.
    Streams incremental chunks and real-time control plane events.
    """
    # Check optional strict token requirement (enforced if Authorization header is provided)
    auth_payload = verify_request_auth(authorization, require_auth=False)

    async def event_generator() -> AsyncGenerator[str, None]:
        session_id = req.session_id
        customer_id = req.customer_id
        user_msg = req.message

        # Gate 0: Step-Up MFA Check (REQ-FUN-005 §3)
        step_up_eval = auth_manager.detect_step_up_intent(user_msg, session_id)
        if step_up_eval:
            yield f'data: {{"type": "guardrail_status", "step_up_required": true, "action_type": "{step_up_eval["action_type"]}"}}\n\n'
            yield f'data: {{"type": "step_up_required", "payload": {json.dumps(step_up_eval, ensure_ascii=False)}}}\n\n'
            
            # Append prompt for client display
            msg = step_up_eval["message"]
            yield f'data: {{"type": "content_chunk", "delta": {json.dumps(msg, ensure_ascii=False)}}}\n\n'

            audit_logger.log_event(
                session_id=session_id,
                customer_id=customer_id,
                input_guardrail_result={"allowed": True, "step_up_triggered": True, "action": step_up_eval["action_type"]},
                output_guardrail_result={"validated_response": msg, "grounding_score": 1.0},
                rag_context_ids=[],
                model_name="rule-engine:step-up",
                latency_ms=5,
                token_usage={"input": len(user_msg), "output": len(msg)}
            )
            yield f'data: {{"type": "completion", "grounding_score": 1.0, "audit_id": "STEP-UP-OK"}}\n\n'
            return

        # Gate 1: In-VPC Input Guardrail (REQ-SEC-008, REQ-SEC-011)
        in_eval = input_guardrail.process_input(user_msg)
        yield f'data: {{"type": "guardrail_status", "input_guardrail": {json.dumps(in_eval, ensure_ascii=False)}}}\n\n'

        if not in_eval["allowed"]:
            blocked_msg = in_eval.get("rejection_message")
            if not blocked_msg:
                blocked_msg = f"【セキュリティ制御】{in_eval.get('reason')}。当行のセキュリティ規約に基づき処理を停止いたしました。"
            
            # Send content chunk and completion
            yield f'data: {{"type": "content_chunk", "delta": {json.dumps(blocked_msg, ensure_ascii=False)}}}\n\n'
            
            out_blocked = {
                "validated_response": blocked_msg,
                "grounding_score": 0.0,
                "pii_leak_prevented": False,
                "financial_advice_blocked": False,
                "disclaimer_appended": True,
                "warnings": [f"Input Guardrail Intervention: {in_eval.get('reason')}"]
            }
            audit_entry = audit_logger.log_event(
                session_id=session_id,
                customer_id=customer_id,
                input_guardrail_result=in_eval,
                output_guardrail_result=out_blocked,
                rag_context_ids=[],
                model_name="amazon.nova-lite-v1:0",
                latency_ms=10,
                token_usage={"input": len(user_msg), "output": 0}
            )
            yield f'data: {{"type": "completion", "grounding_score": 0.0, "audit_id": "{audit_entry["log_id"]}"}}\n\n'
            return

        # Step 2: Context Retrieval via Resilient Core Banking Client & FAQ Vector Search
        customer_account = core_banking_client.extract_account_info(customer_id)
        rag_matches = vector_store.search(in_eval["sanitized_prompt"], top_k=2)
        rag_context_ids = [m.get("id") for m in rag_matches if m.get("id")]

        # Step 3: LLM Generation (Bedrock Nova Lite or Local LLM Client fallback)
        llm_res = llm_client.generate_response(
            sanitized_prompt=in_eval["sanitized_prompt"],
            account_context=customer_account,
            rag_contexts=rag_matches
        )

        # Step 4: Output Guardrail Execution (Grounding score, FIEA filtering, PII scan)
        out_eval = output_guardrail.process_output(
            raw_llm_response=llm_res["text"],
            rag_contexts=rag_matches,
            user_prompt=user_msg,
            account_context=customer_account
        )

        # Step 5: FISC Audit Logging
        audit_entry = audit_logger.log_event(
            session_id=session_id,
            customer_id=customer_id,
            input_guardrail_result=in_eval,
            output_guardrail_result=out_eval,
            rag_context_ids=rag_context_ids,
            model_name=llm_res["model"],
            latency_ms=llm_res["latency_ms"],
            token_usage=llm_res["tokens"]
        )

        # Step 6: Stream Chunks smoothly (Simulate sub-second token streaming)
        final_text = out_eval["validated_response"]
        chunk_size = 18
        for i in range(0, len(final_text), chunk_size):
            chunk = final_text[i:i + chunk_size]
            payload = {"type": "content_chunk", "delta": chunk}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.02)  # 20ms pacing for natural streaming experience

        # Step 7: Final Completion Event with Grounding & Telemetry
        completion_data = {
            "type": "completion",
            "grounding_score": out_eval["grounding_score"],
            "audit_id": audit_entry["log_id"],
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
        yield f"data: {json.dumps(completion_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@app.post("/api/chat")
def chat_endpoint(
    req: ChatRequest,
    authorization: Optional[str] = Header(default=None)
):
    """
    Main Synchronous Chat Endpoint executing the full Control Plane & RAG pipeline:
    1. Step-Up MFA Intent Detection (REQ-FUN-005)
    2. Input Guardrail (PII Redaction & Prompt Injection Filter)
    3. Context Retrieval (Resilient Core Banking API Extraction + FAQ RAG Vector Search)
    4. Bedrock Amazon Nova Lite LLM Execution (or Local LLM Fallback)
    5. Output Guardrail (Grounding check, PII leak scan, Disclaimer append)
    6. FISC Audit Logger recording
    """
    # Verify optional authorization
    verify_request_auth(authorization, require_auth=False)

    # Step 0: Step-Up MFA Check
    step_up_eval = auth_manager.detect_step_up_intent(req.message, req.session_id)
    if step_up_eval:
        return {
            "reply": (
                f"{step_up_eval['message']}\n\n"
                f"【公式取引窓口】セキュリティ認証を行い、お手続きを進めてください。\n"
                f"{step_up_eval['redirect_url']}"
            ),
            "status": "STEP_UP_REQUIRED",
            "step_up": step_up_eval,
            "control_plane": {
                "input_guardrail": {"allowed": True, "step_up_triggered": True},
                "output_guardrail": {"grounding_score": 1.0, "disclaimer_appended": True},
                "rag_contexts": []
            }
        }

    # Step 1: Input Guardrail Execution
    in_eval = input_guardrail.process_input(req.message)
    if not in_eval["allowed"]:
        blocked_msg = in_eval.get("rejection_message")
        if not blocked_msg:
            blocked_msg = f"【セキュリティ制御】{in_eval.get('reason')}。当行のセキュリティ規約に基づき処理を停止いたしました。"
        out_blocked = {
            "validated_response": blocked_msg,
            "grounding_score": 0.0,
            "pii_leak_prevented": False,
            "financial_advice_blocked": False,
            "disclaimer_appended": True,
            "warnings": [f"Input Guardrail Intervention: {in_eval.get('reason')}"]
        }
        audit_entry = audit_logger.log_event(
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
            },
            "audit_log_id": audit_entry["log_id"]
        }

    # Step 2: Context Retrieval via Resilient Core Banking Extraction API Client
    customer_account = core_banking_client.extract_account_info(req.customer_id)
    rag_matches = vector_store.search(in_eval["sanitized_prompt"], top_k=2)
    rag_context_ids = [m.get("id") for m in rag_matches if m.get("id")]

    # Step 3: LLM Generation (Bedrock Nova Lite or Local LLM Client)
    llm_res = llm_client.generate_response(
        sanitized_prompt=in_eval["sanitized_prompt"],
        account_context=customer_account,
        rag_contexts=rag_matches
    )

    # Step 4: Output Guardrail Execution
    out_eval = output_guardrail.process_output(
        raw_llm_response=llm_res["text"],
        rag_contexts=rag_matches,
        user_prompt=req.message,
        account_context=customer_account
    )

    # Step 5: FISC Audit Logging
    audit_entry = audit_logger.log_event(
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
        },
        "audit_log_id": audit_entry["log_id"]
    }


# ==============================================================================
# Static File Hosting (Web Portals)
# ==============================================================================

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
