"""
Unit Tests for Core Banking Database & Service Layer
Verifies SQLite table creation, customer profile queries, current balances, transaction history, and AI extraction payloads.
"""

import os
import sys
import unittest
import tempfile

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core_banking.database import init_db, get_db_connection
from core_banking.service import CoreBankingService
from core_banking.client import CoreBankingClient


class TestCoreBanking(unittest.TestCase):

    def setUp(self):
        # Use temporary file for test database
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        init_db(db_path=self.db_path, seed_if_empty=True)
        self.service = CoreBankingService(db_path=self.db_path)
        self.client = CoreBankingClient(service=self.service)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_database_tables_exist(self):
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()

        self.assertIn("customers", tables)
        self.assertIn("accounts", tables)
        self.assertIn("transactions", tables)

    def test_get_all_customers(self):
        customers = self.service.get_all_customers()
        self.assertGreaterEqual(len(customers), 5)
        for cust in customers:
            self.assertIn("customer_id", cust)
            self.assertIn("name_kanji", cust)
            self.assertIn("name_katakana", cust)

    def test_get_customer_profile_and_balances(self):
        profile = self.service.get_customer_profile("CUST-1001")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["customer_id"], "CUST-1001")
        self.assertEqual(profile["name_kanji"], "山田 太郎")
        self.assertGreaterEqual(len(profile["accounts"]), 3)

        balances = self.service.get_account_balances("CUST-1001")
        self.assertGreaterEqual(len(balances), 3)

        savings_acc = next((a for a in balances if a["account_type_code"] == "SAVINGS"), None)
        self.assertIsNotNone(savings_acc)
        self.assertEqual(savings_acc["currency"], "JPY")
        self.assertGreater(savings_acc["balance"], 0)

    def test_get_transaction_history(self):
        txns = self.service.get_transaction_history("CUST-1001", limit=10)
        self.assertGreaterEqual(len(txns), 5)
        for tx in txns:
            self.assertIn("transaction_id", tx)
            self.assertIn("date", tx)
            self.assertIn("type", tx)
            self.assertIn("amount", tx)
            self.assertIn("balance_after", tx)

    def test_extract_account_info_for_ai(self):
        info = self.client.extract_account_info("CUST-1001")
        self.assertEqual(info["status"], "SUCCESS")
        self.assertEqual(info["customer_id"], "CUST-1001")
        self.assertIn("primary_savings_balance", info)
        self.assertIn("accounts_summary", info)
        self.assertIn("recent_transactions", info)


if __name__ == "__main__":
    unittest.main()
