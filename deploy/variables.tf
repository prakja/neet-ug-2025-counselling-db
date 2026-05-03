variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Environment name (dev/stage/prod)"
  type        = string
  default     = "dev"
}

variable "existing_ecs_cluster_name" {
  description = "Existing ECS cluster name (shared with neet_knowledge_project)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where ECS tasks will run"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "additional_security_group_ids" {
  description = "Additional security groups for ECS tasks (e.g., default SG for DB access)"
  type        = list(string)
  default     = []
}

variable "counselling_bot_token_secret_arn" {
  description = "Secrets Manager ARN for COUNSELLING_BOT_TOKEN"
  type        = string
  default     = ""
}

variable "db_password_secret_arn" {
  description = "Secrets Manager ARN for DB_PASSWORD. Leave empty to use plain env var."
  type        = string
  default     = ""
}

variable "db_host" {
  description = "PostgreSQL host"
  type        = string
  default     = "neetprep-staging.cvvtorjqg7t7.ap-south-1.rds.amazonaws.com"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "learner_development"
}

variable "db_user" {
  description = "PostgreSQL username"
  type        = string
  default     = "learner"
}

variable "db_port" {
  description = "PostgreSQL port"
  type        = string
  default     = "5432"
}

variable "counselling_bot_desired_count" {
  description = "Number of desired ECS tasks"
  type        = number
  default     = 1
}

variable "use_fargate_spot" {
  description = "Use FARGATE_SPOT for cost savings"
  type        = bool
  default     = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
