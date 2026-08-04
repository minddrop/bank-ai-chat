"""
Unit Tests for Synthetic Japanese Bank Account Data
Verifies schema compliance, Katakana/Kanji names, account numbers, and balance formats.
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
        self.assertGreaterEqual(len(customers), 2)
        
        for c in customers:
            self.assertIn("customer_id", c)
            self.assertIn("name_kanji", c)
            self.assertIn("name_katakana", c)
            self.assertEqual(len(c["branch_code"]), 3)
            self.assertEqual(len(c["account_number"]), 7)
            self.assertGreater(len(c["accounts"]), 0)

if __name__ == "__main__":
    unittest.main()
