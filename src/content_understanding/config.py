from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every setting the app reads, from the environment or .env. .env.example lists them all (a test checks)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8809  # local default, derived from the app's name; the container uses 8000
    log_json: bool = False  # JSON log lines (the deploy sets it)
    # https://<resource>.services.ai.azure.com/ (scripts/azure-up.sh prints it); empty: extraction answers 503
    content_understanding_endpoint: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


def settings_without_env_file(**values: Any) -> Settings:
    """Settings from these values and the environment only: .env is not read (tests, tools)."""
    return Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]  (pydantic-settings' init option)
