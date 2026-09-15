from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.instruments_catalog import DEFAULT_WATCHLIST_CSV


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "staging", "production"] = "development"
    service_name: str = "turniping-backend"
    log_level: str = "INFO"
    log_format: Literal["plain", "json"] = "plain"

    app_api_token: str = "dev-local-token"
    session_secret: str = "dev-local-session-secret"
    allowed_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 120

    database_url: str = "postgresql+asyncpg://turniping:turniping@localhost:5432/turniping"
    redis_url: str = "redis://localhost:6379/0"

    # Market data / worker cadence
    price_poll_interval_seconds: int = 30
    news_ingest_interval_minutes: int = 5
    prediction_interval_minutes: int = 10
    outcome_eval_interval_minutes: int = 15
    prediction_horizon_minutes: int = 60

    candle_retention_days: int = 90
    news_retention_days: int = 30

    default_watchlist: str = DEFAULT_WATCHLIST_CSV

    paper_starting_cash_jpy: int = 1_000_000

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def default_watchlist_codes(self) -> list[str]:
        return [c.strip() for c in self.default_watchlist.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
