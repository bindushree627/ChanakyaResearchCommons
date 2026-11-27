import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "chanakya_research_commons_secret_key_2026_vsem")
    DEBUG = False
    TESTING = False

    # Storage Paths
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    WAREHOUSE_DIR = DATA_DIR / "warehouse"
    SYNTHETIC_DATA_DIR = DATA_DIR / "synthetic"
    REPORTS_DIR = BASE_DIR / "reports"

    # Database
    # If DATABASE_URL is set (e.g. postgresql://user:pass@localhost:5432/chanakya), use it
    # Otherwise fallback seamlessly to local SQLite database
    SQLITE_PATH = DATA_DIR / "chanakya_commons.db"
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{SQLITE_PATH}")
    
    # DuckDB Data Warehouse
    DUCKDB_PATH = WAREHOUSE_DIR / "analytics.duckdb"

    # Semantic Embeddings
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    EMBEDDING_DIM = 384

    # LLM / RAG Assistant
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() in ("true", "1", "yes")

    # Ingestion APIs
    OPENALEX_API_URL = "https://api.openalex.org"
    OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "research@chanakya.ac.in")
    ARXIV_API_URL = "http://export.arxiv.org/api/query"

    # Security & Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400 * 7 # 7 days


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLITE_PATH = Config.DATA_DIR / "test_commons.db"
    DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
    DUCKDB_PATH = Config.WAREHOUSE_DIR / "test_analytics.duckdb"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
