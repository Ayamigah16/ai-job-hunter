"""Environment-driven settings. Nothing here is required until Phase 4+ —
fields are optional so `validate-config`/`fetch --dry-run` work with no .env."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_application_credentials: str | None = None
    google_sheets_spreadsheet_id: str | None = None

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    notify_email_from: str | None = None
    notify_email_to: str | None = None

    score_threshold_write: int = 40
    score_threshold_notify: int = 70


def get_settings() -> Settings:
    return Settings()
