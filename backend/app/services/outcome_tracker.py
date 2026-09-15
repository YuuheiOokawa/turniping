import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.market import PriceCandle
from app.db.models.prediction import Prediction, PredictionOutcome


async def _latest_price(session: AsyncSession, instrument_id: int) -> float | None:
    result = await session.execute(
        select(PriceCandle.close)
        .where(PriceCandle.instrument_id == instrument_id)
        .order_by(PriceCandle.ts.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


async def evaluate_due_predictions(session: AsyncSession) -> int:
    """horizonが経過し未評価の予想を実際の値動きと照合する。評価件数を返す。"""
    now = dt.datetime.now(dt.timezone.utc)

    result = await session.execute(
        select(Prediction).outerjoin(PredictionOutcome).where(PredictionOutcome.id.is_(None))
    )
    pending = result.scalars().all()

    evaluated = 0
    for prediction in pending:
        due_at = prediction.created_at + dt.timedelta(minutes=prediction.horizon_minutes)
        if due_at > now:
            continue

        actual_price = await _latest_price(session, prediction.instrument_id)
        if actual_price is None:
            continue

        change_pct = (actual_price - prediction.reference_price) / prediction.reference_price * 100
        actual_direction = "up" if change_pct >= 0 else "down"
        correct = actual_direction == prediction.direction

        session.add(
            PredictionOutcome(
                prediction_id=prediction.id,
                evaluated_at=now,
                actual_price=actual_price,
                actual_change_pct=change_pct,
                correct=correct,
            )
        )
        evaluated += 1

    if evaluated:
        await session.flush()
    return evaluated
