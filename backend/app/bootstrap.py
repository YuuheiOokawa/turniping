from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.market import Instrument, Watchlist
from app.instruments_catalog import DEFAULT_NAMES

__all__ = ["DEFAULT_NAMES", "seed_default_watchlist"]


async def seed_default_watchlist(session: AsyncSession) -> None:
    settings = get_settings()
    for code in settings.default_watchlist_codes:
        name, kind, sector = DEFAULT_NAMES.get(code, (code, "individual", None))

        result = await session.execute(select(Instrument).where(Instrument.code == code))
        instrument = result.scalar_one_or_none()
        if instrument is None:
            instrument = Instrument(code=code, name=name, kind=kind, sector=sector)
            session.add(instrument)
            await session.flush()

        result = await session.execute(select(Watchlist).where(Watchlist.instrument_id == instrument.id))
        if result.scalar_one_or_none() is None:
            session.add(Watchlist(instrument_id=instrument.id))

    await session.commit()
