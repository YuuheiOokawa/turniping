from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_auth
from app.db.models.market import Instrument
from app.db.models.prediction import Prediction, PredictionOutcome
from app.db.session import get_session

router = APIRouter(prefix="/predictions", tags=["predictions"], dependencies=[Depends(require_auth)])


def _serialize(prediction: Prediction) -> dict:
    return {
        "id": prediction.id,
        "created_at": prediction.created_at.isoformat(),
        "horizon_minutes": prediction.horizon_minutes,
        "direction": prediction.direction,
        "confidence": prediction.confidence,
        "technical_score": prediction.technical_score,
        "sentiment_score": prediction.sentiment_score,
        "reference_price": prediction.reference_price,
        "reasons": prediction.reasons,
    }


async def _get_instrument(session: AsyncSession, code: str) -> Instrument:
    result = await session.execute(select(Instrument).where(Instrument.code == code))
    instrument = result.scalar_one_or_none()
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")
    return instrument


@router.get("/{code}/latest")
async def latest_prediction(code: str, session: AsyncSession = Depends(get_session)) -> dict | None:
    instrument = await _get_instrument(session, code)
    result = await session.execute(
        select(Prediction)
        .where(Prediction.instrument_id == instrument.id)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    prediction = result.scalar_one_or_none()
    return _serialize(prediction) if prediction else None


@router.get("/{code}/history")
async def prediction_history(
    code: str, limit: int = 50, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    instrument = await _get_instrument(session, code)
    result = await session.execute(
        select(Prediction)
        .where(Prediction.instrument_id == instrument.id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
    )
    return [_serialize(p) for p in result.scalars().all()]


@router.get("/accuracy/overall")
async def accuracy_overall(session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        select(
            func.count(PredictionOutcome.id),
            func.sum(cast(PredictionOutcome.correct, Integer)),
        )
    )
    total, correct_sum = result.one()
    total = total or 0
    correct = int(correct_sum) if correct_sum is not None else 0
    accuracy = (correct / total * 100) if total else None
    return {"total_evaluated": total, "correct": correct, "accuracy_pct": accuracy}


@router.get("/{code}/accuracy")
async def accuracy_for_instrument(code: str, session: AsyncSession = Depends(get_session)) -> dict:
    instrument = await _get_instrument(session, code)
    result = await session.execute(
        select(func.count(PredictionOutcome.id), func.sum(cast(PredictionOutcome.correct, Integer)))
        .join(Prediction, Prediction.id == PredictionOutcome.prediction_id)
        .where(Prediction.instrument_id == instrument.id)
    )
    total, correct_sum = result.one()
    total = total or 0
    correct = int(correct_sum) if correct_sum is not None else 0
    accuracy = (correct / total * 100) if total else None
    return {"code": code, "total_evaluated": total, "correct": correct, "accuracy_pct": accuracy}
