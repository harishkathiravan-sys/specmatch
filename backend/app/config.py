"""Application configuration."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "SpecMatch_Data_V03_FINAL" / "ManakSetu_BIS_Data_V03"
DB_PATH = BASE_DIR / "specmatch.db"

# Dataset version (displayed in UI)
DATASET_VERSION = os.getenv("DATASET_VERSION", "V0.3")
STANDARDS_COUNT = os.getenv("STANDARDS_COUNT", "24,132")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")
IS_POSTGRES = DATABASE_URL.startswith(("postgresql://", "postgres://"))

# API settings
API_PREFIX = "/api"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# Search settings
SEARCH_PAGE_SIZE = 20
SEARCH_MAX_PAGE_SIZE = 100
FTS_TOKENIZER = "porter unicode61"

# Recommendation settings
TOP_K_CANDIDATES = 50
TOP_K_RECOMMENDATIONS = 5

# File upload settings
MAX_UPLOAD_SIZE_MB = 10
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt"}

# LLM settings (OpenRouter)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "2048"))
OPENROUTER_TEMPERATURE = float(os.getenv("OPENROUTER_TEMPERATURE", "0.3"))

# Embedding / reranker (legacy optional)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
RERANKER_PROVIDER = os.getenv("RERANKER_PROVIDER", "")
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))
