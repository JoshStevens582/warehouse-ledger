from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH) if _ENV_PATH.is_file() else ".env",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://ledger:ledger@localhost:5432/warehouse_ledger"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 480
    paystack_secret_key: str = ""
    paystack_public_key: str = ""
    checkout_callback_url: str = "http://localhost:5173/"
    cors_origins: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
