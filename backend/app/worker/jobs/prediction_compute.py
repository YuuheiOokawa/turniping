import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.db.models.market import Instrument, PriceCandle, Watchlist
from app.db.models.news import NewsArticle, NewsInstrumentLink
from app.db.models.prediction import Prediction
from app.db.session import session_scope
from app.market_data.yahoo_jp import YahooFetchError, fetch_candles
from app.services.prediction_engine import combine_prediction

logger = logging.getLogger(__name__)
settings = get_settings()


async def _sync_daily_candles(session, instrument: Instrument) -> list[float]:
    try:
        candles = await fetch_candles(instrument.code, interval="1d", range_="6mo")
    except YahooFetchError as exc:
        logger.warning("daily candle fetch failed for %s: %s", instrument.code, exc)
        candles = []

    for candle in candles:
        stmt = (
            pg_insert(PriceCandle)
            .values(
                instrument_id=instrument.id,
                timeframe="1d",
                ts=candle.ts,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
            .on_conflict_do_update(
                constraint="uq_candle_key",
                set_={"open": candle.open, "high": candle.high, "low": candle.low,
                      "close": candle.close, "volume": candle.volume},
            )
        )
        await session.execute(stmt)

    if candles:
        return [c.close for c in candles]

    result = await session.execute(
        select(PriceCandle.close)
        .where(PriceCandle.instrument_id == instrument.id, PriceCandle.timeframe == "1d")
        .order_by(PriceCandle.ts.asc())
    )
    return [float(row) for row in result.scalars().all()]


async def _recent_sentiment(session, instrument_id: int) -> tuple[float, int]:
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)
    result = await session.execute(
        select(NewsArticle.sentiment_score)
        .join(NewsInstrumentLink, NewsInstrumentLink.news_id == NewsArticle.id)
        .where(NewsInstrumentLink.instrument_id == instrument_id, NewsArticle.published_at >= since)
    )
    scores = [float(s) for s in result.scalars().all()]
    if not scores:
        return 0.0, 0
    return sum(scores) / len(scores), len(scores)


async def run() -> None:
    async with session_scope() as session:
        result = await session.execute(
            select(Instrument).join(Watchlist, Watchlist.instrument_id == Instrument.id)
        )
        instruments = result.scalars().all()

        for instrument in instruments:
            closes = await _sync_daily_candles(session, instrument)
            if len(closes) < 5:
                continue

            sentiment_avg, news_count = await _recent_sentiment(session, instrument.id)
            prediction = combine_prediction(closes, sentiment_avg=sentiment_avg, news_count=news_count)
            if prediction is None:
                continue

            session.add(
                Prediction(
                    instrument_id=instrument.id,
                    horizon_minutes=settings.prediction_horizon_minutes,
                    direction=prediction.direction,
                    confidence=prediction.confidence,
                    technical_score=prediction.technical_score,
                    sentiment_score=prediction.sentiment_score,
                    reference_price=prediction.reference_price,
                    reasons=prediction.reasons,
                )
            )

        await session.commit()
