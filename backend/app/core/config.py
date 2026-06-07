from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM API (OpenAI-compatible)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data.db"

    # Limits
    max_upload_size_bytes: int = 512_000  # 500KB
    max_chapter_length_chars: int = 16_000  # per chapter for LLM

    # R2 sliding window
    r2_window_size: int = 4000  # chars per window
    r2_overlap_size: int = 800  # overlap between adjacent windows


settings = Settings()
