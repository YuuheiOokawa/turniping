import datetime as dt

from sqlalchemy import select

from app.db.models.market import Instrument, PriceCandle, Watchlist
from app.db.models.prediction import Prediction
from app.services import auto_trader, paper_trading


async def _make_watched_instrument(session, code: str, price: float) -> Instrument:
    instrument = Instrument(code=code, name=f"テスト{code}", kind="individual")
    session.add(instrument)
    await session.flush()
    session.add(Watchlist(instrument_id=instrument.id))
    session.add(
        PriceCandle(
            instrument_id=instrument.id,
            timeframe="1d",
            ts=dt.datetime.now(dt.timezone.utc),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=100,
        )
    )
    await session.flush()
    return instrument


async def _make_prediction(session, instrument_id: int, direction: str, confidence: float) -> Prediction:
    prediction = Prediction(
        instrument_id=instrument_id,
        horizon_minutes=60,
        direction=direction,
        confidence=confidence,
        technical_score=75 if direction == "up" else 25,
        sentiment_score=0.0,
        reference_price=1000.0,
        reasons=["テスト根拠"],
    )
    session.add(prediction)
    await session.flush()
    return prediction


async def test_buys_on_strong_up_prediction_within_budget(session):
    instrument = await _make_watched_instrument(session, "1111.T", price=1000.0)
    await _make_prediction(session, instrument.id, direction="up", confidence=80)

    orders = await auto_trader.run_auto_trades(session)
    await session.commit()

    assert len(orders) == 1
    assert orders[0].side == "buy"
    # auto_trader_max_position_jpy(既定1万円) / 1000円 = 10株
    assert orders[0].quantity == 10
    assert orders[0].reason is not None


async def test_does_not_buy_below_confidence_threshold(session):
    instrument = await _make_watched_instrument(session, "2222.T", price=1000.0)
    await _make_prediction(session, instrument.id, direction="up", confidence=20)

    orders = await auto_trader.run_auto_trades(session)

    assert orders == []


async def test_does_not_buy_when_already_holding(session):
    instrument = await _make_watched_instrument(session, "3333.T", price=1000.0)
    await _make_prediction(session, instrument.id, direction="up", confidence=80)

    account = await paper_trading.get_or_create_account(session, kind="ai")
    await paper_trading.place_order(
        session, account_id=account.id, instrument_id=instrument.id, side="buy", quantity=5, fill_price=1000.0
    )

    orders = await auto_trader.run_auto_trades(session)

    assert orders == []


async def test_sells_entire_position_on_strong_down_prediction(session):
    instrument = await _make_watched_instrument(session, "4444.T", price=1000.0)
    account = await paper_trading.get_or_create_account(session, kind="ai")
    await paper_trading.place_order(
        session, account_id=account.id, instrument_id=instrument.id, side="buy", quantity=5, fill_price=900.0
    )
    await _make_prediction(session, instrument.id, direction="down", confidence=80)

    orders = await auto_trader.run_auto_trades(session)
    await session.commit()

    assert len(orders) == 1
    assert orders[0].side == "sell"
    assert orders[0].quantity == 5

    position = await paper_trading.get_position(session, account.id, instrument.id)
    assert position.quantity == 0


async def test_skips_instrument_with_no_prediction(session):
    await _make_watched_instrument(session, "5555.T", price=1000.0)

    orders = await auto_trader.run_auto_trades(session)

    assert orders == []


async def test_valuation_snapshot_reflects_cash_and_holdings(session):
    instrument = await _make_watched_instrument(session, "6666.T", price=1000.0)
    account = await paper_trading.get_or_create_account(session, kind="ai")
    await paper_trading.place_order(
        session, account_id=account.id, instrument_id=instrument.id, side="buy", quantity=10, fill_price=1000.0
    )
    await session.commit()

    snapshot = await paper_trading.record_valuation_snapshot(session, account)
    await session.commit()

    # 50,000開始 - 10,000(10株x1000円) = 40,000現金 + 10,000評価額 = 50,000総資産
    assert snapshot.cash_jpy == 40_000
    assert snapshot.holdings_value_jpy == 10_000
    assert snapshot.total_value_jpy == 50_000
