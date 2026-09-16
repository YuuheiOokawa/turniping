import datetime as dt

from sqlalchemy import select

from app.db.models.market import Instrument
from app.db.models.prediction import Prediction, PredictionOutcome
from app.db.models.strategy import StrategySignalWeight
from app.services import strategy_learning


async def _make_instrument(session) -> Instrument:
    instrument = Instrument(code="7203.T", name="トヨタ自動車", kind="individual")
    session.add(instrument)
    await session.flush()
    return instrument


async def _add_evaluated_prediction(
    session, instrument_id: int, *, signal_contributions: dict, actual_change_pct: float
) -> None:
    prediction = Prediction(
        instrument_id=instrument_id,
        created_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
        horizon_minutes=60,
        direction="up" if actual_change_pct >= 0 else "down",
        confidence=50,
        technical_score=50,
        sentiment_score=0.0,
        reference_price=1000.0,
        reasons=["test"],
        signal_contributions=signal_contributions,
    )
    session.add(prediction)
    await session.flush()
    session.add(
        PredictionOutcome(
            prediction_id=prediction.id,
            evaluated_at=dt.datetime.now(dt.timezone.utc),
            actual_price=1000.0 * (1 + actual_change_pct / 100),
            actual_change_pct=actual_change_pct,
            correct=True,  # unused by recalibrate; only actual_change_pct matters
        )
    )
    await session.flush()


async def test_below_minimum_sample_size_is_skipped(session):
    instrument = await _make_instrument(session)
    for _ in range(5):  # fewer than MIN_SAMPLE_SIZE
        await _add_evaluated_prediction(
            session, instrument.id, signal_contributions={"sma_cross": 5}, actual_change_pct=1.0
        )

    summaries = await strategy_learning.recalibrate(session)
    assert summaries == []


async def test_consistently_correct_signal_gains_weight(session):
    instrument = await _make_instrument(session)
    for _ in range(strategy_learning.MIN_SAMPLE_SIZE):
        # sma_cross is bullish (positive) and the stock always actually goes up
        await _add_evaluated_prediction(
            session, instrument.id, signal_contributions={"sma_cross": 8}, actual_change_pct=1.0
        )

    summaries = await strategy_learning.recalibrate(session)
    await session.commit()

    assert len(summaries) == 1
    assert summaries[0]["signal_name"] == "sma_cross"
    assert summaries[0]["accuracy"] == 1.0
    assert summaries[0]["weight"] > 1.0

    result = await session.execute(
        select(StrategySignalWeight).where(StrategySignalWeight.signal_name == "sma_cross")
    )
    row = result.scalar_one()
    assert row.weight == summaries[0]["weight"]
    assert row.sample_size == strategy_learning.MIN_SAMPLE_SIZE


async def test_consistently_wrong_signal_loses_weight(session):
    instrument = await _make_instrument(session)
    for _ in range(strategy_learning.MIN_SAMPLE_SIZE):
        # sma_cross says bullish but the stock always actually falls
        await _add_evaluated_prediction(
            session, instrument.id, signal_contributions={"sma_cross": 8}, actual_change_pct=-1.0
        )

    summaries = await strategy_learning.recalibrate(session)

    assert summaries[0]["accuracy"] == 0.0
    assert summaries[0]["weight"] < 1.0


async def test_weight_is_clamped_to_bounds(session):
    instrument = await _make_instrument(session)
    # Pre-seed a weight already at the maximum so one more good streak can't push it further.
    session.add(StrategySignalWeight(signal_name="rsi", weight=strategy_learning.MAX_WEIGHT))
    await session.flush()

    for _ in range(strategy_learning.MIN_SAMPLE_SIZE):
        await _add_evaluated_prediction(
            session, instrument.id, signal_contributions={"rsi": 8}, actual_change_pct=1.0
        )

    summaries = await strategy_learning.recalibrate(session)

    assert summaries[0]["weight"] == strategy_learning.MAX_WEIGHT


async def test_zero_contribution_signals_are_ignored(session):
    instrument = await _make_instrument(session)
    for _ in range(strategy_learning.MIN_SAMPLE_SIZE):
        # macd has no opinion (0) this time; only sma_cross should be scored
        await _add_evaluated_prediction(
            session,
            instrument.id,
            signal_contributions={"sma_cross": 8, "macd": 0},
            actual_change_pct=1.0,
        )

    summaries = await strategy_learning.recalibrate(session)
    signal_names = {s["signal_name"] for s in summaries}
    assert signal_names == {"sma_cross"}
