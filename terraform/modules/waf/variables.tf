variable "alb_arn" {
  description = "Application Load Balancer ARN to associate with WAF"
  type        = string
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "rate_limit_threshold" {
  description = "Maximum number of requests per 5-minute window per IP"
  type        = number
  default     = 1000
}
