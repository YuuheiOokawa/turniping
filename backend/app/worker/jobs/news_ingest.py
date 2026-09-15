import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models.market import Instrument, Watchlist
from app.db.models.news import NewsArticle, NewsInstrumentLink
from app.db.session import session_scope
from app.services import sentiment
from app.services.news_ingest import RawArticle, fetch_articles_for_instrument, fetch_general_market_news

logger = logging.getLogger(__name__)


async def _upsert_article(session, article: RawArticle) -> NewsArticle:
    existing = await session.execute(select(NewsArticle).where(NewsArticle.url == article.url))
    row = existing.scalar_one_or_none()
    if row is not None:
        return row

    score = sentiment.score_text(f"{article.title} {article.summary}")
    news = NewsArticle(
        source=article.source,
        url=article.url,
        title=article.title,
        summary=article.summary,
        published_at=article.published_at,
        sentiment_score=score,
        sentiment_label=sentiment.label_for_score(score),
    )
    session.add(news)
    await session.flush()
    return news


async def _link(session, news_id: int, instrument_id: int) -> None:
    stmt = (
        pg_insert(NewsInstrumentLink)
        .values(news_id=news_id, instrument_id=instrument_id)
        .on_conflict_do_nothing(constraint="uq_news_instrument")
    )
    await session.execute(stmt)


async def run() -> None:
    async with session_scope() as session:
        general_articles = await fetch_general_market_news()
        for article in general_articles:
            await _upsert_article(session, article)

        result = await session.execute(
            select(Instrument).join(Watchlist, Watchlist.instrument_id == Instrument.id)
        )
        instruments = result.scalars().all()

        for instrument in instruments:
            try:
                articles = await fetch_articles_for_instrument(instrument.name)
            except Exception as exc:  # feedparser network failures shouldn't kill the job
                logger.warning("news fetch failed for %s: %s", instrument.code, exc)
                continue
            for article in articles:
                news = await _upsert_article(session, article)
                await _link(session, news.id, instrument.id)

        await session.commit()
