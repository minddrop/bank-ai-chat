# Security Module - Security Groups, KMS CMK, and IAM Roles (REQ-OPS-017 & ADR-0017)

# 1. Security Groups Matrix (Strict Least-Privilege Isolation)

resource "aws_security_group" "alb" {
  name        = "sg_bank_ai_alb"
  description = "Tier 1: Ingress HTTPS from clients to ALB"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow HTTPS from trusted clients"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "sg_bank_ai_alb"
    Environment = var.environment
  }
}

resource "aws_security_group" "ecs" {
  name        = "sg_bank_ai_ecs"
  description = "Tier 2: Ingress from ALB on container port 8000 only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow reverse proxy traffic from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  tags = {
    Name        = "sg_bank_ai_ecs"
    Environment = var.environment
  }
}

# Add Egress rules linking ALB to ECS
resource "aws_security_group_rule" "alb_egress_to_ecs" {
  type                     = "egress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = aws_security_group.alb.id
  source_security_group_id = aws_security_group.ecs.id
}

resource "aws_security_group" "opensearch" {
  name        = "sg_bank_ai_opensearch"
  description = "Tier 3: Ingress from ECS to OpenSearch Serverless"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow OpenSearch HTTPS query from ECS tasks"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = {
    Name        = "sg_bank_ai_opensearch"
    Environment = var.environment
  }
}

resource "aws_security_group" "vpce" {
  name        = "sg_bank_ai_vpce"
  description = "Tier 3: Ingress from ECS to Bedrock and KMS Interface VPC Endpoints"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow AWS Interface Endpoints HTTPS from ECS"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = {
    Name        = "sg_bank_ai_vpce"
    Environment = var.environment
  }
}

# ECS Egress to OpenSearch and VPC Endpoints
resource "aws_security_group_rule" "ecs_egress_to_opensearch" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs.id
  source_security_group_id = aws_security_group.opensearch.id
}

resource "aws_security_group_rule" "ecs_egress_to_vpce" {
  type                     = "egress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.ecs.id
  source_security_group_id = aws_security_group.vpce.id
}

# 2. AWS KMS Customer Managed Key (CMK) AES-256 (FISC Compliance)
resource "aws_kms_key" "bank_vault" {
  description             = "FISC & APPI compliant KMS CMK for In-VPC Token Vault and S3 Audit Log"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "bank-ai-kms-cmk-${var.environment}"
    Environment = var.environment
    Compliance  = "FISC-AES256"
  }
}

resource "aws_kms_alias" "bank_vault" {
  name          = "alias/bank-ai-vault-${var.environment}"
  target_key_id = aws_kms_key.bank_vault.key_id
}

# 3. IAM Roles: Least-Privilege Execution and Task Roles (ADR-0017)

data "aws_iam_policy_document" "ecs_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# ECS Task Execution Role (ECR & CloudWatch)
resource "aws_iam_role" "ecs_execution_role" {
  name               = "BankAiEcsExecutionRole-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_standard" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (Bedrock, KMS, OpenSearch Least Privilege)
resource "aws_iam_role" "ecs_task_role" {
  name               = "BankAiEcsTaskRole-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume_role.json

  tags = {
    Environment = var.environment
  }
}

data "aws_iam_policy_document" "ecs_task_permissions" {
  statement {
    sid    = "BedrockNovaInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = [
      "arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.nova-lite-v1:0",
      "arn:aws:bedrock:ap-northeast-1::foundation-model/amazon.titan-embed-text-v2:0"
    ]
  }

  statement {
    sid    = "KmsSaltAndAuditOps"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey"
    ]
    resources = [aws_kms_key.bank_vault.arn]
  }

  statement {
    sid    = "OpenSearchServerlessAccess"
    effect = "Allow"
    actions = [
      "aoss:APIAccessAll"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ecs_task_policy" {
  name        = "BankAiEcsTaskPolicy-${var.environment}"
  description = "Least privilege permissions for Bank AI ECS Task"
  policy      = data.aws_iam_policy_document.ecs_task_permissions.json
}

resource "aws_iam_role_policy_attachment" "ecs_task_attach" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}
