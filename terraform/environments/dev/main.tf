# Development Environment Root Module (REQ-OPS-017 & ADR-0016)
# Lightweight staging configuration for AWS Tokyo (ap-northeast-1)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "JapaneseMajorBank-AIChat"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

module "vpc" {
  source      = "../../modules/vpc"
  environment = var.environment
}

module "security" {
  source      = "../../modules/security"
  vpc_id      = module.vpc.vpc_id
  environment = var.environment
  aws_region  = var.aws_region
}

module "alb" {
  source            = "../../modules/alb"
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.security.alb_security_group_id
  environment       = var.environment
  certificate_arn   = ""
}

module "ecs" {
  source             = "../../modules/ecs"
  environment        = var.environment
  app_subnet_ids     = module.vpc.app_subnet_ids
  security_group_id  = module.security.ecs_security_group_id
  target_group_arn   = module.alb.target_group_arn
  execution_role_arn = module.security.ecs_execution_role_arn
  task_role_arn      = module.security.ecs_task_role_arn
  container_image    = var.container_image
  desired_count      = 1
}
