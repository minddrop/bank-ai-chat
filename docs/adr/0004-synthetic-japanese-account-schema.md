# ADR 0004: Synthetic Japanese Bank Account Data Schema

* **Status**: Accepted
* **Date**: 2026-08-04
* **Deciders**: AI Bank Engineering Team, Lead Data Engineer

## Context & Problem Statement
Due to strict APPI data protection regulations and bank confidentiality rules, actual customer account databases cannot be accessed or used during POC development. However, the AI assistant must demonstrate realistic account inquiry handling (balance checks, transaction history, fixed-term deposits).

## Decision Drivers
* Need for realistic Japanese banking domain structures (普通預金, 定期預金, 外貨預金, カタカナ名義, 7桁口座番号, 3桁支店コード).
* Zero exposure of real customer PII.
* Support for multi-customer simulation in the UI portal.

## Decision Outcome
Chosen Solution: **Synthetic APPI-Compliant Mock Account JSON Generator**.

### Schema Definition (`data/mock_bank_accounts.json`):
* `customer_id`: Unique synthetic ID (e.g. `CUST-1001`).
* `name_kanji` & `name_katakana`: Realistic synthetic Japanese names (e.g. `ヤマダ タロウ`).
* `branch_code` & `branch_name`: Standard 3-digit branch code (e.g. `001 サクラ支店`).
* `account_number`: Standard 7-digit account number (e.g. `1234567`).
* `accounts`: Array of sub-accounts (Ordinary Savings 普通, Time Deposit 定期, Foreign Currency 外貨).
* `recent_transactions`: Multi-month transaction records (ATM withdrawal, salary deposit 振込, auto-debit).

## Consequences
* **Positive**: 100% realistic customer experience without any risk of APPI violation or real data exposure.
* **Negative**: Requires maintaining synthetic mock schema generators.
