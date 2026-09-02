# Outputs for Secondary DR Environment (AWS Osaka ap-northeast-3)

output "vpc_id" {
  description = "ID of the Osaka DR VPC"
  value       = module.vpc.vpc_id
}

output "alb_dns_name" {
  description = "DNS name of the Osaka DR ALB for Route 53 ARC Routing Control"
  value       = module.alb.alb_dns_name
}

output "ecs_service_name" {
  description = "Name of the DR ECS Fargate Service"
  value       = module.ecs.service_name
}
