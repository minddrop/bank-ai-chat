"""
Automated Unit and Integration Tests for Banking Chaos Engineering Subsystem
Verifies compliance with FISC Safety Standards (第9版 コンティンジェンシープラン策定基準),
APPI Zero-PII Invariant, and RFC 7807 Problem Details.
"""

import json
import os
import sys
import time
import unittest
from fastapi.testclient import TestClient

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from backend.app import app, core_banking_client, audit_logger
from chaos import (
    ChaosScenario,
    SCENARIO_CATALOG,
    FaultInjector,
    SteadyStateEvaluator,
    chaos_manager,
)
from control_plane.audit_logger import AuditStorageExhaustedException


class TestChaosEngineering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["LLM_PROVIDER"] = "local"
        cls.client = TestClient(app)

    def setUp(self):
        FaultInjector.reset_all_faults()
        core_banking_client.circuit_breaker.reset()
        core_banking_client.clear_cache()

    def tearDown(self):
        FaultInjector.reset_all_faults()
        core_banking_client.circuit_breaker.reset()
        core_banking_client.clear_cache()

    # --------------------------------------------------------------------------
    # 1. Fault Injector & Catalog Tests
    # --------------------------------------------------------------------------

    def test_chaos_scenario_catalog_integrity(self):
        """Verify all scenarios in catalog have valid metadata, strategy, and FISC references."""
        self.assertGreaterEqual(len(SCENARIO_CATALOG), 10)
        for scenario_enum, defn in SCENARIO_CATALOG.items():
            self.assertEqual(scenario_enum.value, defn.scenario_id)
            self.assertTrue(len(defn.name_ja) > 0)
            self.assertTrue(len(defn.name_en) > 0)
            self.assertIn(defn.strategy.value, ["FAIL_CLOSED", "GRACEFUL_DEGRADE", "BUFFER_AND_RETRY"])
            self.assertTrue("FISC" in defn.fisc_reference or "個人情報保護法" in defn.fisc_reference or "金融庁" in defn.fisc_reference or "非機能" in defn.fisc_reference)

    def test_fault_injector_latency_and_exception(self):
        """Test unit behavior of FaultInjector."""
        # When inactive
        start = time.time()
        injected = FaultInjector.inject_latency("CORE_BANKING_TIMEOUT", 0.2)
        self.assertFalse(injected)
        self.assertLess(time.time() - start, 0.1)

        # Enable global scenario
        FaultInjector.enable_global_scenario("CORE_BANKING_TIMEOUT")
        self.assertTrue(FaultInjector.is_scenario_active("CORE_BANKING_TIMEOUT"))

        # Injected latency
        start = time.time()
        injected = FaultInjector.inject_latency("CORE_BANKING_TIMEOUT", 0.1)
        self.assertTrue(injected)
        self.assertGreaterEqual(time.time() - start, 0.08)

        # Exception injection
        with self.assertRaises(ConnectionResetError):
            FaultInjector.inject_exception("CORE_BANKING_TIMEOUT", ConnectionResetError("Simulated reset"))

        # Reset
        FaultInjector.reset_all_faults()
        self.assertFalse(FaultInjector.is_scenario_active("CORE_BANKING_TIMEOUT"))

    # --------------------------------------------------------------------------
    # 2. Steady-State Invariant Evaluator Tests
    # --------------------------------------------------------------------------

    def test_steady_state_evaluator_clean_response(self):
        """Clean banking response must pass all invariants."""
        payload = {
            "reply": "普通預金の残高は 1,250,000 円でございます。【重要事項・免責事項】...",
            "status": "SUCCESS"
        }
        report = SteadyStateEvaluator.evaluate_response(payload, status_code=200, latency_ms=120.0)
        self.assertTrue(report.is_healthy)
        self.assertEqual(report.failed_checks, 0)
        self.assertEqual(report.fisc_compliance_status, "COMPLIANT")

    def test_steady_state_evaluator_detects_pii_leak(self):
        """Raw unmasked account number or PIN must trigger CRITICAL APPI violation."""
        leaked_payload = {
            "reply": "お客様の口座番号 1234567 の暗証番号 9876 を確認しました。"
        }
        report = SteadyStateEvaluator.evaluate_response(leaked_payload, status_code=200)
        self.assertFalse(report.is_healthy)
        pii_violation = next((r for r in report.results if r.invariant_name == "ZERO_PII_LEAKAGE"), None)
        self.assertIsNotNone(pii_violation)
        self.assertFalse(pii_violation.passed)
        self.assertEqual(pii_violation.severity, "CRITICAL")

    def test_steady_state_evaluator_detects_stack_trace_leak(self):
        """Internal python stack traces must be detected and rejected."""
        error_payload = "Traceback (most recent call last):\n  File 'app.py', line 45, in generate\nZeroDivisionError: division by zero"
        report = SteadyStateEvaluator.evaluate_response(error_payload, status_code=500)
        self.assertFalse(report.is_healthy)
        stack_violation = next((r for r in report.results if r.invariant_name == "NO_STACK_TRACE_LEAK"), None)
        self.assertIsNotNone(stack_violation)
        self.assertFalse(stack_violation.passed)

    # --------------------------------------------------------------------------
    # 3. Core Banking Resilience & Fault Injection Tests
    # --------------------------------------------------------------------------

    def test_core_banking_timeout_chaos_via_header(self):
        """
        Inject CORE_BANKING_TIMEOUT via HTTP header:
        - Request completes successfully (200 OK).
        - Degraded notice is returned (残高照会システムメンテナンス中).
        - Zero PII leaks into response.
        """
        payload = {
            "session_id": "CHAOS-SESS-01",
            "customer_id": "CUST-1001",
            "message": "現在の普通預金の残高を教えてください"
        }
        headers = {"X-Chaos-Scenario": "CORE_BANKING_TIMEOUT"}
        res = self.client.post("/api/chat", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Chaos-Injected"), "CORE_BANKING_TIMEOUT")

        data = res.json()
        self.assertIn("reply", data)
        # Should gracefully communicate maintenance
        self.assertTrue(
            "メンテナンス中" in data["reply"] or "残高" in data["reply"]
        )
        self.assertIn("【重要事項・免責事項】", data["reply"])

        # Steady-state evaluation
        report = SteadyStateEvaluator.evaluate_response(data, status_code=200)
        self.assertTrue(report.is_healthy)

    def test_core_banking_db_crash_chaos(self):
        """
        Inject CORE_BANKING_DB_CRASH:
        - Circuit breaker records failure.
        - Graceful degradation payload returned.
        """
        FaultInjector.enable_global_scenario("CORE_BANKING_DB_CRASH")
        payload = {
            "session_id": "CHAOS-SESS-02",
            "customer_id": "CUST-1001",
            "message": "残高照会をお願いします"
        }
        res = self.client.post("/api/chat", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reply", data)

        # Verify circuit breaker failure was recorded
        self.assertGreaterEqual(core_banking_client.circuit_breaker.consecutive_failures, 1)

    # --------------------------------------------------------------------------
    # 4. Amazon Bedrock LLM Fault Injection Tests
    # --------------------------------------------------------------------------

    def test_bedrock_429_throttling_chaos(self):
        """
        Inject BEDROCK_429_THROTTLING:
        - System falls back to local/resilient response without exposing raw AWS ClientError.
        """
        headers = {"X-Chaos-Scenario": "BEDROCK_429_THROTTLING"}
        payload = {
            "session_id": "CHAOS-SESS-03",
            "customer_id": "CUST-1001",
            "message": "他行振込手数料を教えてください"
        }
        res = self.client.post("/api/chat", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reply", data)
        self.assertNotIn("botocore.exceptions", data["reply"])

        # Verify steady-state
        report = SteadyStateEvaluator.evaluate_response(data, status_code=200)
        self.assertTrue(report.is_healthy)

    def test_bedrock_500_outage_chaos(self):
        """
        Inject BEDROCK_OUTAGE_500:
        - System provides courteous apology message with customer contact number.
        """
        headers = {"X-Chaos-Scenario": "BEDROCK_OUTAGE_500"}
        payload = {
            "session_id": "CHAOS-SESS-04",
            "customer_id": "CUST-1001",
            "message": "定期預金の金利について"
        }
        res = self.client.post("/api/chat", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reply", data)
        self.assertTrue(
            "定期点検中" in data["reply"] or "通信障害" in data["reply"] or "テレフォンバンキング" in data["reply"]
        )

    # --------------------------------------------------------------------------
    # 5. FISC Audit Logger Resilience & Fail-Closed Tests
    # --------------------------------------------------------------------------

    def test_audit_logger_storage_failure_buffering_and_flush(self):
        """
        When AUDIT_STORAGE_FAILURE is active:
        - Events are safely buffered in memory queue (REQ-NFR-007 Phase 5 Buffer Mode).
        - Flushing buffer empties queue and writes to storage.
        """
        initial_buf = audit_logger.get_buffer_size()
        FaultInjector.enable_global_scenario("AUDIT_STORAGE_FAILURE")

        entry = audit_logger.log_event(
            session_id="CHAOS-AUDIT-01",
            customer_id="CUST-1001",
            input_guardrail_result={"sanitized_prompt": "テスト", "allowed": True},
            output_guardrail_result={"validated_response": "テスト回答", "grounding_score": 1.0},
            rag_context_ids=[],
            model_name="mock-model",
            latency_ms=20,
            token_usage={"input": 10, "output": 10}
        )
        self.assertIn("log_id", entry)
        self.assertGreater(audit_logger.get_buffer_size(), initial_buf)

        # Deactivate fault and flush
        FaultInjector.disable_global_scenario("AUDIT_STORAGE_FAILURE")
        flushed = audit_logger.flush_buffer()
        self.assertGreaterEqual(flushed, 1)
        self.assertEqual(audit_logger.get_buffer_size(), 0)

    def test_audit_logger_buffer_overflow_fails_closed(self):
        """
        If memory buffer capacity is exceeded during prolonged storage failure:
        - AuditLogger raises AuditStorageExhaustedException (Fail-Closed, ADR-0018 P0).
        """
        small_logger = type(audit_logger)(max_buffer_capacity=2)
        FaultInjector.enable_global_scenario("AUDIT_STORAGE_FAILURE")

        # First 2 logs buffer successfully
        small_logger.log_event("S1", "C1", {}, {}, [], "m", 10, {})
        small_logger.log_event("S2", "C1", {}, {}, [], "m", 10, {})

        # 3rd log exceeds capacity of 2 -> Must fail closed
        with self.assertRaises(AuditStorageExhaustedException):
            small_logger.log_event("S3", "C1", {}, {}, [], "m", 10, {})

        FaultInjector.disable_global_scenario("AUDIT_STORAGE_FAILURE")

    # --------------------------------------------------------------------------
    # 6. Chaos Management API Endpoints
    # --------------------------------------------------------------------------

    def test_chaos_api_list_scenarios(self):
        res = self.client.get("/api/chaos/scenarios")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["enabled"])
        self.assertGreaterEqual(len(data["scenarios"]), 10)
        scenario_ids = [s["scenario_id"] for s in data["scenarios"]]
        self.assertIn("CORE_BANKING_TIMEOUT", scenario_ids)
        self.assertIn("BEDROCK_429_THROTTLING", scenario_ids)

    def test_chaos_api_status(self):
        res = self.client.get("/api/chaos/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("chaos_enabled", data)
        self.assertIn("circuit_breaker_state", data)
        self.assertIn("audit_buffer_size", data)

    def test_chaos_api_enable_disable_reset(self):
        # Enable
        res = self.client.post("/api/chaos/enable", json={"scenario": "CORE_BANKING_TIMEOUT"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(FaultInjector.is_scenario_active("CORE_BANKING_TIMEOUT"))

        # Disable
        res = self.client.post("/api/chaos/disable", json={"scenario": "CORE_BANKING_TIMEOUT"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(FaultInjector.is_scenario_active("CORE_BANKING_TIMEOUT"))

        # Reset
        res = self.client.post("/api/chaos/reset")
        self.assertEqual(res.status_code, 200)

    def test_chaos_api_simulate_endpoint(self):
        res = self.client.post(
            "/api/chaos/simulate",
            json={
                "scenario": "CORE_BANKING_TIMEOUT",
                "customer_id": "CUST-1001",
                "message": "普通預金残高を教えて"
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["scenario"], "CORE_BANKING_TIMEOUT")
        self.assertIn(data["status"], ["PASSED", "RUNNING"])
        self.assertIn("steady_state_report", data)
        self.assertTrue(data["steady_state_report"]["is_healthy"])

    def test_chaos_api_steady_state_check(self):
        res = self.client.get("/api/chaos/steady-state")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_healthy"])
        self.assertEqual(data["fisc_compliance_status"], "COMPLIANT")


if __name__ == "__main__":
    unittest.main()
