output "collection_id" {
  description = "OpenSearch Serverless Collection ID"
  value       = aws_opensearchserverless_collection.faq.id
}

output "collection_arn" {
  description = "OpenSearch Serverless Collection ARN"
  value       = aws_opensearchserverless_collection.faq.arn
}

output "collection_endpoint" {
  description = "OpenSearch Serverless Collection Endpoint"
  value       = aws_opensearchserverless_collection.faq.collection_endpoint
}
