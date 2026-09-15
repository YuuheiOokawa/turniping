import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), index=True
    )
    horizon_minutes: Mapped[int] = mapped_column(Integer)
    direction: Mapped[str] = mapped_column(String(8))  # "up" | "down"
    confidence: Mapped[float] = mapped_column(Float)
    technical_score: Mapped[float] = mapped_column(Float)
    sentiment_score: Mapped[float] = mapped_column(Float)
    reference_price: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)

    outcome: Mapped["PredictionOutcome | None"] = relationship(back_populates="prediction", uselist=False)


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), unique=True, index=True
    )
    evaluated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    actual_price: Mapped[float] = mapped_column(Float)
    actual_change_pct: Mapped[float] = mapped_column(Float)
    correct: Mapped[bool] = mapped_column(Boolean)

    prediction: Mapped["Prediction"] = relationship(back_populates="outcome")
