variable "aws_region" {
  description = "AWS Tokyo Region"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "container_image" {
  description = "ECR Image URI"
  type        = string
  default     = "665192915466.dkr.ecr.ap-northeast-1.amazonaws.com/bank-ai-chat-app:latest"
}

variable "certificate_arn" {
  description = "ACM Certificate ARN for production domain"
  type        = string
  default     = ""
}
