import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent.parent / '.env')

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_password")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "120"))
AI_FAIL_RATE = float(os.getenv("AI_FAIL_RATE", "0.0"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))
AI_REPLY_STRATEGY = os.getenv("AI_REPLY_STRATEGY", "all")
AI_MAX_GROUP_BOT_RESPONSES = int(os.getenv("AI_MAX_GROUP_BOT_RESPONSES", "2"))
SEED_USERS = os.getenv("SEED_USERS", "")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://free.v36.cm")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


