from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.market import Instrument, Watchlist

# code -> (name, kind, sector)
DEFAULT_NAMES: dict[str, tuple[str, str, str | None]] = {
    "^N225": ("日経平均株価", "index", None),
    "1306.T": ("NEXT FUNDS TOPIX連動型上場投信", "index", None),
    # 自動車
    "7203.T": ("トヨタ自動車", "individual", "自動車"),
    "7267.T": ("本田技研工業", "individual", "自動車"),
    "7201.T": ("日産自動車", "individual", "自動車"),
    # 電機・精密
    "6758.T": ("ソニーグループ", "individual", "電機・精密"),
    "6501.T": ("日立製作所", "individual", "電機・精密"),
    "6702.T": ("富士通", "individual", "電機・精密"),
    "6861.T": ("キーエンス", "individual", "電機・精密"),
    # 通信・IT
    "9984.T": ("ソフトバンクグループ", "individual", "通信・IT"),
    "9432.T": ("日本電信電話", "individual", "通信・IT"),
    "9433.T": ("KDDI", "individual", "通信・IT"),
    "6098.T": ("リクルートホールディングス", "individual", "通信・IT"),
    # 銀行
    "8306.T": ("三菱UFJフィナンシャル・グループ", "individual", "銀行"),
    "8316.T": ("三井住友フィナンシャルグループ", "individual", "銀行"),
    "8411.T": ("みずほフィナンシャルグループ", "individual", "銀行"),
    "8604.T": ("野村ホールディングス", "individual", "証券・金融"),
    # 商社
    "8058.T": ("三菱商事", "individual", "商社"),
    "8031.T": ("三井物産", "individual", "商社"),
    "8001.T": ("伊藤忠商事", "individual", "商社"),
    # 小売
    "9983.T": ("ファーストリテイリング", "individual", "小売"),
    "3382.T": ("セブン&アイ・ホールディングス", "individual", "小売"),
    # 医薬品
    "4502.T": ("武田薬品工業", "individual", "医薬品"),
    "4503.T": ("アステラス製薬", "individual", "医薬品"),
    # 素材
    "5401.T": ("日本製鉄", "individual", "鉄鋼・素材"),
    # エンタメ
    "7974.T": ("任天堂", "individual", "エンタメ"),
}


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
