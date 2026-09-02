variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "kms_key_arn" {
  description = "KMS CMK ARN for OpenSearch Serverless encryption-at-rest"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where OpenSearch VPC Endpoint is deployed"
  type        = string
}

variable "subnet_ids" {
  description = "Isolated data subnet IDs for OpenSearch VPC Endpoint"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for OpenSearch VPC Endpoint"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS Task Role ARN granted data access"
  type        = string
}
