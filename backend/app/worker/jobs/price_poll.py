import asyncio
import json
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models.market import Instrument, PriceCandle, Watchlist
from app.db.session import session_scope
from app.market_data.market_hours import is_market_open
from app.market_data.yahoo_jp import Candle, YahooFetchError, fetch_latest_price
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

# 逐次取得だと1銘柄の遅延/失敗が全体を押し出し、30秒間隔の次回実行と
# 衝突して他のジョブの枠を奪いかねない(prediction_compute.pyと同じ理由)。
CONCURRENT_FETCH_LIMIT = 10


async def _fetch_one(semaphore: asyncio.Semaphore, instrument: Instrument) -> tuple[Instrument, Candle | None]:
    async with semaphore:
        try:
            candle = await fetch_latest_price(instrument.code)
        except YahooFetchError as exc:
            logger.warning("price fetch failed for %s: %s", instrument.code, exc)
            candle = None
        return instrument, candle


async def run() -> None:
    if not is_market_open():
        return

    redis = get_redis()

    async with session_scope() as session:
        result = await session.execute(
            select(Instrument).join(Watchlist, Watchlist.instrument_id == Instrument.id)
        )
        instruments = result.scalars().all()

        semaphore = asyncio.Semaphore(CONCURRENT_FETCH_LIMIT)
        fetch_results = await asyncio.gather(*(_fetch_one(semaphore, i) for i in instruments))

        for instrument, candle in fetch_results:
            if candle is None:
                continue

            stmt = (
                pg_insert(PriceCandle)
                .values(
                    instrument_id=instrument.id,
                    timeframe="1m",
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

            await redis.publish(
                f"prices:{instrument.code}",
                json.dumps({"code": instrument.code, "price": candle.close, "ts": candle.ts.isoformat()}),
            )

        await session.commit()
