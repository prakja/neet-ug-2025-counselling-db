import os

COUNSELLING_BOT_TOKEN = os.getenv("COUNSELLING_BOT_TOKEN")
DB_HOST = os.getenv("DB_HOST", "neetprep-staging.cvvtorjqg7t7.ap-south-1.rds.amazonaws.com")
DB_NAME = os.getenv("DB_NAME", "learner_development")
DB_USER = os.getenv("DB_USER", "learner")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
