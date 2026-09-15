from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.paper import PaperAccount, PaperOrder, PaperPosition

settings = get_settings()


class InsufficientFundsError(RuntimeError):
    pass


class InsufficientSharesError(RuntimeError):
    pass


async def get_or_create_account(session: AsyncSession) -> PaperAccount:
    result = await session.execute(select(PaperAccount).limit(1))
    account = result.scalar_one_or_none()
    if account is None:
        account = PaperAccount(cash_jpy=settings.paper_starting_cash_jpy)
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


async def place_order(
    session: AsyncSession,
    *,
    instrument_id: int,
    side: str,
    quantity: int,
    fill_price: float,
) -> PaperOrder:
    account = await get_or_create_account(session)
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
    )
    session.add(order)
    await session.flush()
    return order
