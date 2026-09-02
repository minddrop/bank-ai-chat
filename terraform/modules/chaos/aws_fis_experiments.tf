# ==============================================================================
# AWS Fault Injection Service (FIS) Infrastructure Chaos Templates
# Compliant with FISC Safety Standards (第9版) & ADR-0023
# Deployed in AWS Tokyo (ap-northeast-1)
# ==============================================================================

variable "environment" {
  type        = string
  default     = "staging"
  description = "Target deployment environment (staging, dr-sandbox)"
}

variable "ecs_cluster_arn" {
  type        = string
  description = "ARN of the Bank AI ECS Fargate Cluster"
}

variable "ecs_service_name" {
  type        = string
  description = "Name of the Bank AI Backend ECS Service"
}

variable "cloudwatch_alarm_5xx_arn" {
  type        = string
  description = "ARN of ALB 5XX CloudWatch Alarm for Emergency Abort Condition"
}

# ------------------------------------------------------------------------------
# IAM Role for AWS FIS Service Execution
# ------------------------------------------------------------------------------

resource "aws_iam_role" "fis_service_role" {
  name = "bank-ai-chaos-fis-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "fis.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Compliance  = "FISC-Safety-Std-9"
    System      = "BankAIChat"
  }
}

resource "aws_iam_policy" "fis_ecs_actions" {
  name        = "bank-ai-chaos-fis-ecs-policy-${var.environment}"
  description = "Permissions for AWS FIS to stop ECS Fargate tasks during GameDays"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:ListTasks",
          "ecs:DescribeTasks",
          "ecs:StopTask"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:DescribeAlarms"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "fis_ecs_attach" {
  role       = aws_iam_role.fis_service_role.name
  policy_arn = aws_iam_policy.fis_ecs_actions.arn
}

# ------------------------------------------------------------------------------
# Experiment 1: ECS Task Sudden Termination (Multi-AZ Failover Drill)
# ------------------------------------------------------------------------------

resource "aws_fis_experiment_template" "fargate_task_termination" {
  description = "FISC GameDay: Stop random ECS tasks in ap-northeast-1a to verify zero-downtime ALB failover"
  role_arn    = aws_iam_role.fis_service_role.arn

  stop_condition {
    source = "aws:cloudwatch:alarm"
    value  = var.cloudwatch_alarm_5xx_arn
  }

  action {
    name      = "stop-fargate-task"
    action_id = "aws:ecs:stop-task"

    target {
      key   = "Tasks"
      value = "TargetTasksInAzA"
    }
  }

  target {
    name           = "TargetTasksInAzA"
    resource_type  = "aws:ecs:task"
    selection_mode = "COUNT(1)"

    resource_tag {
      key   = "AvailabilityZone"
      value = "ap-northeast-1a"
    }

    parameters = {
      cluster = var.ecs_cluster_arn
      service = var.ecs_service_name
    }
  }

  tags = {
    Name        = "bank-ai-fargate-task-kill"
    FiscRef     = "FISC-Safety-Std-9-Reliability-1.1"
    Environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# Experiment 2: ECS CPU Stress Simulation (Auto-scaling Step-Scaling Drill)
# ------------------------------------------------------------------------------

resource "aws_fis_experiment_template" "fargate_cpu_stress" {
  description = "FISC GameDay: Inject CPU load to trigger ECS Step-Scaling from 2 to 10 tasks under 1000 TPS load"
  role_arn    = aws_iam_role.fis_service_role.arn

  stop_condition {
    source = "aws:cloudwatch:alarm"
    value  = var.cloudwatch_alarm_5xx_arn
  }

  action {
    name      = "cpu-stress"
    action_id = "aws:ssm:send-command"

    parameter {
      key   = "documentArn"
      value = "arn:aws:ssm:ap-northeast-1::document/AWSFIS-Run-CPU-Stress"
    }
    parameter {
      key   = "documentParameters"
      value = jsonencode({ DurationSeconds = "180", CPU = "90" })
    }
    parameter {
      key   = "duration"
      value = "PT3M"
    }

    target {
      key   = "Instances"
      value = "TargetEcsContainers"
    }
  }

  target {
    name           = "TargetEcsContainers"
    resource_type  = "aws:ec2:instance"
    selection_mode = "PERCENT(50)"

    resource_tag {
      key   = "System"
      value = "BankAIChat"
    }
  }

  tags = {
    Name        = "bank-ai-cpu-stress-step-scaling"
    FiscRef     = "FISC-Safety-Std-9-Capacity-1.0"
    Environment = var.environment
  }
}
