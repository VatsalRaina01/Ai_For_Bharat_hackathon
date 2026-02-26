"""Configuration and environment variables for LokSarthi."""
import os

# AWS Region
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Bedrock
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "2000"))
BEDROCK_TEMPERATURE = float(os.environ.get("BEDROCK_TEMPERATURE", "0.3"))

# DynamoDB
USERS_TABLE = os.environ.get("USERS_TABLE", "loksarthi-users")
SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "loksarthi-sessions")

# S3
DATA_BUCKET = os.environ.get("DATA_BUCKET", "loksarthi-data")

# Supported Languages
SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "en": "English",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
}

# Default language
DEFAULT_LANGUAGE = "hi"

# Session TTL (30 days in seconds)
SESSION_TTL_SECONDS = 30 * 24 * 60 * 60

# User TTL (1 year in seconds)
USER_TTL_SECONDS = 365 * 24 * 60 * 60
