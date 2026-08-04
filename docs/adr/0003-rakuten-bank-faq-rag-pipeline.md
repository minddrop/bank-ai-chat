# ADR 0003: Rakuten Bank FAQ Ingestion & RAG Pipeline

* **Status**: Accepted
* **Date**: 2026-08-04
* **Deciders**: AI Bank Engineering Team, RAG Specialist

## Context & Problem Statement
To accurately answer general banking inquiries (such as transfer fees, account opening procedures, password resets, and debit card terms) without hallucinations, the AI assistant needs a authoritative Japanese banking knowledge base.

## Decision Drivers
* Real-world reference source: Public Rakuten Bank FAQ portal (`https://help-personal.rakuten-bank.net/`).
* High precision and low latency for search retrieval.
* Need for structured JSON storage for offline RAG indexing.

## Decision Outcome
Chosen Solution: **Automated Scraper & In-Memory Vector Store RAG Pipeline**.

### Implementation Details:
* **Extraction Utility**: `scripts/extract_rakuten_faq.py` parses the Rakuten Bank FAQ site into structured JSON (`data/rakuten_faq.json`).
* **Vector Store**: `src/rag/vector_store.py` builds an embedded vector index combining TF-IDF and cosine similarity for semantic Japanese search.
* **Grounding Engine**: Output Guardrail verifies that LLM answers cite or match retrieved FAQ context snippets.

## Consequences
* **Positive**: 100% grounded answers on Japanese retail banking procedures with zero reliance on hallucinated policies.
* **Negative**: Requires routine re-scraping to stay synced with live bank FAQ updates.
