import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_auth
from app.bootstrap import DEFAULT_NAMES
from app.db.models.market import Instrument, PriceCandle, Watchlist
from app.db.session import get_session
from app.market_data.yahoo_jp import YahooFetchError, fetch_symbol_meta

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(require_auth)])


class AddWatchlistRequest(BaseModel):
    code: str


async def _latest_two_closes(session: AsyncSession, instrument_id: int) -> tuple[float | None, float | None]:
    result = await session.execute(
        select(PriceCandle.close)
        .where(PriceCandle.instrument_id == instrument_id)
        .order_by(PriceCandle.ts.desc())
        .limit(2)
    )
    closes = [float(c) for c in result.scalars().all()]
    latest = closes[0] if len(closes) >= 1 else None
    previous = closes[1] if len(closes) >= 2 else None
    return latest, previous


@router.get("/instruments")
async def list_instruments(session: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await session.execute(
        select(Instrument).join(Watchlist, Watchlist.instrument_id == Instrument.id)
    )
    instruments = result.scalars().all()

    items = []
    for instrument in instruments:
        latest, previous = await _latest_two_closes(session, instrument.id)
        change_pct = None
        if latest is not None and previous:
            change_pct = (latest - previous) / previous * 100
        items.append(
            {
                "code": instrument.code,
                "name": instrument.name,
                "kind": instrument.kind,
                "last_price": latest,
                "change_pct": change_pct,
            }
        )
    return items


@router.post("/watchlist", status_code=201)
async def add_to_watchlist(payload: AddWatchlistRequest, session: AsyncSession = Depends(get_session)) -> dict:
    code = payload.code.strip()
    result = await session.execute(select(Instrument).where(Instrument.code == code))
    instrument = result.scalar_one_or_none()

    if instrument is None:
        name, kind = DEFAULT_NAMES.get(code, (code, "individual"))
        try:
            meta = await fetch_symbol_meta(code)
        except YahooFetchError as exc:
            raise HTTPException(status_code=404, detail=f"銘柄コードが見つかりません: {exc}") from exc
        name = meta.get("longName") or meta.get("shortName") or name
        instrument = Instrument(code=code, name=name, kind=kind)
        session.add(instrument)
        await session.flush()

    result = await session.execute(select(Watchlist).where(Watchlist.instrument_id == instrument.id))
    if result.scalar_one_or_none() is None:
        session.add(Watchlist(instrument_id=instrument.id))

    await session.commit()
    return {"code": instrument.code, "name": instrument.name}


@router.delete("/watchlist/{code}", status_code=204)
async def remove_from_watchlist(code: str, session: AsyncSession = Depends(get_session)) -> None:
    result = await session.execute(select(Instrument).where(Instrument.code == code))
    instrument = result.scalar_one_or_none()
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")

    result = await session.execute(select(Watchlist).where(Watchlist.instrument_id == instrument.id))
    watch = result.scalar_one_or_none()
    if watch is not None:
        await session.delete(watch)
        await session.commit()


@router.get("/instruments/{code}/candles")
async def get_candles(
    code: str,
    timeframe: str = "1d",
    limit: int = 90,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await session.execute(select(Instrument).where(Instrument.code == code))
    instrument = result.scalar_one_or_none()
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")

    result = await session.execute(
        select(PriceCandle)
        .where(PriceCandle.instrument_id == instrument.id, PriceCandle.timeframe == timeframe)
        .order_by(PriceCandle.ts.desc())
        .limit(limit)
    )
    candles = list(reversed(result.scalars().all()))
    return [
        {
            "ts": c.ts.isoformat(),
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": c.volume,
        }
        for c in candles
    ]
