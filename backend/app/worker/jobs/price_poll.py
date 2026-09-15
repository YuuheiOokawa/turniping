import json
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.models.market import Instrument, PriceCandle, Watchlist
from app.db.session import session_scope
from app.market_data.market_hours import is_market_open
from app.market_data.yahoo_jp import YahooFetchError, fetch_latest_price
from app.redis_client import get_redis

logger = logging.getLogger(__name__)


async def run() -> None:
    if not is_market_open():
        return

    redis = get_redis()

    async with session_scope() as session:
        result = await session.execute(
            select(Instrument).join(Watchlist, Watchlist.instrument_id == Instrument.id)
        )
        instruments = result.scalars().all()

        for instrument in instruments:
            try:
                candle = await fetch_latest_price(instrument.code)
            except YahooFetchError as exc:
                logger.warning("price fetch failed for %s: %s", instrument.code, exc)
                continue
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
