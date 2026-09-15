import datetime as dt

from sqlalchemy import delete

from app.config import get_settings
from app.db.models.market import PriceCandle
from app.db.models.news import NewsArticle
from app.db.session import session_scope

settings = get_settings()


async def run() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    candle_cutoff = now - dt.timedelta(days=settings.candle_retention_days)
    news_cutoff = now - dt.timedelta(days=settings.news_retention_days)

    async with session_scope() as session:
        await session.execute(
            delete(PriceCandle).where(PriceCandle.timeframe == "1m", PriceCandle.ts < candle_cutoff)
        )
        await session.execute(delete(NewsArticle).where(NewsArticle.published_at < news_cutoff))
        await session.commit()
