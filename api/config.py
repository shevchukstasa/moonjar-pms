"""
Moonjar PMS — Application configuration.
"""

import logging
import os
from pydantic_settings import BaseSettings
from functools import lru_cache

_config_logger = logging.getLogger("moonjar.config")

# Secrets that MUST be overridden before production
_INSECURE_DEFAULTS = {
    "change-to-random-64-char-string",
    "change-me",
    "change-this-to-random-32-char-key",
}


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

    # Public API URL (for Telegram webhook registration, etc.)
    # Auto-detected from RAILWAY_PUBLIC_DOMAIN if not set explicitly.
    API_BASE_URL: str = ""

    @property
    def api_base_url(self) -> str:
        """Resolve API base URL from explicit config or Railway domain."""
        if self.API_BASE_URL:
            return self.API_BASE_URL.rstrip("/")
        # Railway auto-provides this env var
        railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
        if railway_domain:
            return f"https://{railway_domain}"
        return ""

    # Sales integration
    SALES_APP_URL: str = ""
    SALES_APP_API_KEY: str = ""
    PRODUCTION_WEBHOOK_ENABLED: bool = True
    PRODUCTION_WEBHOOK_AUTH_MODE: str = "bearer"
    PRODUCTION_WEBHOOK_BEARER_TOKEN: str = ""
    PRODUCTION_WEBHOOK_HMAC_SECRET: str = ""

    # AI
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # IP allowlist
    ADMIN_IP_ALLOWLIST: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def model_post_init(self, __context) -> None:
        """Strip whitespace from all secret/key fields to prevent copy-paste issues."""
        for field in (
            "SECRET_KEY", "SECRET_KEY_PREVIOUS", "OWNER_KEY",
            "TOTP_ENCRYPTION_KEY", "BACKUP_ENCRYPTION_KEY",
            "SALES_APP_API_KEY", "PRODUCTION_WEBHOOK_BEARER_TOKEN",
            "PRODUCTION_WEBHOOK_HMAC_SECRET", "GOOGLE_OAUTH_CLIENT_ID",
            "TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
            "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY",
        ):
            val = getattr(self, field, None)
            if val and val != val.strip():
                object.__setattr__(self, field, val.strip())

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    _is_production = bool(
        os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENV", "").lower() == "production"
    )
    # In production, REFUSE to start with insecure default secrets
    # Critical secrets block startup; non-critical ones only warn
    critical_insecure = []
    warn_insecure = []
    if s.SECRET_KEY in _INSECURE_DEFAULTS:
        critical_insecure.append("SECRET_KEY")
    if s.OWNER_KEY in _INSECURE_DEFAULTS:
        critical_insecure.append("OWNER_KEY")
    # TOTP is implemented — block startup with insecure default
    if s.TOTP_ENCRYPTION_KEY in _INSECURE_DEFAULTS:
        critical_insecure.append("TOTP_ENCRYPTION_KEY")

    if critical_insecure and _is_production:
        raise RuntimeError(
            f"FATAL: insecure default values for: {', '.join(critical_insecure)}. "
            f"Set proper secrets via environment variables before starting in production."
        )
    all_insecure = critical_insecure + warn_insecure
    if all_insecure:
        _config_logger.warning(
            f"⚠ Insecure default secrets detected: {', '.join(all_insecure)}. "
            f"Set proper values in .env before deploying to production."
        )
    return s
