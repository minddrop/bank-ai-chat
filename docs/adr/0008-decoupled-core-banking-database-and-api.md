# ADR 0008: Decoupled Core Banking Database and Extraction REST API

* **Status**: Accepted
* **Date**: 2026-08-05
* **Deciders**: AI Bank Engineering Team, Lead Solutions Architect

## Context & Problem Statement
The AI Customer Chat System requires access to real-time customer account balances, basic profile details, and transaction history. However, running AI chat queries directly against core banking operational files violates architectural boundary separation principles. The core banking main system must operate independently with an explicit database schema and REST API endpoints for customer balance checking and transaction queries.

## Decision Drivers
* Strict architectural boundary separation between Core Banking Systems (勘定系) and AI Assistant Control Planes.
* Explicit database schema for accounts, customers, and multi-month transaction histories (`customers`, `accounts`, `transactions` tables).
* Standard REST API endpoints (`/api/core/*`) providing secure data extraction interfaces for microservices and AI chatbots.
* Full FISC and APPI compliance for customer PII protection.

## Decision Outcome
Chosen Solution: **SQLite Core Banking Database (`data/bank_core.db`) with `CoreBankingService` & `CoreBankingClient` REST APIs**.

### Database Schema Definition:
* `customers`: `customer_id`, `name_kanji`, `name_katakana`, `birth_date`, `branch_code`, `branch_name`, `account_number`, `customer_tier`, `happy_program_stage`, `direct_banking_status`.
* `accounts`: `account_id`, `customer_id`, `account_type` (普通預金, 定期預金, 外貨預金), `account_type_code`, `balance`, `currency`, `interest_rate`, `maturity_date`.
* `transactions`: `transaction_id`, `account_id`, `customer_id`, `date`, `type` (振込入金, 給与振込, デビット決済, etc.), `amount`, `currency`, `description`, `balance_after`.

### REST API Endpoints:
* `GET /api/core/customers`: List registered banking customers.
* `GET /api/core/customers/{customer_id}`: Customer profile and account summary.
* `GET /api/core/customers/{customer_id}/accounts`: Query current balances across all sub-accounts.
* `GET /api/core/customers/{customer_id}/transactions`: Query transaction history.
* `POST /api/core/extract-account-info`: AI Chatbot extraction interface.

## Consequences
* **Positive**: Clear separation of concerns; AI Assistant communicates with Core Banking via API client contracts; full Web Management Portal for core account operations.
* **Negative**: Additional database maintenance and schema migration management.
