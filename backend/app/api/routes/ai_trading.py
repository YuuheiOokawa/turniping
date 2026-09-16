from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_auth
from app.config import get_settings
from app.db.models.market import Instrument
from app.db.models.paper import PaperOrder, PaperPosition, PaperValuationSnapshot
from app.db.session import get_session
from app.services import paper_trading

router = APIRouter(prefix="/ai-trading", tags=["ai-trading"], dependencies=[Depends(require_auth)])

settings = get_settings()


@router.get("/account")
async def get_account(session: AsyncSession = Depends(get_session)) -> dict:
    account = await paper_trading.get_or_create_account(session, kind="ai")
    await session.commit()

    result = await session.execute(
        select(PaperPosition, Instrument)
        .join(Instrument, Instrument.id == PaperPosition.instrument_id)
        .where(PaperPosition.account_id == account.id, PaperPosition.quantity > 0)
    )

    positions = []
    holdings_value = 0.0
    for position, instrument in result.all():
        try:
            current_price = await paper_trading.get_current_price(session, instrument)
        except RuntimeError:
            current_price = position.avg_price
        market_value = current_price * position.quantity
        cost_basis = position.avg_price * position.quantity
        holdings_value += market_value
        positions.append(
            {
                "code": instrument.code,
                "name": instrument.name,
                "quantity": position.quantity,
                "avg_price": position.avg_price,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl_jpy": market_value - cost_basis,
                "unrealized_pnl_pct": ((current_price / position.avg_price) - 1) * 100
                if position.avg_price
                else 0.0,
            }
        )

    total_value = account.cash_jpy + holdings_value
    return {
        "cash_jpy": account.cash_jpy,
        "holdings_value_jpy": holdings_value,
        "total_value_jpy": total_value,
        "positions": positions,
    }


@router.get("/performance")
async def get_performance(session: AsyncSession = Depends(get_session)) -> dict:
    account = await paper_trading.get_or_create_account(session, kind="ai")
    holdings_value, total_value = await paper_trading.compute_portfolio_value(session, account)
    await session.commit()

    starting_cash = settings.ai_trader_starting_cash_jpy
    pnl_jpy = total_value - starting_cash
    pnl_pct = (pnl_jpy / starting_cash) * 100 if starting_cash else 0.0

    return {
        "starting_cash_jpy": starting_cash,
        "cash_jpy": account.cash_jpy,
        "holdings_value_jpy": holdings_value,
        "total_value_jpy": total_value,
        "pnl_jpy": pnl_jpy,
        "pnl_pct": pnl_pct,
    }


@router.get("/orders")
async def list_orders(limit: int = 100, session: AsyncSession = Depends(get_session)) -> list[dict]:
    account = await paper_trading.get_or_create_account(session, kind="ai")
    await session.commit()

    result = await session.execute(
        select(PaperOrder, Instrument)
        .join(Instrument, Instrument.id == PaperOrder.instrument_id)
        .where(PaperOrder.account_id == account.id)
        .order_by(PaperOrder.filled_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": order.id,
            "code": instrument.code,
            "name": instrument.name,
            "side": order.side,
            "quantity": order.quantity,
            "fill_price": order.fill_price,
            "filled_at": order.filled_at.isoformat(),
            "reason": order.reason,
        }
        for order, instrument in result.all()
    ]


@router.get("/history")
async def get_history(limit: int = 500, session: AsyncSession = Depends(get_session)) -> list[dict]:
    account = await paper_trading.get_or_create_account(session, kind="ai")
    await session.commit()

    result = await session.execute(
        select(PaperValuationSnapshot)
        .where(PaperValuationSnapshot.account_id == account.id)
        .order_by(PaperValuationSnapshot.ts.desc())
        .limit(limit)
    )
    snapshots = list(reversed(result.scalars().all()))
    return [
        {
            "ts": s.ts.isoformat(),
            "cash_jpy": s.cash_jpy,
            "holdings_value_jpy": s.holdings_value_jpy,
            "total_value_jpy": s.total_value_jpy,
        }
        for s in snapshots
    ]
