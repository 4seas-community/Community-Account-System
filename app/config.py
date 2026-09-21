from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./cas.db"
    jwt_secret: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    checkin_secret: str = "dev-checkin-secret"
    admin_key: str = "dev-admin-key"

    access_token_ttl_minutes: int = 60
    verify_token_ttl_hours: int = 24
    login_token_ttl_minutes: int = 15

    email_backend: str = "console"  # console | smtp
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "no-reply@4seas.example"

    telegram_bot_token: str = ""

    webhook_timeout_seconds: int = 5
    webhook_max_attempts: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
