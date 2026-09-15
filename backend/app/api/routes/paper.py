from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_auth
from app.db.models.market import Instrument, PriceCandle
from app.db.models.paper import PaperOrder, PaperPosition
from app.db.session import get_session
from app.market_data.yahoo_jp import YahooFetchError, fetch_latest_price
from app.services import paper_trading

router = APIRouter(prefix="/paper", tags=["paper"], dependencies=[Depends(require_auth)])


class PlaceOrderRequest(BaseModel):
    code: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: int = Field(gt=0)


async def _current_price(session: AsyncSession, instrument: Instrument) -> float:
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
        raise HTTPException(status_code=502, detail=f"価格取得に失敗しました: {exc}") from exc
    if candle is None:
        raise HTTPException(status_code=502, detail="現在値を取得できませんでした")
    return candle.close


@router.get("/account")
async def get_account(session: AsyncSession = Depends(get_session)) -> dict:
    account = await paper_trading.get_or_create_account(session)
    await session.commit()

    result = await session.execute(
        select(PaperPosition, Instrument)
        .join(Instrument, Instrument.id == PaperPosition.instrument_id)
        .where(PaperPosition.account_id == account.id, PaperPosition.quantity > 0)
    )
    positions = [
        {
            "code": instrument.code,
            "name": instrument.name,
            "quantity": position.quantity,
            "avg_price": position.avg_price,
        }
        for position, instrument in result.all()
    ]
    return {"cash_jpy": account.cash_jpy, "positions": positions}


@router.get("/orders")
async def list_orders(limit: int = 50, session: AsyncSession = Depends(get_session)) -> list[dict]:
    account = await paper_trading.get_or_create_account(session)
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
            "side": order.side,
            "quantity": order.quantity,
            "fill_price": order.fill_price,
            "filled_at": order.filled_at.isoformat(),
        }
        for order, instrument in result.all()
    ]


@router.post("/orders", status_code=201)
async def place_order(payload: PlaceOrderRequest, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(select(Instrument).where(Instrument.code == payload.code))
    instrument = result.scalar_one_or_none()
    if instrument is None:
        raise HTTPException(status_code=404, detail="instrument not found")

    price = await _current_price(session, instrument)

    try:
        order = await paper_trading.place_order(
            session,
            instrument_id=instrument.id,
            side=payload.side,
            quantity=payload.quantity,
            fill_price=price,
        )
    except (paper_trading.InsufficientFundsError, paper_trading.InsufficientSharesError) as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await session.commit()
    return {
        "id": order.id,
        "code": instrument.code,
        "side": order.side,
        "quantity": order.quantity,
        "fill_price": order.fill_price,
        "filled_at": order.filled_at.isoformat(),
    }
