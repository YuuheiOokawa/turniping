import datetime as dt

from sqlalchemy import Date, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BacktestSignalSample(Base):
    """過去の日足データから機械的に再構成した、各シグナルの生の方向値と
    翌営業日の実際の値動き。答え合わせ(ライブ)が溜まるのを待たずに、
    数年分のデータで各シグナルの的中率を大きなサンプル数で検証するために使う。

    ライブの predictions テーブルとは別管理とし、ダッシュボードや個別銘柄の
    予想履歴には一切表示されない(過去に遡って生成した学習専用データのため)。
    """

    __tablename__ = "backtest_signal_samples"
    __table_args__ = (UniqueConstraint("instrument_id", "as_of_date", name="uq_backtest_sample"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[dt.date] = mapped_column(Date, index=True)
    # signal_name -> 生の(重み適用前の)方向シグナル値。predictions.signal_contributionsと同じ形式。
    signal_contributions: Mapped[dict] = mapped_column(JSON)
    actual_direction: Mapped[str] = mapped_column(String(8))  # "up" | "down" (翌営業日の終値ベース)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )
