"""
Configuration settings module using Pydantic Settings.
Handles environment variables, Render-specific database URL conversion, and defaults.
"""
from typing import List, Set, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Telegram Configuration
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    admin_user_ids: str = Field(default="", alias="ADMIN_USER_IDS")

    # Google Gemini AI Configuration
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    embedding_model: str = Field(default="text-embedding-004", alias="EMBEDDING_MODEL")

    # Database & Cache Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/unicon_ai",
        alias="DATABASE_URL"
    )
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")

    # Webhook & Deployment
    webhook_url: Optional[str] = Field(default=None, alias="WEBHOOK_URL")
    webhook_path: str = Field(default="/webhook/telegram", alias="WEBHOOK_PATH")
    webhook_secret: Optional[str] = Field(default=None, alias="WEBHOOK_SECRET")
    port: int = Field(default=8000, alias="PORT")
    host: str = Field(default="0.0.0.0", alias="HOST")
    environment: str = Field(default="production", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Group Learning & Processing Settings
    group_batch_window_seconds: int = Field(default=45, alias="GROUP_BATCH_WINDOW_SECONDS")
    group_learning_default: bool = Field(default=True, alias="GROUP_LEARNING_DEFAULT")
    group_reply_default: bool = Field(default=False, alias="GROUP_REPLY_DEFAULT")
    max_memory_messages: int = Field(default=15, alias="MAX_MEMORY_MESSAGES")
    similarity_threshold: float = Field(default=0.72, alias="SIMILARITY_THRESHOLD")
    dedup_threshold: float = Field(default=0.92, alias="DEDUP_THRESHOLD")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> str:
        if not v:
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/unicon_ai"
        # Fix Render / standard Postgres URLs for async SQLAlchemy
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def admin_ids_set(self) -> Set[int]:
        """Returns parsed set of admin Telegram IDs."""
        if not self.admin_user_ids:
            return set()
        ids = set()
        for item in self.admin_user_ids.replace(";", ",").split(","):
            cleaned = item.strip()
            if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
                ids.add(int(cleaned))
        return ids

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def full_webhook_url(self) -> Optional[str]:
        if not self.webhook_url:
            return None
        base = self.webhook_url.rstrip("/")
        path = self.webhook_path if self.webhook_path.startswith("/") else f"/{self.webhook_path}"
        return f"{base}{path}"


settings = Settings()
