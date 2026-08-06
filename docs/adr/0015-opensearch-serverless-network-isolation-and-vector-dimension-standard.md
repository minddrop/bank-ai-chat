# ADR 0015: OpenSearch Serverless Network Isolation & Vector Dimension Standard

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Infrastructure Architect, Lead Security Engineer, AI Search Engineer

---

## Context & Problem Statement

The system utilizes Amazon OpenSearch Serverless (AOSS) as a vector database for retrieving Rakuten Bank FAQ knowledge base passages. During the infrastructure audit, two operational ambiguities were identified:
1. **Vector Embedding Dimension Discrepancy**: Legacy draft specifications contained inconsistent vector dimension definitions (1536-dim vs 1024-dim), creating potential indexing mismatches when embedding model outputs are queried against the vector index.
2. **Network Perimeter & FISC Isolation**: OpenSearch Serverless collections must strictly prevent public Internet ingress to comply with FISC Security Standards (FISC安全対策基準) and APPI data sovereignty rules.

We must establish a single, deterministic standard for OpenSearch Serverless vector dimension configuration, indexing algorithms, and PrivateLink network access isolation.

---

## Decision Drivers

1. **Deterministic Index Provisioning**: Infrastructure engineers and automated Terraform scripts require explicit HNSW algorithm parameters, distance metrics, and vector dimensions.
2. **FISC & APPI Security Compliance**: Complete exclusion of public endpoints for vector collections; all data access must route strictly over Private Interface VPC Endpoints (`com.amazonaws.ap-northeast-1.aoss`).
3. **Rakuten FAQ Dataset Compatibility**: Alignment with the Amazon Titan Text Embeddings v2 (`amazon.titan-embed-text-v2:0`) 1024-dimension specification used for semantic search across Japanese banking FAQ items.

---

## Considered Options

1. **1024-Dimension Titan Text Embeddings v2 with Private VPC Endpoint Network Isolation (Chosen Option)**:
   - Standardize all vector embeddings and OpenSearch index mappings on **1024 dimensions** using HNSW (Hierarchical Navigable Small World) cosine similarity.
   - Restrict AOSS network policy exclusively to VPC access through PrivateLink endpoints within Isolated Data Subnets (`10.100.20.0/24`, `10.100.21.0/24`, `10.100.22.0/24`).
2. **1536-Dimension Vector Standard with Public Endpoint Filtering**:
   - Use legacy 1536-dim embeddings and restrict access via IP whitelist on public endpoints.
   - *Drawback*: IP whitelisting on public endpoints violates FISC data isolation mandates and increases exposure risk.

---

## Decision Outcome

Chosen Option: **Option 1 (1024-Dimension Titan Text Embeddings v2 with Private VPC Endpoint Network Isolation)**.

### Technical & IaC Specifications:

- **Model & Vector Dimension**: Amazon Titan Text Embeddings v2 (`amazon.titan-embed-text-v2:0`) emitting **1024-dimensional** float vectors.
- **Index Engine**: OpenSearch Serverless `VECTORSEARCH` collection with `hnsw` algorithm (`ef_construction = 512`, `m = 16`, `space_type = cosine`).
- **Network Security Policy**:
  - `AllowFromVPCEndpoints`: Restricted strictly to AOSS VPC Endpoint (`vpce-xxxxxxxxxxxxxxxxx`).
  - `NoPublicAccess`: Enforced `type = "network"` block with `AllowPublicAccess = false`.
- **Data Encryption Policy**: AWS KMS Customer Managed Key (CMK) encryption at rest (`aws:kms`).

---

## Consequences

### Positive:
- **Zero Internet Exposure**: Vector data and metadata cannot be queried or accessed outside the Bank VPC.
- **Deterministic Provisioning**: Eliminates dimensional mismatch errors during vector ingestion or similarity scoring.
- **Strict Compliance**: Satisfies FISC, APPI, and FSA data isolation standards.

### Negative / Risks:
- **Index Re-indexing Required**: Any legacy 1536-dimension index vectors must be re-embedded using Titan v2 prior to ingestion.
