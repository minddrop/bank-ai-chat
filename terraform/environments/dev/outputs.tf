output "alb_dns_name" {
  description = "Public ALB Endpoint"
  value       = module.alb.alb_dns_name
}

output "ecs_cluster_name" {
  description = "Dev ECS Cluster Name"
  value       = module.ecs.cluster_name
}
