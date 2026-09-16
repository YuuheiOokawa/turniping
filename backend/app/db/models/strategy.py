import datetime as dt

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StrategySignalWeight(Base):
    """予想エンジンの各シグナル(移動平均・RSI・MACD・ボリンジャー・センチメント・
    相場全体)の現在の重み。答え合わせ実績に基づき自己学習で定期更新される。
    """

    __tablename__ = "strategy_signal_weights"
    __table_args__ = (UniqueConstraint("signal_name", name="uq_strategy_signal_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_name: Mapped[str] = mapped_column(String(32))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )
