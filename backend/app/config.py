import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # LLM & API Keys
    LLM_PROVIDER: str = "openai"  # "openai" or "google"
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Databases
    # Example: postgresql+asyncpg://research_user:research_password@localhost:5432/deep_research_platform
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Comma-separated list of allowed browser origins for CORS
    CORS_ORIGINS: str = "http://localhost:3000"
    # Regex for preview/production hosts (e.g. *.vercel.app). Set empty to disable.
    CORS_ORIGIN_REGEX: str = r"https://.*\.vercel\.app"

    # Fallback to local SQLite when DATABASE_URL is not set
    SQLITE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/deep_research.db"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def db_url(self) -> str:
        """Returns PostgreSQL if configured, otherwise falls back to SQLite."""
        if self.DATABASE_URL:
            # For SQLAlchemy async, ensure we use postgresql+asyncpg
            url = self.DATABASE_URL
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return self.SQLITE_URL

    @property
    def is_postgres(self) -> bool:
        return bool(self.DATABASE_URL)

    @property
    def is_redis(self) -> bool:
        return bool(self.REDIS_URL)

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def cors_origin_regex(self) -> Optional[str]:
        value = self.CORS_ORIGIN_REGEX.strip()
        return value or None

# Instantiate settings
settings = Settings()
