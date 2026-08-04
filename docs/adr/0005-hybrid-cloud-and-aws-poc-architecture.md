# ADR 0005: Hybrid Cloud & AWS Standalone POC Architecture

* **Status**: Accepted
* **Date**: 2026-08-04
* **Deciders**: Enterprise Architecture Team, Lead Cloud Architect

## Context & Problem Statement
Japanese mega-banks operate core banking (勘定系) systems on-premise in private data centers. Production target deployment will be a hybrid topology (On-Prem core banking + AWS Private Cloud). However, for the POC phase, rapid prototyping and validation require a self-contained, fully deployable architecture in AWS.

## Decision Drivers
* Target production design: Hybrid topology connected via AWS Direct Connect with hardware Security Modules (HSM).
* POC requirement: Standalone AWS implementation mimicking core banking APIs via microservices while exercising full Bedrock and Control Plane components.

## Decision Outcome
Chosen Solution: **Design Hybrid Architecture for Production, Implement Standalone Containerized AWS Architecture for POC**.

### Architectural Layers:
1. **Production Blueprint**: On-prem core banking mainframes linked to AWS Private VPC via AWS Direct Connect.
2. **POC Implementation**: Standalone FastAPI + Web Frontend application hosted on AWS ECS Fargate pattern with local Bedrock Nova Lite invocation and synthetic database.

## Consequences
* **Positive**: Fast POC deployment without requiring on-prem hardware provisioning while providing a clear migration blueprint for production.
* **Negative**: API integration interfaces between on-prem and AWS must be mocked during the POC phase.
