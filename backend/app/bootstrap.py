from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.market import Instrument, Watchlist

DEFAULT_NAMES: dict[str, tuple[str, str]] = {
    "^N225": ("日経平均株価", "index"),
    "1306.T": ("NEXT FUNDS TOPIX連動型上場投信", "index"),
    "7203.T": ("トヨタ自動車", "individual"),
    "6758.T": ("ソニーグループ", "individual"),
    "9984.T": ("ソフトバンクグループ", "individual"),
}


async def seed_default_watchlist(session: AsyncSession) -> None:
    settings = get_settings()
    for code in settings.default_watchlist_codes:
        name, kind = DEFAULT_NAMES.get(code, (code, "individual"))

        result = await session.execute(select(Instrument).where(Instrument.code == code))
        instrument = result.scalar_one_or_none()
        if instrument is None:
            instrument = Instrument(code=code, name=name, kind=kind)
            session.add(instrument)
            await session.flush()

        result = await session.execute(select(Watchlist).where(Watchlist.instrument_id == instrument.id))
        if result.scalar_one_or_none() is None:
            session.add(Watchlist(instrument_id=instrument.id))

    await session.commit()
