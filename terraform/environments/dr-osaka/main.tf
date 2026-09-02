# Secondary Disaster Recovery (DR) Environment Root Module (REQ-OPS-017 §1.3 & ADR-0022)
# Region: AWS Osaka (ap-northeast-3)
# Topology: Warm Standby / Pilot Light (1 Task) with Route 53 ARC DNS Failover

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "bank-ai-tfstate-apne3-dr"
    key            = "environments/dr-osaka/terraform.tfstate"
    region         = "ap-northeast-3"
    dynamodb_table = "bank-ai-tflocks-dr"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "JapaneseMajorBank-AIChat"
      Environment = var.environment
      Role        = "DisasterRecovery-Secondary"
      ManagedBy   = "Terraform"
      Compliance  = "FISC-APPI-FSA"
    }
  }
}

# 1. 3-Tier DR VPC Module (ap-northeast-3, 10.101.0.0/16)
module "vpc" {
  source      = "../../modules/vpc"
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
}

# 2. Security Module (KMS Multi-Region Keys & IAM Roles)
module "security" {
  source      = "../../modules/security"
  vpc_id      = module.vpc.vpc_id
  environment = var.environment
  aws_region  = var.aws_region
}

# 3. Application Load Balancer Module (DR Standby)
module "alb" {
  source            = "../../modules/alb"
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.security.alb_security_group_id
  environment       = var.environment
  certificate_arn   = var.certificate_arn
}

# 4. OpenSearch Serverless Module (Replica Collection)
module "opensearch" {
  source            = "../../modules/opensearch"
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.isolated_subnet_ids
  security_group_id = module.security.opensearch_security_group_id
  kms_key_arn       = module.security.kms_key_arn
  task_role_arn     = module.security.ecs_task_role_arn
}

# 5. AWS WAF v2 WebACL Module
module "waf" {
  source       = "../../modules/waf"
  environment  = var.environment
  alb_arn      = module.alb.alb_arn
  enable_cloudwatch = true
}

# 6. ECS Fargate Cluster & Service Module (Pilot Light: 1 Warm Task)
module "ecs" {
  source             = "../../modules/ecs"
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_app_subnet_ids
  security_group_id  = module.security.ecs_security_group_id
  target_group_arn   = module.alb.target_group_arn
  task_role_arn      = module.security.ecs_task_role_arn
  execution_role_arn = module.security.ecs_execution_role_arn
  container_image    = var.container_image
  desired_count      = var.desired_count
  cpu                = 2048
  memory             = 4096
}
