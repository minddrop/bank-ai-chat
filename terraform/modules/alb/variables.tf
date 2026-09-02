variable "vpc_id" {
  description = "VPC ID where the ALB target group is created"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of Tier 1 Public Subnet IDs"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security Group ID for ALB"
  type        = string
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "certificate_arn" {
  description = "ACM Certificate ARN for HTTPS listener"
  type        = string
  default     = ""
}
