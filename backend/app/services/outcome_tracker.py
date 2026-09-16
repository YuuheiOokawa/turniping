import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.market import PriceCandle
from app.db.models.prediction import Prediction, PredictionOutcome


async def _price_after(session: AsyncSession, instrument_id: int, after: dt.datetime) -> float | None:
    """予想が作られた時刻より後の実際の値動きを反映した価格だけを返す。

    単に最新のPriceCandleを使うと、市場が閉まっている間は前日終値のまま
    ずっと変化しないため、その"値動きゼロ"を実際の下落予想と照合すると
    機械的に不正解扱いになってしまう(実測: 評価済み430件中373件が
    このケースで、的中率を大きく歪めていた)。予想時刻より後に記録された
    価格が無ければ、まだ答え合わせできる材料が無いとして評価を保留する。
    """
    result = await session.execute(
        select(PriceCandle.close)
        .where(PriceCandle.instrument_id == instrument_id, PriceCandle.ts > after)
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

        actual_price = await _price_after(session, prediction.instrument_id, prediction.created_at)
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
