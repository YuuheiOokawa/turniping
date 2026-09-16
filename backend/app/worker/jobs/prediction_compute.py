import asyncio
import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.db.models.market import Instrument, PriceCandle, Watchlist
from app.db.models.news import NewsArticle, NewsInstrumentLink
from app.db.models.prediction import Prediction
from app.db.session import session_scope
from app.market_data.yahoo_jp import Candle, YahooFetchError, fetch_candles
from app.services.prediction_engine import combine_prediction, compute_technical_score
from app.services.strategy_learning import load_weights

logger = logging.getLogger(__name__)
settings = get_settings()

MARKET_INDEX_CODE = "^N225"
# 79銘柄を1件ずつ順番に取得すると、Yahoo側が遅い/落ちている時に
# このジョブ1回で数分〜十数分かかり、他のジョブ(答え合わせ等)の
# スケジュール枠を奪ってしまう(実際に outcome_eval が15時間動かなく
# なる事故が発生した)。同時実行数を絞りつつ並行取得して worst-case を
# 大幅に縮める。
CONCURRENT_FETCH_LIMIT = 10


async def _fetch_one(semaphore: asyncio.Semaphore, instrument: Instrument) -> tuple[Instrument, list[Candle]]:
    async with semaphore:
        try:
            candles = await fetch_candles(instrument.code, interval="1d", range_="6mo")
        except YahooFetchError as exc:
            logger.warning("daily candle fetch failed for %s: %s", instrument.code, exc)
            candles = []
        return instrument, candles


async def _upsert_candles(session, instrument: Instrument, candles: list[Candle]) -> tuple[list[float], list[float]]:
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
        return [c.close for c in candles], [c.volume for c in candles]

    result = await session.execute(
        select(PriceCandle.close, PriceCandle.volume)
        .where(PriceCandle.instrument_id == instrument.id, PriceCandle.timeframe == "1d")
        .order_by(PriceCandle.ts.asc())
    )
    rows = result.all()
    return [float(r[0]) for r in rows], [float(r[1]) for r in rows]


async def _recent_sentiment(session, instrument_id: int) -> tuple[float, int]:
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=settings.sentiment_lookback_hours)
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

        semaphore = asyncio.Semaphore(CONCURRENT_FETCH_LIMIT)
        fetch_results = await asyncio.gather(*(_fetch_one(semaphore, i) for i in instruments))

        data_by_instrument: dict[int, tuple[list[float], list[float]]] = {}
        for instrument, candles in fetch_results:
            data_by_instrument[instrument.id] = await _upsert_candles(session, instrument, candles)

        # 市場全体(日経平均)のテクニカルスコアを算出し、個別銘柄が相場全体と
        # 同じ方向を向いているか("Don't fight the tape")の判断材料にする。
        market_score: float | None = None
        market_instrument = next((i for i in instruments if i.code == MARKET_INDEX_CODE), None)
        if market_instrument is not None:
            market_closes, _market_volumes = data_by_instrument.get(market_instrument.id, ([], []))
            if len(market_closes) >= 5:
                market_score, _, _ = compute_technical_score(market_closes)

        # 答え合わせの実績に基づき自己学習(strategy_learning.py)が調整した
        # シグナルごとの重み。まだ十分なデータが無いシグナルは既定の1.0のまま。
        weights = await load_weights(session)

        for instrument in instruments:
            closes, volumes = data_by_instrument.get(instrument.id, ([], []))
            if len(closes) < 5:
                continue

            sentiment_avg, news_count = await _recent_sentiment(session, instrument.id)
            prediction = combine_prediction(
                closes,
                sentiment_avg=sentiment_avg,
                news_count=news_count,
                volumes=volumes,
                market_score=market_score if instrument.id != getattr(market_instrument, "id", None) else None,
                weights=weights,
            )
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
                    signal_contributions=prediction.signal_contributions,
                )
            )

        await session.commit()
