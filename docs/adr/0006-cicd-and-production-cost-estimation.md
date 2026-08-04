# ADR 0006: Enterprise CI/CD Pipeline & Production AWS Cost Architecture

* **Status**: Accepted
* **Date**: 2026-08-04
* **Deciders**: Enterprise Architect, Lead DevOps Engineer, Finance Lead

## Context & Problem Statement
Deploying an AI Customer Assistant for a major Japanese financial institution requires automated, zero-downtime deployment pipelines with strict security scanning, SAST/DAST testing, control plane guardrail verification, and a predictable, cost-optimized production infrastructure footprint in AWS Tokyo (`ap-northeast-1`).

## Decision Drivers
* Zero-downtime deployment with automatic canary rollback capabilities.
* Mandatory automated security gates for APPI PII redaction and FISC compliance before code reaches production.
* Predictable cost model for 1,000,000 monthly customer interactions in AWS Tokyo.

## Decision Outcome
Chosen Option: **AWS ECR + ECS Fargate Blue/Green Canary Deployment paired with Bedrock Nova Lite Token Pricing Optimization**.

### Implementation Strategy:
1. **CI/CD Pipeline**: GitHub Actions / AWS CodePipeline executing unit tests, control plane injection tests, Trivy vulnerability scanning, and ECS Fargate Blue/Green Canary rollouts.
2. **Cost Strategy**: Amazon Bedrock Nova Lite (`amazon.nova-lite-v1:0`) in Tokyo (`ap-northeast-1`) providing ~¥80,000 JPY/month total AWS operational cost for 1,000,000 customer sessions.

## Consequences
* **Positive**: 100% automated regulatory compliance testing; 85%+ LLM cost savings compared to traditional models; zero downtime for bank customers.
* **Negative**: Requires maintaining automated canary health alarms during deployments.
