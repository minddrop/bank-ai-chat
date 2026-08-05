"""
Unit Tests for Synthetic Japanese Bank Account Data
Verifies schema compliance, Katakana/Kanji names, account numbers, balance formats, and transaction history details.
"""

import json
import os
import unittest

DATA_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "mock_bank_accounts.json"))

class TestAccountData(unittest.TestCase):

    def test_mock_account_schema(self):
        self.assertTrue(os.path.exists(DATA_FILE))
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.assertIn("bank_info", data)
        self.assertTrue(data["bank_info"]["fisc_compliance_mode"])
        
        customers = data.get("customers", [])
        self.assertGreaterEqual(len(customers), 5)
        
        for c in customers:
            self.assertIn("customer_id", c)
            self.assertIn("name_kanji", c)
            self.assertIn("name_katakana", c)
            self.assertEqual(len(c["branch_code"]), 3)
            self.assertEqual(len(c["account_number"]), 7)
            self.assertGreater(len(c["accounts"]), 0)

            # Test accounts and current balance
            for acc in c["accounts"]:
                self.assertIn("account_id", acc)
                self.assertIn("account_type", acc)
                self.assertIn("balance", acc)
                self.assertIsInstance(acc["balance"], (int, float))
                self.assertIn("currency", acc)

            # Test transaction history
            txns = c.get("recent_transactions", [])
            self.assertGreaterEqual(len(txns), 5)
            for tx in txns:
                self.assertIn("transaction_id", tx)
                self.assertIn("date", tx)
                self.assertIn("type", tx)
                self.assertIn("amount", tx)
                self.assertIsInstance(tx["amount"], (int, float))
                self.assertIn("description", tx)
                self.assertIn("balance_after", tx)
                self.assertIsInstance(tx["balance_after"], (int, float))

if __name__ == "__main__":
    unittest.main()

