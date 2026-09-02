variable "vpc_cidr" {
  description = "IPv4 CIDR block for 3-Tier Banking VPC"
  type        = string
  default     = "10.100.0.0/16"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "azs" {
  description = "Multi-AZ availability zones in AWS Tokyo"
  type        = list(string)
  default     = ["ap-northeast-1a", "ap-northeast-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for Tier 1: Public Subnets (ALB & NAT Gateways)"
  type        = list(string)
  default     = ["10.100.1.0/24", "10.100.2.0/24"]
}

variable "app_subnet_cidrs" {
  description = "CIDR blocks for Tier 2: Private App Subnets (ECS Fargate)"
  type        = list(string)
  default     = ["10.100.11.0/24", "10.100.12.0/24"]
}

variable "data_subnet_cidrs" {
  description = "CIDR blocks for Tier 3: Isolated Data Subnets (VPC Endpoints & OpenSearch)"
  type        = list(string)
  default     = ["10.100.21.0/24", "10.100.22.0/24"]
}
