variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "app_subnet_ids" {
  description = "List of Tier 2 Private App Subnet IDs"
  type        = list(string)
}

variable "security_group_id" {
  description = "ECS Task Security Group ID"
  type        = string
}

variable "target_group_arn" {
  description = "ALB Target Group ARN"
  type        = string
}

variable "execution_role_arn" {
  description = "ECS Task Execution Role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS Task Role ARN"
  type        = string
}

variable "container_image" {
  description = "ECR Container Image URI"
  type        = string
  default     = "665192915466.dkr.ecr.ap-northeast-1.amazonaws.com/bank-ai-chat-app:latest"
}

variable "desired_count" {
  description = "Desired number of ECS Fargate tasks"
  type        = number
  default     = 2
}
