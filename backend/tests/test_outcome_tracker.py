import datetime as dt

from sqlalchemy import select

from app.db.models.market import Instrument, PriceCandle
from app.db.models.prediction import Prediction, PredictionOutcome
from app.services.outcome_tracker import evaluate_due_predictions


async def _make_instrument(session) -> Instrument:
    instrument = Instrument(code="^N225", name="日経平均株価", kind="index")
    session.add(instrument)
    await session.flush()
    return instrument


async def test_correct_up_prediction_is_marked_correct(session):
    instrument = await _make_instrument(session)
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=120)
    prediction = Prediction(
        instrument_id=instrument.id,
        created_at=past,
        horizon_minutes=60,
        direction="up",
        confidence=80,
        technical_score=70,
        sentiment_score=0.2,
        reference_price=1000.0,
        reasons=["test"],
    )
    session.add(prediction)
    await session.flush()

    session.add(
        PriceCandle(
            instrument_id=instrument.id,
            timeframe="1m",
            ts=dt.datetime.now(dt.timezone.utc),
            open=1050,
            high=1060,
            low=1040,
            close=1050.0,
            volume=100,
        )
    )
    await session.flush()

    evaluated = await evaluate_due_predictions(session)
    await session.commit()

    assert evaluated == 1

    result = await session.execute(
        select(PredictionOutcome).where(PredictionOutcome.prediction_id == prediction.id)
    )
    outcome = result.scalar_one()
    assert outcome.correct is True


async def test_stale_price_from_before_the_prediction_does_not_evaluate_it(session):
    """市場が閉まったままだと最新PriceCandleが予想作成時点より前(=値動きゼロ)
    のことがある。これを答え合わせに使うと、下落予想は機械的に「不正解」、
    上昇予想は機械的に「正解」になってしまう(実測: 評価済み430件中373件が
    このケースで的中率を大きく歪めていた)。予想より後の価格が無い間は
    保留され続けることを確認する。
    """
    instrument = await _make_instrument(session)
    stale_candle_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=5)
    past = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=120)

    session.add(
        PriceCandle(
            instrument_id=instrument.id,
            timeframe="1m",
            ts=stale_candle_time,  # 予想作成(past)より前の価格
            open=1000,
            high=1000,
            low=1000,
            close=1000.0,
            volume=100,
        )
    )
    await session.flush()

    prediction = Prediction(
        instrument_id=instrument.id,
        created_at=past,
        horizon_minutes=60,
        direction="down",
        confidence=80,
        technical_score=30,
        sentiment_score=0.0,
        reference_price=1000.0,
        reasons=["test"],
    )
    session.add(prediction)
    await session.flush()

    evaluated = await evaluate_due_predictions(session)
    assert evaluated == 0

    result = await session.execute(
        select(PredictionOutcome).where(PredictionOutcome.prediction_id == prediction.id)
    )
    assert result.scalar_one_or_none() is None


async def test_prediction_not_yet_due_is_skipped(session):
    instrument = await _make_instrument(session)
    prediction = Prediction(
        instrument_id=instrument.id,
        created_at=dt.datetime.now(dt.timezone.utc),
        horizon_minutes=60,
        direction="up",
        confidence=80,
        technical_score=70,
        sentiment_score=0.0,
        reference_price=1000.0,
        reasons=["test"],
    )
    session.add(prediction)
    await session.flush()

    evaluated = await evaluate_due_predictions(session)
    assert evaluated == 0
