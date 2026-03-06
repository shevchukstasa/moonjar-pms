"""
Moonjar PMS — Application configuration.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/moonjar"

    # JWT
    SECRET_KEY: str = "change-to-random-64-char-string"
    SECRET_KEY_PREVIOUS: str = ""
    JWT_ACCESS_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_MINUTES: int = 10080  # 7 days

    # CORS
    CORS_ORIGINS: str = "http://localhost:5174,http://localhost:5175"

    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID: str = ""

    # Owner setup
    OWNER_KEY: str = "change-me"

    # TOTP
    TOTP_ENCRYPTION_KEY: str = "change-this-to-random-32-char-key"

    # Backup
    BACKUP_ENCRYPTION_KEY: str = ""
    S3_BACKUP_BUCKET: str = ""
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "ap-southeast-1"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_OWNER_CHAT_ID: str = ""

    # Sales integration
    SALES_APP_URL: str = ""
    SALES_APP_API_KEY: str = ""
    PRODUCTION_WEBHOOK_ENABLED: bool = True
    PRODUCTION_WEBHOOK_AUTH_MODE: str = "bearer"
    PRODUCTION_WEBHOOK_BEARER_TOKEN: str = ""
    PRODUCTION_WEBHOOK_HMAC_SECRET: str = ""

    # AI
    OPENAI_API_KEY: str = ""

    # IP allowlist
    ADMIN_IP_ALLOWLIST: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
