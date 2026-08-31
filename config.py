import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
    
    # Comma-separated admin Telegram IDs
    ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "").strip()
    ADMIN_IDS: List[int] = [
        int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()
    ]
    
    # AI provider options: "gemini", "openai", "auto"
    AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").lower().strip()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "recruitment_bot.db"))

config = Config()
