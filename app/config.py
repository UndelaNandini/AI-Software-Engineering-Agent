from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Configuration
    PROJECT_NAME: str = "AI Software Engineering Agent"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEFAULT_MODEL: str = "gpt-4o"

    # Agent Limits
    MAX_REPAIR_ATTEMPTS: int = 3
    EXECUTION_TIMEOUT_SECONDS: int = 60
    MAX_FILE_SIZE_BYTES: int = 1_000_000  # 1 MB max per file to avoid context blowup

    # Workspace Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent


@lru_cache()
def get_settings() -> Settings:
    return Settings()
