from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.market import Instrument, PriceCandle
from app.db.models.paper import PaperAccount, PaperOrder, PaperPosition, PaperValuationSnapshot
from app.market_data.yahoo_jp import YahooFetchError, fetch_latest_price

settings = get_settings()

STARTING_CASH_BY_KIND = {
    "manual": settings.paper_starting_cash_jpy,
    "ai": settings.ai_trader_starting_cash_jpy,
}


class InsufficientFundsError(RuntimeError):
    pass


class InsufficientSharesError(RuntimeError):
    pass


async def get_or_create_account(session: AsyncSession, kind: str = "manual") -> PaperAccount:
    result = await session.execute(select(PaperAccount).where(PaperAccount.kind == kind))
    account = result.scalar_one_or_none()
    if account is None:
        starting_cash = STARTING_CASH_BY_KIND.get(kind, settings.paper_starting_cash_jpy)
        account = PaperAccount(kind=kind, cash_jpy=starting_cash)
        session.add(account)
        await session.flush()
    return account


async def get_position(session: AsyncSession, account_id: int, instrument_id: int) -> PaperPosition | None:
    result = await session.execute(
        select(PaperPosition).where(
            PaperPosition.account_id == account_id, PaperPosition.instrument_id == instrument_id
        )
    )
    return result.scalar_one_or_none()


async def get_current_price(session: AsyncSession, instrument: Instrument) -> float:
    """直近の保存済み価格を使い、無ければYahoo Financeから実際の現在値を取得する。"""
    result = await session.execute(
        select(PriceCandle.close)
        .where(PriceCandle.instrument_id == instrument.id)
        .order_by(PriceCandle.ts.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return float(row)

    try:
        candle = await fetch_latest_price(instrument.code)
    except YahooFetchError as exc:
        raise RuntimeError(f"現在値を取得できませんでした: {exc}") from exc
    if candle is None:
        raise RuntimeError("現在値を取得できませんでした")
    return candle.close


async def place_order(
    session: AsyncSession,
    *,
    account_id: int,
    instrument_id: int,
    side: str,
    quantity: int,
    fill_price: float,
    reason: str | None = None,
    prediction_id: int | None = None,
) -> PaperOrder:
    result = await session.execute(select(PaperAccount).where(PaperAccount.id == account_id))
    account = result.scalar_one()
    position = await get_position(session, account.id, instrument_id)

    cost = fill_price * quantity

    if side == "buy":
        if account.cash_jpy < cost:
            raise InsufficientFundsError("現金残高が不足しています")
        account.cash_jpy -= cost
        if position is None:
            position = PaperPosition(
                account_id=account.id, instrument_id=instrument_id, quantity=quantity, avg_price=fill_price
            )
            session.add(position)
        else:
            new_qty = position.quantity + quantity
            position.avg_price = (
                position.avg_price * position.quantity + fill_price * quantity
            ) / new_qty
            position.quantity = new_qty
    elif side == "sell":
        if position is None or position.quantity < quantity:
            raise InsufficientSharesError("保有数量が不足しています")
        position.quantity -= quantity
        account.cash_jpy += cost
    else:
        raise ValueError(f"unknown side: {side}")

    order = PaperOrder(
        account_id=account.id,
        instrument_id=instrument_id,
        side=side,
        quantity=quantity,
        fill_price=fill_price,
        reason=reason,
        prediction_id=prediction_id,
    )
    session.add(order)
    await session.flush()
    return order


async def compute_portfolio_value(session: AsyncSession, account: PaperAccount) -> tuple[float, float]:
    """(保有株の評価額, 総資産(現金+評価額)) を実際の現在値で計算する。"""
    result = await session.execute(
        select(PaperPosition, Instrument)
        .join(Instrument, Instrument.id == PaperPosition.instrument_id)
        .where(PaperPosition.account_id == account.id, PaperPosition.quantity > 0)
    )
    holdings_value = 0.0
    for position, instrument in result.all():
        try:
            price = await get_current_price(session, instrument)
        except RuntimeError:
            price = position.avg_price  # 取得できない場合は簿価で代用
        holdings_value += price * position.quantity

    total_value = account.cash_jpy + holdings_value
    return holdings_value, total_value


async def record_valuation_snapshot(session: AsyncSession, account: PaperAccount) -> PaperValuationSnapshot:
    holdings_value, total_value = await compute_portfolio_value(session, account)
    snapshot = PaperValuationSnapshot(
        account_id=account.id,
        cash_jpy=account.cash_jpy,
        holdings_value_jpy=holdings_value,
        total_value_jpy=total_value,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot
