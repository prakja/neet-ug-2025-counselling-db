terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name_prefix = "neet-counselling-${var.environment}"

  common_tags = merge(
    {
      Project     = "neet-counselling"
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.tags
  )

  exec_secret_arns = compact([
    var.counselling_bot_token_secret_arn != "" ? var.counselling_bot_token_secret_arn : "",
    var.db_password_secret_arn != "" ? var.db_password_secret_arn : ""
  ])

  container_secrets = concat(
    var.counselling_bot_token_secret_arn != "" ? [{ name = "COUNSELLING_BOT_TOKEN", valueFrom = var.counselling_bot_token_secret_arn }] : [],
    var.db_password_secret_arn != "" ? [{ name = "DB_PASSWORD", valueFrom = var.db_password_secret_arn }] : []
  )
}

data "aws_ecs_cluster" "shared" {
  cluster_name = var.existing_ecs_cluster_name
}

data "aws_vpc" "selected" {
  id = var.vpc_id
}

resource "aws_cloudwatch_log_group" "counselling" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 30
}

resource "aws_ecr_repository" "counselling" {
  name = "${local.name_prefix}"

  image_scanning_configuration {
    scan_on_push = true
  }

  force_delete = true
}

resource "aws_security_group" "counselling" {
  name        = "${local.name_prefix}-tasks"
  description = "Security group for counselling bot ECS tasks"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  count = length(local.exec_secret_arns) > 0 ? 1 : 0

  name = "${local.name_prefix}-exec-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["secretsmanager:GetSecretValue"]
        Resource = local.exec_secret_arns
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "counselling" {
  family                   = "${local.name_prefix}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = "counselling"
      image     = "${aws_ecr_repository.counselling.repository_url}:latest"
      essential = true
      command   = ["python", "run_counselling_bot.py"]

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DB_HOST", value = var.db_host },
        { name = "DB_NAME", value = var.db_name },
        { name = "DB_USER", value = var.db_user },
        { name = "DB_PORT", value = var.db_port }
      ]

      secrets = local.container_secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.counselling.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags
}

resource "aws_ecs_service" "counselling" {
  name                   = "${local.name_prefix}"
  cluster                = data.aws_ecs_cluster.shared.id
  task_definition        = aws_ecs_task_definition.counselling.arn
  desired_count          = var.counselling_bot_desired_count

  dynamic "capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = 1
      base              = 0
    }
  }

  dynamic "capacity_provider_strategy" {
    for_each = var.use_fargate_spot ? [] : [1]
    content {
      capacity_provider = "FARGATE"
      weight            = 1
      base              = 0
    }
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.counselling.id]
    assign_public_ip = true
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = local.common_tags
}
