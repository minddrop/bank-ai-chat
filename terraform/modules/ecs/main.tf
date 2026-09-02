# ECS Module - ECS Fargate Cluster, Task Definition & Service (REQ-OPS-017 §2.3)

# 1. CloudWatch Log Group for Application & Guardrail Logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/ecs/bank-ai-chat-${var.environment}"
  retention_in_days = 365

  tags = {
    Name        = "bank-ai-logs-${var.environment}"
    Environment = var.environment
  }
}

# 2. ECS Cluster with Container Insights
resource "aws_ecs_cluster" "main" {
  name = "bank-ai-production-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "bank-ai-cluster-${var.environment}"
    Environment = var.environment
  }
}

# 3. ECS Fargate Task Definition (2 vCPU / 4 GB)
resource "aws_ecs_task_definition" "app" {
  family                   = "bank-ai-task-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([
    {
      name      = "bank-ai-container"
      image     = var.container_image
      essential = true

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "LLM_PROVIDER", value = "bedrock" },
        { name = "AWS_DEFAULT_REGION", value = "ap-northeast-1" },
        { name = "PORT", value = "8000" },
        { name = "PYTHONUNBUFFERED", value = "1" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.app_logs.name
          "awslogs-region"        = "ap-northeast-1"
          "awslogs-stream-prefix" = "bank-ai"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 15
      }
    }
  ])

  tags = {
    Name        = "bank-ai-task-def-${var.environment}"
    Environment = var.environment
  }
}

# 4. ECS Fargate Service (Multi-AZ Deployment)
resource "aws_ecs_service" "app" {
  name            = "bank-ai-backend-service-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.app_subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "bank-ai-container"
    container_port   = 8000
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Name        = "bank-ai-service-${var.environment}"
    Environment = var.environment
  }
}
