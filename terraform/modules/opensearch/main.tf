# OpenSearch Serverless Module - Vector Store Collection & Policies (REQ-FUN-003 & ADR-0015)

# 1. Encryption Policy (KMS CMK Encrypted at Rest)
resource "aws_opensearchserverless_security_policy" "encryption" {
  name        = "bank-ai-faq-enc-${var.environment}"
  type        = "encryption"
  description = "FISC KMS CMK encryption policy for FAQ vector collection"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource = [
          "collection/bank-ai-faq-${var.environment}"
        ]
      }
    ]
    AWSOwnedKey = false
    KmsARN      = var.kms_key_arn
  })
}

# 2. VPC Endpoint for OpenSearch Serverless (Network Isolation)
resource "aws_opensearchserverless_vpc_endpoint" "aoss_vpce" {
  name               = "bank-ai-aoss-vpce-${var.environment}"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  security_group_ids = [var.security_group_id]
}

# 3. Network Policy (Strict VPC-only, Public Access Blocked)
resource "aws_opensearchserverless_security_policy" "network" {
  name        = "bank-ai-faq-net-${var.environment}"
  type        = "network"
  description = "Isolated network policy blocking public internet access"

  policy = jsonencode([
    {
      Description = "VPC-only access for FAQ vector store"
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/bank-ai-faq-${var.environment}"
          ]
        },
        {
          ResourceType = "dashboard"
          Resource = [
            "collection/bank-ai-faq-${var.environment}"
          ]
        }
      ]
      AllowFromPublic = false
      SourceVPCEs     = [aws_opensearchserverless_vpc_endpoint.aoss_vpce.id]
    }
  ])
}

# 4. OpenSearch Serverless Vector Collection (1024-dim Titan Text Embeddings v2)
resource "aws_opensearchserverless_collection" "faq" {
  name        = "bank-ai-faq-${var.environment}"
  type        = "VECTORSEARCH"
  description = "1024-dim Titan v2 Vector Store for Rakuten Bank FAQ"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network
  ]

  tags = {
    Name        = "bank-ai-faq-${var.environment}"
    Environment = var.environment
  }
}

# 5. Data Access Policy (Task Role Permission)
resource "aws_opensearchserverless_access_policy" "data_access" {
  name        = "bank-ai-faq-access-${var.environment}"
  type        = "data"
  description = "Grant ECS Task Role CRUD permissions on FAQ collection and indexes"

  policy = jsonencode([
    {
      Description = "ECS Task vector search and index operations"
      Principal   = [var.ecs_task_role_arn]
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/bank-ai-faq-${var.environment}"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DescribeCollectionItems",
            "aoss:UpdateCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource = [
            "index/bank-ai-faq-${var.environment}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
    }
  ])
}
