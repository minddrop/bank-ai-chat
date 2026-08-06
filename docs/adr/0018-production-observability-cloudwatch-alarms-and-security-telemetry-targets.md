# ADR 0018: Production Observability, CloudWatch Alarms & Security Telemetry Targets

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal DevOps Architect, Security Operations Lead, SRE Lead

---

## Context & Problem Statement

Maintaining 99.99% uptime, <800ms P95 end-to-end response latency, and strict security compliance requires comprehensive observability across the entire AWS deployment stack. Initial draft requirements listed high-level performance targets but lacked deterministic metrics, evaluation windows, threshold numbers, CloudWatch alarm rules, and automated security alert notification routing.

We must formally establish the production observability metrics, CloudWatch alarm definitions, telemetry targets, and incident response alerting routes.

---

## Decision Drivers

1. **Production Availability & Latency SLAs**: Real-time tracking of P50, P95, P99 request latencies, HTTP 5xx error rates, and ECS task CPU/Memory saturation.
2. **Security & Guardrail Event Detection**: Immediate notification of high prompt injection volumes, outbound PII reflection attempts, or low NLI grounding scores (<0.70).
3. **FISC Compliance & Audit Trail Integrity**: Zero-tolerance monitoring for S3 Audit log write failures or KMS key access anomalies.

---

## Considered Options

1. **Structured CloudWatch Logs & Metrics with SNS Telemetry Fanout (Chosen Option)**:
   - Export custom metrics (`GuardrailBlockCount`, `GroundingViolationCount`, `PiiScrubbedCount`, `AuditWriteFailureCount`) from the ECS FastAPI backend directly into CloudWatch Embedded Metric Format (EMF).
   - Configure deterministic CloudWatch Alarms bound to SNS Topics (`BankAiHighPriorityAlerts`, `BankAiSecurityHubAlerts`) for PagerDuty and SOC escalation.
2. **Third-Party SaaS Monitoring (Datadog / New Relic)**:
   - Stream all logs and APM telemetry out of VPC to a third-party SaaS provider.
   - *Drawback*: Requires complex data scrubbing guarantees to prevent telemetry PII leaks and violates strict FISC data sovereignty guidelines without dedicated in-region SaaS endpoints.

---

## Decision Outcome

Chosen Option: **Option 1 (Structured CloudWatch Logs & Metrics with SNS Telemetry Fanout)**.

### Observability Metrics & Alarm Target Specification Table:

| Metric Name | Namespace | Statistic | Evaluation Window | Alarm Threshold | Alert Priority & Action |
|---|---|---|---|---|---|
| `TargetResponseTime` | `AWS/ApplicationELB` | P95 | 5 minutes (2 periods) | `> 800 ms` | **P2 High**: Trigger ECS Auto-scaling & notify DevOps team. |
| `HTTPCode_Target_5XX_Count` | `AWS/ApplicationELB` | Sum | 1 minute (1 period) | `> 5 requests` | **P1 Critical**: Page SRE team & trigger rollback if in deployment. |
| `CPUUtilization` | `AWS/ECS` | Average | 5 minutes (2 periods) | `> 80%` | **P2 High**: Scale out ECS tasks (up to 30 max). |
| `MemoryUtilization` | `AWS/ECS` | Average | 5 minutes (2 periods) | `> 85%` | **P2 High**: Scale out ECS tasks & inspect for memory leaks. |
| `GuardrailBlockCount` | `BankAi/ControlPlane` | Sum | 5 minutes (1 period) | `> 10 blocks` | **P2 High Security**: Notify SOC of potential attack pattern. |
| `GroundingViolationCount` | `BankAi/ControlPlane` | Sum | 5 minutes (1 period) | `> 5 violations` | **P2 High**: Alert AI Model Governance team for RAG drift. |
| `Bedrock429ThrottlingCount`| `BankAi/LLM` | Sum | 1 minute (1 period) | `> 2 errors` | **P2 High**: Increase Bedrock provisioned throughput quota. |
| `S3AuditWriteError` | `BankAi/Audit` | Sum | 1 minute (1 period) | `> 0 errors` | **P0 Blocker**: Immediate page; system circuit breaker fails closed. |

---

## Consequences

### Positive:
- **Zero Blind Spots**: Immediate visibility into latency degradation, guardrail attacks, and model failures.
- **Fail-Closed Safety**: S3 audit write errors immediately trip system alerts to prevent un-audited customer transactions.
- **In-VPC Sovereignty**: All telemetry data remains 100% within AWS Tokyo (`ap-northeast-1`).

### Negative / Risks:
- **Alert Fatigue Prevention Required**: Alarm thresholds must be calibrated during initial load testing to prevent false positives.
