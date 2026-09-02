# Variables for Secondary DR Environment (AWS Osaka ap-northeast-3)

variable "aws_region" {
  description = "AWS Region for Secondary Disaster Recovery"
  type        = string
  default     = "ap-northeast-3"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dr-osaka"
}

variable "vpc_cidr" {
  description = "VPC CIDR block for Osaka DR VPC (REQ-OPS-017 §1.3)"
  type        = string
  default     = "10.101.0.0/16"
}

variable "container_image" {
  description = "Container image URI in ECR"
  type        = string
  default     = "123456789012.dkr.ecr.ap-northeast-3.amazonaws.com/bank-ai-chat:latest"
}

variable "desired_count" {
  description = "Pilot light standby task count"
  type        = number
  default     = 1
}

variable "certificate_arn" {
  description = "ACM Certificate ARN for DR ALB"
  type        = string
  default     = "arn:aws:acm:ap-northeast-3:123456789012:certificate/dr-placeholder"
}
