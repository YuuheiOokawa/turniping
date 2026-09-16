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
    # Google Newsの企業名検索はヒット件数が少ない銘柄も多く、24時間だと
    # センチメントが拾えない銘柄が大半になる(実データで確認済み)。
    # 60分先を予想するタスクにはニュースの多少の陳腐化は許容範囲として、
    # 母数を確保するため48時間まで見る。
    sentiment_lookback_hours: int = 48

    candle_retention_days: int = 90
    news_retention_days: int = 30

    default_watchlist: str = DEFAULT_WATCHLIST_CSV

    paper_starting_cash_jpy: int = 1_000_000

    # AI自動売買シミュレーション(ユーザーの手動ペーパートレードとは別口座)
    ai_trader_starting_cash_jpy: int = 50_000
    auto_trader_interval_minutes: int = 10
    # 1銘柄あたりの最大投資額。5万円全額を1銘柄に賭けさせず、複数銘柄に分散させるため上限を設ける。
    auto_trader_max_position_jpy: int = 10_000
    # prediction_engineの連続スコアリング方式では、実データ上の確信度は
    # 中央値17%・90パーセンタイル34%程度で、60%はほぼ出現しない(実測済み)。
    # 「上位1割程度の強いシグナルのみで動く」を狙い、90パーセンタイル近辺の
    # 35%を既定閾値とする。
    auto_trader_buy_confidence_threshold: float = 35.0
    auto_trader_sell_confidence_threshold: float = 35.0

    # 自己学習: 答え合わせ実績から各シグナルの重みを再計算する頻度。
    strategy_learning_interval_minutes: int = 60

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def default_watchlist_codes(self) -> list[str]:
        return [c.strip() for c in self.default_watchlist.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
