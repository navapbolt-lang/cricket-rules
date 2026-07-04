"""Application configuration via environment variables.

Loads settings from .env using pydantic-settings. All values can be
overridden via environment variables (case-insensitive).
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_api_keys: str = ""  # Comma-separated fallback keys
    groq_api_key: str = ""
    groq_api_keys: str = ""  # Comma-separated fallback keys
    serpapi_key: str = ""
    serpapi_keys: str = ""  # Comma-separated fallback keys
    web_search_enabled: bool = True
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "all-MiniLM-L6-v2"

    vector_db_type: str = "qdrant"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    database_url: str = (
        "postgresql+asyncpg://user:password@localhost:5432/cricket_rules"
    )
    redis_url: str = "redis://localhost:6379"

    admin_api_key: str = "admin-secret-key"
    jwt_secret: str = "change-me-in-production"

    default_plan: str = "starter"
    default_monthly_quota: int = 10000

    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_device: str = "cpu"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()
