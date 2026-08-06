# ADR 0011: Compute Architecture Re-evaluation – AWS ECS Fargate vs. AWS Lambda & Fully Managed Options

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Lead AWS Cloud Solutions Architect, Principal Cybersecurity Architect, Banking AI Operations Lead

---

## Context & Problem Statement

The Japanese Major Bank AI Customer Assistant handles real-time end-user banking inquiries, requiring strict adherence to Japanese financial regulations (APPI, FSA Guidelines, FISC Security Standards, Banking Act, FIEA). The synchronous AI chat pipeline involves complex In-VPC Dual Control Planes (Input DLP, PII tokenized vaulting, prompt injection classifiers, Output NLI entailment grounding verification, and FIEA investment advice restrictions) and streams responses via Server-Sent Events (SSE) from Amazon Bedrock Nova Lite (`amazon.nova-lite-v1:0`).

As part of continuous architecture governance, we re-evaluated whether **AWS Lambda** or fully managed serverless compute services (**AWS App Runner**, **Amazon Bedrock Agents**) would be superior to the baseline **AWS ECS Fargate** container architecture in terms of streaming capability, latency SLAs, proxy timeouts, security/compliance boundaries, and cost predictability.

---

## Decision Drivers

1. **Real-Time Streaming Reliability**: Un-truncated Server-Sent Events (SSE) streaming without proxy integration timeouts (e.g., API Gateway's 29-second hard limit).
2. **Latency & Cold-Start SLA**: Low P95 latency (< 800ms) for retail banking end-users, completely eliminating cold-start spikes inside private VPC subnets.
3. **Execution Time Flexibility**: Support for multi-turn RAG retrieval chains, agentic reasoning, and complex safety guardrail processing without 15-minute or 29-second execution caps.
4. **FISC & APPI Security Compliance**: Strict VPC subnet isolation (`10.100.0.0/16`), AWS PrivateLink VPC Endpoints, mTLS to core banking databases, fine-grained Security Groups, and KMS CMK AES-256 encryption.
5. **Operational Predictability & Cost**: Cost-effective, predictable operations under continuous 24/7 banking traffic patterns (~1,000,000 requests/month).

---

## Considered Options

1. **AWS ECS Fargate behind Application Load Balancer (ALB)** *(Chosen)*
   - Containerized FastAPI microservices running warm tasks across 3 Availability Zones (`ap-northeast-1a`, `1c`, `1d`).
2. **AWS Lambda + Amazon API Gateway (Serverless API Stack)**
   - Event-driven Lambda functions handling chat endpoints behind API Gateway REST/HTTP APIs.
3. **AWS App Runner (Fully Managed Container Service)**
   - Managed web application platform orchestrating container deployments.
4. **Amazon Bedrock Agents + API Gateway (Fully Managed Orchestration)**
   - Bedrock managed agentic orchestration bypassing custom FastAPI control plane logic.

---

## Trade-Off Comparison Matrix

| Evaluation Criteria | AWS ECS Fargate (Option 1) | AWS Lambda + API Gateway (Option 2) | AWS App Runner (Option 3) | Bedrock Agents (Option 4) |
|---|---|---|---|---|
| **Real-Time SSE Streaming** | **Excellent**: Native HTTP/1.1 & HTTP/2 SSE support via ALB with configurable idle timeouts (up to 4000s). No proxy limits. | **Poor / High Risk**: API Gateway enforces a **hard 29s integration timeout**. Lambda Function URLs bypass API Gateway WAF/controls. | **Moderate**: Supports SSE, but lacks granular VPC ingress/egress controls. | **Moderate**: Stream support limited to standard Bedrock agent event schemas. |
| **Latency & Cold Starts** | **Zero Cold Starts**: 4 warm Fargate tasks across 3 AZs; pre-initialized Python models & vector DB connections. P95 < 630ms. | **High Tail Latency**: VPC ENI attachment + Python runtime + PII/Guardrail model init causes **1s–3s cold starts**. | **Low-to-Moderate**: Automatic scaling introduces cold starts during rapid traffic spikes. | **Low-to-Moderate**: Managed invocation overhead. |
| **Execution Time Limits** | **Uncapped**: No execution timeout limits for long agentic chains or RAG retries. | **Strict Caps**: Hard 29s API Gateway timeout and 15-minute Lambda max execution cap. | **Configurable**: Up to 120s request timeout limit. | **Managed**: Bound by Bedrock API call limits. |
| **FISC & APPI Compliance** | **100% Compliant**: Isolated Private App Subnets (`10.100.0.0/16`), PrivateLink VPC endpoints, KMS CMK, full mTLS. | **Compliant with Overhead**: Requires VPC Lambda configuration + Provisioned Concurrency to maintain state. | **Non-Compliant**: Lacks fine-grained 3-tier VPC subnet placement and mTLS core banking controls. | **Partial**: Cannot run custom pre-ingestion PII tokenization vault in-VPC. |
| **Monthly Cost (1M reqs)** | **$180/mo (Predictable)**: Fixed 4-task warm pool with auto-scaling for peak traffic. | **$45–$210/mo**: Cheap at low volume, but Provisioned Concurrency pushes cost above ECS. | **$140–$250/mo**: Memory-based pricing per instance. | **Variable**: Token + agent step usage pricing. |

---

## Decision Outcome

Chosen Option: **Option 1 (AWS ECS Fargate for synchronous chat streaming) with AWS Lambda reserved for asynchronous background workflows**.

### Key Architectural Specifications:

1. **Synchronous Chat & Control Plane Path**:
   - Hosted on **AWS ECS Fargate** across 3 AZs (`ap-northeast-1a`, `1c`, `1d`) behind an Application Load Balancer (ALB).
   - Serves real-time Server-Sent Events (SSE) streaming directly from Amazon Bedrock Nova Lite to end-user browsers without proxy timeouts.
   - Eliminates cold starts, guaranteeing P95 response latency < 800ms including full Input/Output DLP Guardrails, OpenSearch RAG lookups, and audit logging.

2. **Asynchronous Background Processing Path (AWS Lambda)**:
   - **AWS Lambda** is adopted exclusively for asynchronous event-driven tasks:
     - S3 audit log rotation and SHA-256 integrity verification triggers.
     - Scheduled Rakuten FAQ OpenSearch vector database re-indexing pipelines.
     - Automated daily FISC compliance metric aggregation and CloudWatch alert processing.

---

## Consequences

* **Positive**:
  - Guaranteed zero cold-start latency for real-time customer chat interactions.
  - Complete evasion of API Gateway's 29-second integration timeout during complex RAG and agentic reasoning flows.
  - Uncompromised FISC/APPI compliance with full 3-tier VPC network isolation and PrivateLink endpoints.
  - Predictable cost structure under continuous retail banking workloads.
* **Negative**:
  - Requires maintaining ECS Fargate task definitions, ALB target groups, and container deployment pipelines (managed automatically via existing GitHub Actions CD pipeline).
