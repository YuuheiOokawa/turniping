import pytest

from app.db.models.market import Instrument
from app.services import paper_trading


async def _make_instrument(session) -> Instrument:
    instrument = Instrument(code="7203.T", name="トヨタ自動車", kind="individual")
    session.add(instrument)
    await session.flush()
    return instrument


async def test_buy_reduces_cash_and_creates_position(session):
    instrument = await _make_instrument(session)
    account = await paper_trading.get_or_create_account(session, kind="manual")
    order = await paper_trading.place_order(
        session, account_id=account.id, instrument_id=instrument.id, side="buy", quantity=10, fill_price=1000.0
    )
    await session.commit()

    position = await paper_trading.get_position(session, account.id, instrument.id)

    assert order.side == "buy"
    assert position is not None
    assert position.quantity == 10
    assert account.cash_jpy == pytest.approx(1_000_000 - 10_000)


async def test_buy_insufficient_funds_raises(session):
    instrument = await _make_instrument(session)
    account = await paper_trading.get_or_create_account(session, kind="manual")
    with pytest.raises(paper_trading.InsufficientFundsError):
        await paper_trading.place_order(
            session, account_id=account.id, instrument_id=instrument.id, side="buy", quantity=100_000,
            fill_price=1000.0,
        )


async def test_sell_without_position_raises(session):
    instrument = await _make_instrument(session)
    account = await paper_trading.get_or_create_account(session, kind="manual")
    with pytest.raises(paper_trading.InsufficientSharesError):
        await paper_trading.place_order(
            session, account_id=account.id, instrument_id=instrument.id, side="sell", quantity=1,
            fill_price=1000.0,
        )


async def test_buy_then_sell_returns_cash(session):
    instrument = await _make_instrument(session)
    account = await paper_trading.get_or_create_account(session, kind="manual")
    await paper_trading.place_order(
        session, account_id=account.id, instrument_id=instrument.id, side="buy", quantity=10, fill_price=1000.0
    )
    await paper_trading.place_order(
        session, account_id=account.id, instrument_id=instrument.id, side="sell", quantity=10, fill_price=1200.0
    )
    await session.commit()

    position = await paper_trading.get_position(session, account.id, instrument.id)

    assert position.quantity == 0
    assert account.cash_jpy == pytest.approx(1_000_000 - 10_000 + 12_000)


async def test_manual_and_ai_accounts_are_separate_with_different_starting_cash(session):
    manual = await paper_trading.get_or_create_account(session, kind="manual")
    ai = await paper_trading.get_or_create_account(session, kind="ai")

    assert manual.id != ai.id
    assert manual.cash_jpy == pytest.approx(1_000_000)
    assert ai.cash_jpy == pytest.approx(50_000)
