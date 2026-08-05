"""
Core Banking System Database Module
Manages SQLite schema for customers, account balances, and transaction history.
"""

import json
import os
import sqlite3
from typing import Dict, Any, List, Optional

DB_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "bank_core.db"))
MOCK_FILE = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "mock_bank_accounts.json"))


def get_db_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_FILE, seed_if_empty: bool = True) -> None:
    """Creates customers, accounts, and transactions tables and seeds default data if empty."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        name_kanji TEXT NOT NULL,
        name_katakana TEXT NOT NULL,
        birth_date TEXT,
        branch_code TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        account_number TEXT NOT NULL,
        customer_tier TEXT DEFAULT 'STANDARD',
        happy_program_stage TEXT,
        direct_banking_status TEXT DEFAULT 'ACTIVE'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_type TEXT NOT NULL,
        account_type_code TEXT NOT NULL,
        balance REAL NOT NULL DEFAULT 0.0,
        currency TEXT NOT NULL DEFAULT 'JPY',
        interest_rate TEXT,
        maturity_date TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'JPY',
        description TEXT NOT NULL,
        balance_after REAL NOT NULL,
        FOREIGN KEY (account_id) REFERENCES accounts (account_id),
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    )
    """)

    conn.commit()

    if seed_if_empty:
        cursor.execute("SELECT COUNT(*) as count FROM customers")
        count = cursor.fetchone()["count"]
        if count == 0:
            seed_db_from_mock_json(conn)

    conn.close()


def seed_db_from_mock_json(conn: sqlite3.Connection) -> None:
    if not os.path.exists(MOCK_FILE):
        return

    with open(MOCK_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cursor = conn.cursor()

    for cust in data.get("customers", []):
        cursor.execute("""
        INSERT OR REPLACE INTO customers (
            customer_id, name_kanji, name_katakana, birth_date,
            branch_code, branch_name, account_number, customer_tier,
            happy_program_stage, direct_banking_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cust["customer_id"],
            cust.get("name_kanji", ""),
            cust.get("name_katakana", ""),
            cust.get("birth_date", ""),
            cust.get("branch_code", "001"),
            cust.get("branch_name", "本店営業部"),
            cust.get("account_number", "1234567"),
            cust.get("customer_tier", "STANDARD"),
            cust.get("happy_program_stage", ""),
            cust.get("direct_banking_status", "ACTIVE")
        ))

        # Insert accounts
        for acc in cust.get("accounts", []):
            cursor.execute("""
            INSERT OR REPLACE INTO accounts (
                account_id, customer_id, account_type, account_type_code,
                balance, currency, interest_rate, maturity_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                acc["account_id"],
                cust["customer_id"],
                acc.get("account_type", "普通預金"),
                acc.get("account_type_code", "SAVINGS"),
                acc.get("balance", 0.0),
                acc.get("currency", "JPY"),
                acc.get("interest_rate", "0.02%"),
                acc.get("maturity_date")
            ))

        # Insert transactions (link to primary SAVINGS account if not explicit)
        primary_acc_id = cust["accounts"][0]["account_id"] if cust.get("accounts") else f"ACC-{cust['customer_id']}-SAV"
        for tx in cust.get("recent_transactions", []):
            cursor.execute("""
            INSERT OR REPLACE INTO transactions (
                transaction_id, account_id, customer_id, date, type,
                amount, currency, description, balance_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx["transaction_id"],
                primary_acc_id,
                cust["customer_id"],
                tx.get("date", ""),
                tx.get("type", "普通預金"),
                tx.get("amount", 0.0),
                tx.get("currency", "JPY"),
                tx.get("description", ""),
                tx.get("balance_after", 0.0)
            ))

    conn.commit()
