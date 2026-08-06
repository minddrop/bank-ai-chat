# ADR 0017: Enterprise IAM Least-Privilege Access & KMS Key Policy Topology

* **Status**: Accepted
* **Date**: 2026-08-07
* **Deciders**: Principal Security Architect, IAM Platform Lead, Compliance Officer

---

## Context & Problem Statement

In an enterprise banking application deployed under FISC Security Standards (FISC安全対策基準) and APPI rules, access control must enforce the Principle of Least Privilege. Ambiguity in IAM role boundaries or KMS Customer Managed Key (CMK) key policies risks overly permissive access (e.g. wildcards `*` on S3, KMS, or Bedrock resources), which violates banking audit guidelines.

We must formally document the IAM role separation architecture, OpenID Connect (OIDC) identity federation for deployment pipelines, and KMS CMK key policy topologies.

---

## Decision Drivers

1. **FISC & Banking Act IAM Controls**: Elimination of blanket `*:*` wildcard actions on all IAM policies; mandatory scoping of actions to explicit resource ARNs.
2. **Key Rotation & Access Boundary**: KMS CMK key policies must allow specific service principals (ECS, S3, CloudWatch, AOSS) while strictly preventing root/admin decryption of sensitive audit buckets without log generation.
3. **Zero Static Long-Lived Credentials**: CI/CD automation must not store static AWS access keys; GitHub Actions deployment must utilize short-lived OIDC tokens.

---

## Considered Options

1. **Role-Separated IAM Policy Topology with OIDC & KMS CMK Key Policy Scoping (Chosen Option)**:
   - Separate ECS Execution Role (`BankAiEcsTaskExecutionRole`) from ECS Task Runtime Role (`BankAiEcsTaskRole`).
   - Use GitHub Actions OIDC role federation with repository/branch condition locks.
   - Enforce explicit KMS CMK key policy scoping for `kms:GenerateDataKey`, `kms:Decrypt`, and `kms:Encrypt`.
2. **Shared Application Role with Static IAM User Keys**:
   - Combine task execution and application runtime into a single role, using static IAM credentials in CI/CD secrets.
   - *Drawback*: Major compliance failure under FISC Sec 3.2, PCI-DSS Req 8, and APPI Article 20.

---

## Decision Outcome

Chosen Option: **Option 1 (Role-Separated IAM Policy Topology with OIDC & KMS CMK Key Policy Scoping)**.

### IAM & KMS Architecture Specifications:

1. **ECS Task Execution Role (`BankAiEcsTaskExecutionRole`)**:
   - Scoped strictly to container lifecycle management: pulling container images from AWS ECR (`ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `ecr:GetAuthorizationToken`), retrieving secrets from Secrets Manager (`secretsmanager:GetSecretValue`), and creating CloudWatch log streams (`logs:CreateLogStream`, `logs:PutLogEvents`).

2. **ECS Task Runtime Role (`BankAiEcsTaskRole`)**:
   - Scoped strictly to application runtime dependencies:
     - `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on resource `arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.nova-lite-v1:0`.
     - `aoss:APIAccessAll` on OpenSearch Serverless collection ARN.
     - `s3:PutObject` on Audit Log bucket `japan-bank-ai-audit-log-ap-northeast-1`.
     - `kms:GenerateDataKey` and `kms:Decrypt` on CMK ARN `alias/bank-ai-cmk`.

3. **GitHub Actions OIDC Federation (`GitHubActionsDeployRole`)**:
   - Federated trust via `token.actions.githubusercontent.com`.
   - Condition statement locked to: `repo:minddrop/bank-ai-chat:ref:refs/heads/main`.
   - Permissions limited to ECR image pushing and ECS task definition updating in `ap-northeast-1`.

4. **AWS KMS CMK Key Policy Topology**:
   - Key Rotation: `enable_key_rotation = true` (Automatic annual rotation).
   - Strict Principal Delegation: Explicit policy statements granting decryption access only to CloudWatch Logs, S3 Audit Bucket, AOSS Vector Store, and ECS Task Roles.

---

## Consequences

### Positive:
- **Zero Static Credentials**: Eliminates credential leak risks in developer workstations or CI/CD pipelines.
- **Audit Ready**: Meets 100% of FISC, APPI, PCI-DSS, and FSA IAM auditing criteria.
- **Blast Radius Containment**: A compromised ECS container cannot modify IAM policies, delete S3 buckets, or decrypt unauthorized KMS keys.

### Negative / Risks:
- **IAM Policy Verbosity**: Requires maintaining distinct, highly granular JSON policies in IaC.
