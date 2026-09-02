# Production Environment Root Module (REQ-OPS-017 & ADR-0016)
# Region: AWS Tokyo (ap-northeast-1)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Deterministic Remote State Management (REQ-OPS-017 §2.1)
  backend "s3" {
    bucket         = "bank-ai-tfstate-apne1-prod"
    key            = "environments/prod/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "bank-ai-tflocks-prod"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "JapaneseMajorBank-AIChat"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Compliance  = "FISC-APPI-FSA"
    }
  }
}

# 1. 3-Tier VPC Module
module "vpc" {
  source      = "../../modules/vpc"
  environment = var.environment
}

# 2. Security Module (Security Groups, KMS CMK, IAM Roles)
module "security" {
  source      = "../../modules/security"
  vpc_id      = module.vpc.vpc_id
  environment = var.environment
  aws_region  = var.aws_region
}

# 3. Application Load Balancer Module
module "alb" {
  source            = "../../modules/alb"
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.security.alb_security_group_id
  environment       = var.environment
  certificate_arn   = var.certificate_arn
}

# 4. AWS WAF v2 Security Module
module "waf" {
  source      = "../../modules/waf"
  alb_arn     = module.alb.alb_arn
  environment = var.environment
}

# 5. OpenSearch Serverless Module (Vector Store)
module "opensearch" {
  source             = "../../modules/opensearch"
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.data_subnet_ids
  security_group_id  = module.security.opensearch_security_group_id
  kms_key_arn        = module.security.kms_cmk_arn
  ecs_task_role_arn  = module.security.ecs_task_role_arn
  environment        = var.environment
}

# 6. ECS Fargate Cluster & Service Module
module "ecs" {
  source             = "../../modules/ecs"
  environment        = var.environment
  app_subnet_ids     = module.vpc.app_subnet_ids
  security_group_id  = module.security.ecs_security_group_id
  target_group_arn   = module.alb.target_group_arn
  execution_role_arn = module.security.ecs_execution_role_arn
  task_role_arn      = module.security.ecs_task_role_arn
  container_image    = var.container_image
  desired_count      = 2
}
