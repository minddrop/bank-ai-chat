"""
Unit Tests for Core Banking Resilience & Circuit Breaker
Verifies compliance with REQ-FUN-004, REQ-IF-016, and ADR-0008.
Tests in-memory caching, 1.5s timeout handling, circuit states (CLOSED, OPEN, HALF_OPEN),
and graceful degradation behavior.
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core_banking.client import (
    CoreBankingClient,
    CircuitBreaker,
    CircuitState,
    CoreBankingTimeoutException,
    CoreBankingCircuitBreakerOpenException,
)


class TestCircuitBreaker(unittest.TestCase):

    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

    def test_consecutive_failure_trips_to_open(self):
        cb = CircuitBreaker(consecutive_limit=3)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

    def test_recovery_transition_to_half_open_and_closed(self):
        # Short open duration of 0.2s for rapid testing
        cb = CircuitBreaker(consecutive_limit=2, open_wait_seconds=0.2)
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.can_execute())

        # Wait for recovery timeout
        time.sleep(0.25)
        self.assertTrue(cb.can_execute())
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Successful probe call closes circuit
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.can_execute())

    def test_failed_probe_in_half_open_reopens_circuit(self):
        cb = CircuitBreaker(consecutive_limit=2, open_wait_seconds=0.2)
        cb.record_failure()
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)

        time.sleep(0.25)
        self.assertTrue(cb.can_execute())
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)

        # Failed probe trips right back to OPEN
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)


class TestCoreBankingClientResilience(unittest.TestCase):

    def test_in_memory_cache_hit_and_ttl(self):
        mock_service = MagicMock()
        mock_service.get_customer_profile.return_value = {
            "customer_id": "CUST-1001",
            "name_kanji": "山田 太郎"
        }

        # Short TTL of 0.3 seconds for test
        client = CoreBankingClient(service=mock_service, cache_ttl_seconds=0.3)

        # Call 1: Fetches from service
        res1 = client.get_customer_summary("CUST-1001")
        self.assertEqual(res1["customer_id"], "CUST-1001")
        self.assertEqual(mock_service.get_customer_profile.call_count, 1)

        # Call 2: Within TTL -> Hits cache without invoking service
        res2 = client.get_customer_summary("CUST-1001")
        self.assertEqual(res2["customer_id"], "CUST-1001")
        self.assertEqual(mock_service.get_customer_profile.call_count, 1)

        # Sleep past TTL
        time.sleep(0.35)

        # Call 3: Cache expired -> Calls service again
        res3 = client.get_customer_summary("CUST-1001")
        self.assertEqual(res3["customer_id"], "CUST-1001")
        self.assertEqual(mock_service.get_customer_profile.call_count, 2)

    def test_timeout_and_graceful_degradation(self):
        mock_service = MagicMock()

        def slow_call(*args, **kwargs):
            time.sleep(0.5)
            return {"customer_id": "CUST-1001"}

        mock_service.extract_account_info_for_ai.side_effect = slow_call

        # Client with 0.2s timeout
        client = CoreBankingClient(
            service=mock_service,
            call_timeout_seconds=0.2,
            circuit_breaker=CircuitBreaker(consecutive_limit=3, call_timeout_seconds=0.2)
        )

        res = client.extract_account_info("CUST-1001")
        self.assertEqual(res["status"], "DEGRADED")
        self.assertTrue(res["is_degraded"])
        self.assertIn("メンテナンス中", res["degradation_message"])
        self.assertIsNone(res["primary_savings_balance"])

    def test_circuit_breaker_open_returns_degraded_response_immediately(self):
        mock_service = MagicMock()
        mock_service.extract_account_info_for_ai.side_effect = Exception("Database connection failure")

        cb = CircuitBreaker(consecutive_limit=2, open_wait_seconds=10.0)
        client = CoreBankingClient(service=mock_service, circuit_breaker=cb)

        # Fail twice to trip circuit breaker
        client.extract_account_info("CUST-1001")
        client.extract_account_info("CUST-1001")
        self.assertEqual(cb.state, CircuitState.OPEN)

        # Third call: Circuit is OPEN, mock_service should not be called again
        initial_count = mock_service.extract_account_info_for_ai.call_count
        res = client.extract_account_info("CUST-1001")
        self.assertEqual(mock_service.extract_account_info_for_ai.call_count, initial_count)
        self.assertEqual(res["status"], "DEGRADED")
        self.assertEqual(res["circuit_breaker_state"], "OPEN")
        self.assertIn("メンテナンス中", res["degradation_message"])


if __name__ == "__main__":
    unittest.main()
