# AWS Detailed Architecture Design Specification
## Japanese Major Bank Production AI Assistant System

**System Name**: Japanese Major Bank Production AI Assistant System  
**AWS Target Region**: Tokyo (`ap-northeast-1`)  
**Secondary DR Region**: Osaka (`ap-northeast-2`)  
**Compliance Standards**: FISC Security Standards (FISC安全対策基準), APPI (個人情報保護法), FSA Guidelines (金融庁AIガイドライン), Banking Act (銀行法), FIEA (金融商品取引法), PCI-DSS 4.0, GLBA Safeguards Rule (16 CFR Part 314), CFPB AI Guidance, SR 11-7, ISO 42001/AIUC-1, NYDFS Part 500  

---

## 1. Network Topology & VPC Architecture

### 1.1 VPC IPv4 Address Plan
- **Primary VPC (Tokyo `ap-northeast-1`)**: CIDR Block `10.100.0.0/16`
- **Availability Zones**: Multi-AZ deployment across `ap-northeast-1a`, `ap-northeast-1c`, `ap-northeast-1d`

| Subnet Tier | Zone | CIDR Block | Route Target | Purpose |
|---|---|---|---|---|
| Public Subnet 1A | `ap-northeast-1a` | `10.100.1.0/24` | Internet Gateway (IGW) | Application Load Balancer (ALB), NAT Gateway 1A |
| Public Subnet 1C | `ap-northeast-1c` | `10.100.2.0/24` | Internet Gateway (IGW) | Application Load Balancer (ALB), NAT Gateway 1C |
| Public Subnet 1D | `ap-northeast-1d` | `10.100.3.0/24` | Internet Gateway (IGW) | Application Load Balancer (ALB), NAT Gateway 1D |
| Private App Subnet 1A | `ap-northeast-1a` | `10.100.10.0/23` | NAT Gateway 1A / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Control Planes) |
| Private App Subnet 1C | `ap-northeast-1c` | `10.100.12.0/23` | NAT Gateway 1C / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Control Planes) |
| Private App Subnet 1D | `ap-northeast-1d` | `10.100.14.0/23` | NAT Gateway 1D / Transit Gateway | ECS Fargate Tasks (FastAPI Backend, Control Planes) |
| Isolated Data Subnet 1A | `ap-northeast-1a` | `10.100.20.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, KMS Endpoint, Secrets Manager |
| Isolated Data Subnet 1C | `ap-northeast-1c` | `10.100.21.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, Bedrock Endpoint, S3 Endpoint |
| Isolated Data Subnet 1D | `ap-northeast-1d` | `10.100.22.0/24` | Local VPC Only / VPC Endpoints | OpenSearch Serverless, CloudWatch Logs Endpoint |

### 1.2 Route Tables & NAT Gateway Allocation
- **Public Route Table (`rtb-public`)**: Associated with Public Subnets (1A, 1C, 1D). Route `0.0.0.0/0` -> Internet Gateway (`igw-xxxx`).
- **Private App Route Tables (`rtb-private-1a`, `rtb-private-1c`, `rtb-private-1d`)**: Associated with Private App Subnets. Route `0.0.0.0/0` -> Corresponding NAT Gateway in matching AZ (`nat-1a`, `nat-1c`, `nat-1d`).
- **Isolated Data Route Table (`rtb-isolated`)**: Associated with Isolated Data Subnets. **Zero outbound default route (`0.0.0.0/0`)**. Traffic routes strictly inside VPC or to Interface VPC Endpoints (`vpce-xxxx`).

### 1.3 VPC Flow Logs Configuration
- **Destination**: S3 Log Archive Bucket `japan-bank-ai-vpc-flowlogs-ap-northeast-1`.
- **Traffic Type**: `ALL` (Accept and Reject).
- **Log Format**: `${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status}`.
- **Encryption**: KMS CMK `alias/bank-ai-cmk`.

### 1.4 Application Load Balancer (ALB) & Security Groups
- **Listeners**:
  - Port 80 (HTTP): Redirects `HTTP 301` to Port 443 (HTTPS).
  - Port 443 (HTTPS): Uses SSL Policy `ELBSecurityPolicy-TLS13-1-2-2021-06` with ACM Certificate `arn:aws:acm:ap-northeast-1:123456789012:certificate/xxxx`.
  - Idle Timeout: `300 seconds` (to support long-lived SSE connections).
- **Health Check Configuration**:
  - Path: `/health`
  - Interval: `15 seconds`
  - Timeout: `5 seconds`
  - Healthy Threshold: `2`
  - Unhealthy Threshold: `3`
  - Success Code: `200`

### 1.5 Security Group Ingress / Egress Rules Matrix

| Security Group ID | Source / Target | Protocol / Port | Purpose / Note |
|---|---|---|---|
| `sg-alb` (Public ALB) | `0.0.0.0/0` | TCP 443 (HTTPS) | Inbound HTTPS traffic from Internet / Portal |
| `sg-alb` (Public ALB) | `0.0.0.0/0` | TCP 80 (HTTP) | Inbound HTTP traffic (Redirected to 443) |
| `sg-alb` (Public ALB) | `sg-ecs-tasks` | TCP 8000 | Egress to ECS Fargate tasks |
| `sg-ecs-tasks` (ECS App) | `sg-alb` | TCP 8000 | Inbound HTTP from ALB |
| `sg-ecs-tasks` (ECS App) | `sg-vpc-endpoints` | TCP 443 (HTTPS) | Egress to AWS PrivateLink Endpoints |
| `sg-ecs-tasks` (ECS App) | `sg-opensearch` | TCP 443 (HTTPS) | Egress to OpenSearch Serverless Collection |
| `sg-vpc-endpoints` | `sg-ecs-tasks` | TCP 443 (HTTPS) | Inbound HTTPS from ECS Tasks to VPC Endpoints |
| `sg-opensearch` | `sg-ecs-tasks` | TCP 443 (HTTPS) | Inbound HTTPS from ECS Tasks to AOSS Engine |

---

## 2. ECS Fargate Compute & Task Specifications

### 2.1 Task Definition JSON Schema

```json
{
  "family": "bank-ai-assistant-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "runtimePlatform": {
    "cpuArchitecture": "ARM64",
    "operatingSystemFamily": "LINUX"
  },
  "executionRoleArn": "arn:aws:iam::123456789012:role/BankAiEcsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789012:role/BankAiEcsTaskRole",
  "containerDefinitions": [
    {
      "name": "bank-ai-backend",
      "image": "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/bank-ai-chat:latest",
      "essential": true,
      "user": "10001:10001",
      "readonlyRootFilesystem": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        { "name": "AWS_REGION", "value": "ap-northeast-1" },
        { "name": "BEDROCK_MODEL_ID", "value": "amazon.nova-lite-v1:0" },
        { "name": "EMBEDDING_MODEL_ID", "value": "amazon.titan-embed-text-v2:0" },
        { "name": "AOSS_ENDPOINT", "value": "https://xxxx.ap-northeast-1.aoss.amazonaws.com" },
        { "name": "KMS_KEY_ALIAS", "value": "alias/bank-ai-cmk" },
        { "name": "AUDIT_S3_BUCKET", "value": "japan-bank-ai-audit-log-ap-northeast-1" },
        { "name": "LOG_LEVEL", "value": "INFO" },
        { "name": "GUARDRAIL_STRICT_MODE", "value": "true" }
      ],
      "secrets": [
        {
          "name": "VAULT_HMAC_SALT",
          "valueFrom": "arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:bank-ai/vault-hmac-salt:salt::"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 15,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 30
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/bank-ai-assistant",
          "awslogs-region": "ap-northeast-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

---

## 3. Storage, Database & OpenSearch Serverless Policies

### 3.1 Amazon OpenSearch Serverless (AOSS) Policies

#### Encryption Policy (`aoss-security-policy-encryption`)
```json
{
  "Rules": [
    {
      "ResourceType": "collection",
      "Resource": ["collection/bank-ai-faq-vectors"]
    }
  ],
  "AWSOwnedKey": false,
  "KmsARN": "arn:aws:kms:ap-northeast-1:123456789012:key/bank-ai-cmk"
}
```

#### Network Policy (`aoss-security-policy-network`)
```json
[
  {
    "Rules": [
      {
        "ResourceType": "collection",
        "Resource": ["collection/bank-ai-faq-vectors"]
      },
      {
        "ResourceType": "dashboard",
        "Resource": ["collection/bank-ai-faq-vectors"]
      }
    ],
    "AllowFromVPCEndpoints": ["vpce-0123456789abcdef0"],
    "AllowPublicAccess": false
  }
]
```

#### Data Access Policy (`aoss-access-policy`)
```json
[
  {
    "Rules": [
      {
        "ResourceType": "index",
        "Resource": ["index/bank-ai-faq-vectors/*"],
        "Permission": [
          "aoss:CreateIndex",
          "aoss:UpdateIndex",
          "aoss:DescribeIndex",
          "aoss:ReadDocument",
          "aoss:WriteDocument"
        ]
      }
    ],
    "Principal": [
      "arn:aws:iam::123456789012:role/BankAiEcsTaskRole"
    ]
  }
]
```

### 3.2 S3 Audit Bucket Policy Enforcing Encryption & TLS 1.3
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EnforceTLS13Only",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::japan-bank-ai-audit-log-ap-northeast-1",
        "arn:aws:s3:::japan-bank-ai-audit-log-ap-northeast-1/*"
      ],
      "Condition": {
        "NumericLessThan": {
          "s3:TlsVersion": "1.3"
        }
      }
    },
    {
      "Sid": "EnforceKMSCMKEncryption",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::japan-bank-ai-audit-log-ap-northeast-1/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

---

## 4. Complete IAM Roles & KMS Policies

### 4.1 ECS Task Runtime Role (`BankAiEcsTaskRole`) Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockNovaLiteInvoke",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.nova-lite-v1:0"
    },
    {
      "Sid": "TitanEmbeddingsInvoke",
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.titan-embed-text-v2:0"
    },
    {
      "Sid": "AossDataAccess",
      "Effect": "Allow",
      "Action": "aoss:APIAccessAll",
      "Resource": "arn:aws:aoss:ap-northeast-1:123456789012:collection/*"
    },
    {
      "Sid": "S3AuditLogPut",
      "Effect": "Allow",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::japan-bank-ai-audit-log-ap-northeast-1/*"
    },
    {
      "Sid": "KmsCryptographicOperations",
      "Effect": "Allow",
      "Action": [
        "kms:GenerateDataKey",
        "kms:Decrypt",
        "kms:Encrypt"
      ],
      "Resource": "arn:aws:kms:ap-northeast-1:123456789012:key/bank-ai-cmk"
    }
  ]
}
```

### 4.2 GitHub Actions OIDC Deploy Role Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuthAndPush",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EcsTaskDefinitionUpdate",
      "Effect": "Allow",
      "Action": [
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassRoleToEcs",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::123456789012:role/BankAiEcsTaskExecutionRole",
        "arn:aws:iam::123456789012:role/BankAiEcsTaskRole"
      ]
    }
  ]
}
```

---

## 5. Observability & Alarm Targets

| Alarm Name | Metric Name | Namespace | Statistic | Threshold | Evaluation | Priority | Notification |
|---|---|---|---|---|---|---|---|
| `BankAi-P95LatencyHigh` | `TargetResponseTime` | `AWS/ApplicationELB` | P95 | `> 0.800 s` | 2 periods (5 mins) | P2 High | SNS -> DevOps Pager |
| `BankAi-5xxErrorSpike` | `HTTPCode_Target_5XX_Count` | `AWS/ApplicationELB` | Sum | `> 5 reqs` | 1 period (1 min) | P1 Critical | SNS -> SRE Page |
| `BankAi-GuardrailBlockSurge` | `GuardrailBlockCount` | `BankAi/ControlPlane` | Sum | `> 10 blocks` | 1 period (5 mins) | P2 Security | SNS -> SOC Alert |
| `BankAi-GroundingViolation` | `GroundingViolationCount` | `BankAi/ControlPlane` | Sum | `> 5 count` | 1 period (5 mins) | P2 High | SNS -> Model Governance |
| `BankAi-AuditS3WriteError` | `S3AuditWriteError` | `BankAi/Audit` | Sum | `> 0 errors` | 1 period (1 min) | P0 Blocker | SNS -> Immediate Page |
