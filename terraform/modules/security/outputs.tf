output "alb_security_group_id" {
  description = "ALB Security Group ID"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ECS Task Security Group ID"
  value       = aws_security_group.ecs.id
}

output "opensearch_security_group_id" {
  description = "OpenSearch Serverless Security Group ID"
  value       = aws_security_group.opensearch.id
}

output "vpce_security_group_id" {
  description = "VPC Endpoints Security Group ID"
  value       = aws_security_group.vpce.id
}

output "kms_cmk_arn" {
  description = "KMS Customer Managed Key ARN"
  value       = aws_kms_key.bank_vault.arn
}

output "kms_cmk_alias_arn" {
  description = "KMS CMK Alias ARN"
  value       = aws_kms_alias.bank_vault.arn
}

output "ecs_execution_role_arn" {
  description = "ECS Task Execution Role ARN"
  value       = aws_iam_role.ecs_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ECS Task Role ARN"
  value       = aws_iam_role.ecs_task_role.arn
}
