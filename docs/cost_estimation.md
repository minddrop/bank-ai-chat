# AWS Production Cost Estimation & ROI Analysis
## Japanese Major Bank AI Customer Assistant System

---

## 1. Overview & Sizing Assumptions

This document provides a detailed cost estimation for operating the **Japanese Major Bank AI Customer Assistant System** in production on AWS Tokyo (`ap-northeast-1`).

*(See [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md), [ADR-0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md), and [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) for rationale and cost trade-off decisions)*

### Base Production Scale Sizing:
- **Monthly Customer Interactions**: 1,000,000 requests / month (~33,333 requests / day).
- **Peak Throughput**: 1,000 Transactions Per Second (TPS).
- **Average Prompt Payload**: 500 input tokens (including system prompt & RAG context).
- **Average Output Payload**: 300 output tokens (including polite Keigo answer & disclaimers).
- **Availability Target**: 99.99% Multi-AZ availability.
- **Data Sovereignty**: 100% in-region processing in AWS Tokyo (`ap-northeast-1`).

---

## 2. AWS Tokyo Monthly Cost Itemization (`ap-northeast-1`)

| Service Component | Specification & Capacity | Unit Pricing (USD) | Monthly Cost (USD) | Monthly Cost (JPY @ ¥150/$) | Governing ADR |
|---|---|---|---|---|---|
| **Amazon Bedrock** (Amazon Nova Lite) | 1,000,000 requests/mo (500M input tokens, 300M output tokens) | $0.00006/1K in, $0.00024/1K out | $102.00 | ¥15,300 | [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md) |
| **AWS ECS Fargate** (Backend & Control Planes) | 4 Tasks x (2 vCPU, 4GB RAM) Multi-AZ Auto-scaling | $0.04048/vCPU-hr, $0.004445/GB-hr | $184.00 | ¥27,600 | [ADR-0011](file:///home/joe/src/bank-ai-chat/docs/adr/0011-compute-architecture-re-evaluation-ecs-vs-lambda.md) |
| **Amazon OpenSearch Serverless** (FAQ RAG) | 2 OCU Multi-AZ Vector Index | $0.24/OCU-hr | $140.00 | ¥21,000 | [ADR-0015](file:///home/joe/src/bank-ai-chat/docs/adr/0015-opensearch-serverless-network-isolation-and-vector-dimension-standard.md) |
| **Amazon S3** (Encrypted Audit Logs) | 100 GB Standard Storage + KMS encryption + Put/Get requests | $0.025/GB | $12.50 | ¥1,875 | [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md) |
| **AWS KMS** (Customer Managed Keys) | 2 CMK Keys (Audit Log & Vector DB Encryption) | $1.00/key/month | $2.00 | ¥300 | [ADR-0017](file:///home/joe/src/bank-ai-chat/docs/adr/0017-enterprise-iam-least-privilege-access-and-kms-key-policy-topology.md) |
| **AWS Application Load Balancer** | Dual-AZ ALB + LCU processing | $0.0243/hr + LCU charges | $28.50 | ¥4,275 | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **AWS WAF & Shield Standard** | 1 Web ACL + 5 Managed Rulesets (OWASP Top 10, IP Rep) | $5.00/ACL + $1.00/rule | $35.00 | ¥5,250 | [ADR-0007](file:///home/joe/src/bank-ai-chat/docs/adr/0007-production-aws-detailed-design-specification.md) |
| **Amazon CloudWatch & X-Ray** | 30 GB Log Ingestion, Alarm metrics, X-Ray tracing | $0.675/GB | $25.00 | ¥3,750 | [ADR-0018](file:///home/joe/src/bank-ai-chat/docs/adr/0018-production-observability-cloudwatch-alarms-and-security-telemetry-targets.md) |
| **AWS Network Egress** | Data Transfer Out (100 GB/month) | $0.114/GB | $11.40 | ¥1,710 | [ADR-0005](file:///home/joe/src/bank-ai-chat/docs/adr/0005-hybrid-cloud-and-aws-poc-architecture.md) |
| **Total Estimated Monthly Cost** | | | **$540.40 / month** | **¥81,060 / 月** | [ADR-0006](file:///home/joe/src/bank-ai-chat/docs/adr/0006-cicd-and-production-cost-estimation.md) |

---

## 3. Annual Cost & ROI Summary

### Annual Financial Summary:
- **Total Estimated Monthly Operations Cost**: **$540.40 USD** (~**¥81,060 JPY**).
- **Total Estimated Annual Operations Cost**: **$6,484.80 USD / year** (~**¥972,720 JPY / 年**).

### Financial Benefits & Cost Advantage:
1. **85%+ LLM Cost Reduction**: Utilizing **Amazon Nova Lite** on Amazon Bedrock delivers fast, highly fluent Japanese banking responses at a fraction of legacy model endpoints. *(See [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md))*
2. **Call Center Deflection Savings**: Deflecting 1,000,000 tier-1 customer inquiries per month from human call centers (avg cost ¥300/call) yields an estimated **¥300,000,000 JPY annual operational savings** for the bank.
3. **FISC Compliance without Premium Overhead**: Full regulatory compliance (APPI PII scrubbing, KMS AES-256, S3 audit locking) achieved natively in AWS Tokyo with minimal operational overhead. *(See [ADR-0001](file:///home/joe/src/bank-ai-chat/docs/adr/0001-japanese-banking-compliance-and-control-planes.md), [ADR-0009](file:///home/joe/src/bank-ai-chat/docs/adr/0009-dlp-security-guardrails-and-compliance-framework.md))*

