"""
Application configuration — loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

# ── HubSpot ───────────────────────────────────────────────────────────────────
HUBSPOT_PRIVATE_APP_TOKEN: str = os.getenv("HUBSPOT_PRIVATE_APP_TOKEN", "")
HUBSPOT_BASE_URL: str = "https://api.hubapi.com"

# ── Target Website ────────────────────────────────────────────────────────────
TARGET_WEBSITE_URL: str = os.getenv("TARGET_WEBSITE_URL", "https://www.polymedicure.com")

# ── App ───────────────────────────────────────────────────────────────────────
APP_ENV: str = os.getenv("APP_ENV", "development")
SESSION_EXPIRY_MINUTES: int = int(os.getenv("SESSION_EXPIRY_MINUTES", "30"))

# ── Storage ───────────────────────────────────────────────────────────────────
CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./data/chromadb")
SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./data/leads.db")

# ── Retrieval ─────────────────────────────────────────────────────────────────
RAG_TOP_K: int = 5
RAG_SIMILARITY_THRESHOLD: float = 0.40   # cosine distance (lower = more similar)
CHUNK_CHAR_SIZE: int = 1500              # ~375 tokens per chunk
CHUNK_OVERLAP_CHARS: int = 200

# ── Validation ────────────────────────────────────────────────────────────────
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in .env file")
