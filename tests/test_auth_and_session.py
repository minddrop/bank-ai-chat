"""
Unit Tests for Authentication, Authorization & Step-Up MFA
Verifies compliance with REQ-FUN-005, NIST SP 800-63B, and ADR-0014.
"""

import os
import sys
import time
import unittest

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from backend.auth import AuthManager, auth_manager


class TestAuthAndSession(unittest.TestCase):

    def setUp(self):
        self.mgr = AuthManager(secret_key=b"TEST_SECRET_KEY_FOR_UNITTESTS_2026", ttl_seconds=3)

    def test_token_creation_and_verification(self):
        token = self.mgr.create_token(customer_id="CUST-1001", tier="SUPER_VIP")
        self.assertIsInstance(token, str)
        self.assertEqual(len(token.split(".")), 3)

        payload = self.mgr.verify_token(token)
        self.assertEqual(payload["sub"], "CUST-1001")
        self.assertEqual(payload["tier"], "SUPER_VIP")
        self.assertEqual(payload["auth_level"], "LEVEL_1_INQUIRY")
        self.assertIn("jti", payload)
        self.assertIn("exp", payload)

    def test_bearer_prefix_support(self):
        token = self.mgr.create_token(customer_id="CUST-1002")
        bearer_token = f"Bearer {token}"
        payload = self.mgr.verify_token(bearer_token)
        self.assertEqual(payload["sub"], "CUST-1002")

    def test_token_expiration(self):
        short_mgr = AuthManager(secret_key=b"TEST_EXPIRY_KEY", ttl_seconds=1)
        token = short_mgr.create_token(customer_id="CUST-1003")
        # Sleep for 1.5 seconds to trigger expiration
        time.sleep(1.5)

        with self.assertRaises(ValueError) as ctx:
            short_mgr.verify_token(token)
        self.assertIn("AUTH_EXPIRED", str(ctx.exception))

    def test_tampered_token_rejected(self):
        token = self.mgr.create_token(customer_id="CUST-1001")
        parts = token.split(".")
        # Tamper payload part
        tampered_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"

        with self.assertRaises(ValueError) as ctx:
            self.mgr.verify_token(tampered_token)
        self.assertIn("AUTH_INVALID_SIGNATURE", str(ctx.exception))

    def test_invalid_format_token(self):
        with self.assertRaises(ValueError) as ctx:
            self.mgr.verify_token("not-a-jwt-token")
        self.assertIn("AUTH_INVALID_FORMAT", str(ctx.exception))

    def test_token_revocation_blacklist(self):
        token = self.mgr.create_token(customer_id="CUST-1004")
        # First verification succeeds
        payload = self.mgr.verify_token(token)
        self.assertIsNotNone(payload)

        # Revoke token
        revoked = self.mgr.revoke_token(token)
        self.assertTrue(revoked)

        # Second verification fails
        with self.assertRaises(ValueError) as ctx:
            self.mgr.verify_token(token)
        self.assertIn("AUTH_REVOKED", str(ctx.exception))

    def test_step_up_intent_fund_transfer(self):
        res = self.mgr.detect_step_up_intent("10万円を山田さんに振込をしてください", session_id="SESS-001")
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "STEP_UP_REQUIRED")
        self.assertEqual(res["action_type"], "FUND_TRANSFER")
        self.assertIn("transfer", res["redirect_url"])
        self.assertIn("SESS-001", res["redirect_url"])
        self.assertEqual(res["required_auth_level"], "MFA_HARDWARE_OR_BIOMETRIC")

    def test_step_up_intent_pin_change(self):
        res = self.mgr.detect_step_up_intent("暗証番号を変更したいのですが", session_id="SESS-002")
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "STEP_UP_REQUIRED")
        self.assertEqual(res["action_type"], "PIN_CHANGE")
        self.assertIn("pin-change", res["redirect_url"])

    def test_step_up_intent_account_closure(self):
        res = self.mgr.detect_step_up_intent("定期預金解約の手続きをお願いします")
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "STEP_UP_REQUIRED")
        self.assertEqual(res["action_type"], "TIME_DEPOSIT_CANCEL")

    def test_safe_inquiry_does_not_trigger_step_up(self):
        queries = [
            "現在の普通預金残高を教えてください",
            "他行宛の振込手数料はいくらですか？",
            "ハッピープログラムのスーパーVIPになる条件は何ですか？",
            "直近の入出金明細を確認したいです",
        ]
        for q in queries:
            res = self.mgr.detect_step_up_intent(q)
            # Safe questions should not trigger step-up redirect
            self.assertIsNone(res, f"Unexpected step-up trigger for query: {q}")


if __name__ == "__main__":
    unittest.main()
