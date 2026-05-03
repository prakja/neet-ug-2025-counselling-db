aws_region  = "ap-south-1"
environment = "dev"

existing_ecs_cluster_name = "np-pgrest"
vpc_id                      = "vpc-04631eeddd864b8b3"
private_subnet_ids = [
  "subnet-0d6de2dce64c5edab",
  "subnet-0da960e96ca52559b",
  "subnet-0e4b884bd5bf7a94b"
]

# Attach default SG to enable Aurora DB connectivity
additional_security_group_ids = [
  "sg-07a6946d804345bf4"
]

# Secrets - leave empty if using plain env vars for staging
counselling_bot_token_secret_arn = ""
db_password_secret_arn           = ""

# DB config for prod Aurora cluster
db_host   = "neetprep-aurora-cluster-mumbai.cluster-cvvtorjqg7t7.ap-south-1.rds.amazonaws.com"
db_user   = "neet_bot_user"
db_name   = "learner_development"
db_port   = "5432"

# Fargate Spot for cost savings
use_fargate_spot = true

# Task count
counselling_bot_desired_count = 1

tags = {
  Project     = "neet-counselling"
  Environment = "dev"
  ManagedBy   = "terraform"
}
