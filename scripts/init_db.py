#!/usr/bin/env python3
"""
CLI Script to Initialize and Seed the Core Banking Database (data/bank_core.db)
"""

import os
import sys

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core_banking.database import init_db, DB_FILE

def main():
    print(f"Initializing Core Banking SQLite Database at {DB_FILE}...")
    init_db(seed_if_empty=True)
    print("Core Banking Database successfully initialized and seeded.")

if __name__ == "__main__":
    main()
