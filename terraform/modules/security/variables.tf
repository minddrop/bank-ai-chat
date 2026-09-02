variable "vpc_id" {
  description = "VPC ID where security groups reside"
  type        = string
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS Tokyo Region"
  type        = string
  default     = "ap-northeast-1"
}
