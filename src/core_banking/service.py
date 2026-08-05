"""
Core Banking System Service Layer
Provides data query and business logic interfaces for Account Balances, Customer Profile, and Transaction History.
"""

from typing import Dict, Any, List, Optional
from core_banking.database import get_db_connection, init_db, DB_FILE


class CoreBankingService:

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        init_db(self.db_path, seed_if_empty=True)

    def get_all_customers(self) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers ORDER BY customer_id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_customer_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        cust = cursor.fetchone()
        if not cust:
            conn.close()
            return None

        cust_dict = dict(cust)
        # Attach accounts
        cursor.execute("SELECT * FROM accounts WHERE customer_id = ?", (customer_id,))
        cust_dict["accounts"] = [dict(acc) for acc in cursor.fetchall()]

        # Attach recent transactions
        cursor.execute("SELECT * FROM transactions WHERE customer_id = ? ORDER BY date DESC, transaction_id DESC LIMIT 20", (customer_id,))
        cust_dict["recent_transactions"] = [dict(tx) for tx in cursor.fetchall()]

        conn.close()
        return cust_dict

    def get_account_balances(self, customer_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE customer_id = ?", (customer_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_transaction_history(
        self,
        customer_id: str,
        account_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        if account_id:
            cursor.execute(
                "SELECT * FROM transactions WHERE customer_id = ? AND account_id = ? ORDER BY date DESC, transaction_id DESC LIMIT ?",
                (customer_id, account_id, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM transactions WHERE customer_id = ? ORDER BY date DESC, transaction_id DESC LIMIT ?",
                (customer_id, limit)
            )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def extract_account_info_for_ai(self, customer_id: str) -> Dict[str, Any]:
        """
        High-level extraction interface for AI Chat Bot to securely extract
        account summary, current balances, and recent transaction records.
        """
        profile = self.get_customer_profile(customer_id)
        if not profile:
            return {"status": "NOT_FOUND", "message": f"Customer {customer_id} not found."}

        balances = self.get_account_balances(customer_id)
        transactions = self.get_transaction_history(customer_id, limit=10)

        # Form formatted summary strings for JPY and foreign accounts
        savings_balance = next((a["balance"] for a in balances if a["account_type_code"] == "SAVINGS"), 0.0)
        formatted_balances = [
            {
                "account_id": a["account_id"],
                "account_type": a["account_type"],
                "currency": a["currency"],
                "balance": a["balance"],
                "interest_rate": a.get("interest_rate", "")
            }
            for a in balances
        ]

        return {
            "status": "SUCCESS",
            "customer_id": profile["customer_id"],
            "name_katakana": profile["name_katakana"],
            "name_kanji": profile["name_kanji"],
            "branch_name": profile["branch_name"],
            "branch_code": profile["branch_code"],
            "account_number": profile["account_number"],
            "customer_tier": profile["customer_tier"],
            "primary_savings_balance": savings_balance,
            "accounts_summary": formatted_balances,
            "recent_transactions": transactions
        }
