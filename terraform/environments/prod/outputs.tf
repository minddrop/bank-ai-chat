output "alb_dns_name" {
  description = "Public Application Load Balancer DNS Endpoint"
  value       = module.alb.alb_dns_name
}

output "ecs_cluster_name" {
  description = "Production ECS Cluster Name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Production ECS Service Name"
  value       = module.ecs.service_name
}

output "kms_cmk_arn" {
  description = "KMS Customer Managed Key for In-VPC Token Vault"
  value       = module.security.kms_cmk_arn
}

output "opensearch_endpoint" {
  description = "OpenSearch Serverless Collection Endpoint"
  value       = module.opensearch.collection_endpoint
}
