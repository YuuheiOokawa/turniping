import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PaperAccount(Base):
    __tablename__ = "paper_account"
    __table_args__ = (UniqueConstraint("kind", name="uq_paper_account_kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # "manual" = ユーザーが自分で発注する口座, "ai" = AIが予想に基づき自動売買する口座
    kind: Mapped[str] = mapped_column(String(16), default="manual")
    cash_jpy: Mapped[float] = mapped_column(Float)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )


class PaperPosition(Base):
    __tablename__ = "paper_positions"
    __table_args__ = (UniqueConstraint("account_id", "instrument_id", name="uq_paper_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("paper_account.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    avg_price: Mapped[float] = mapped_column(Float, default=0.0)


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("paper_account.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(4))  # "buy" | "sell"
    quantity: Mapped[int] = mapped_column(Integer)
    fill_price: Mapped[float] = mapped_column(Float)
    filled_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc)
    )
    # AI自動売買の場合のみ入る: どの予想に基づき、なぜこの発注をしたか
    prediction_id: Mapped[int | None] = mapped_column(
        ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class PaperValuationSnapshot(Base):
    """AI口座などの評価額を定期的に記録し、資金推移(エクイティカーブ)を見せるための履歴。"""

    __tablename__ = "paper_valuation_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("paper_account.id", ondelete="CASCADE"), index=True)
    ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), index=True, default=lambda: dt.datetime.now(dt.timezone.utc)
    )
    cash_jpy: Mapped[float] = mapped_column(Float)
    holdings_value_jpy: Mapped[float] = mapped_column(Float)
    total_value_jpy: Mapped[float] = mapped_column(Float)
