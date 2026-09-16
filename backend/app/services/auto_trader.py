import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.market import Instrument, Watchlist
from app.db.models.paper import PaperOrder
from app.db.models.prediction import Prediction
from app.services import paper_trading

logger = logging.getLogger(__name__)
settings = get_settings()


async def _latest_prediction(session: AsyncSession, instrument_id: int) -> Prediction | None:
    result = await session.execute(
        select(Prediction)
        .where(Prediction.instrument_id == instrument_id)
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _reason(prediction: Prediction) -> str:
    reasons = "、".join(prediction.reasons) if prediction.reasons else "特記事項なし"
    return f"予想: {prediction.direction}(確信度{prediction.confidence:.0f}%)。根拠: {reasons}"


async def run_auto_trades(session: AsyncSession) -> list[PaperOrder]:
    """最新の予想に基づき、ルールベースでAI口座(kind='ai')の売買を実行する。

    ルール(シンプルなトレンドフォロー方式。将来ここを差し替えれば戦略を変えられる):
    - 上昇予想かつ確信度が買い閾値以上、かつ未保有 → 1銘柄あたり上限額(既定1万円)まで買う
    - 下落予想かつ確信度が売り閾値以上、かつ保有中 → 全数売却
    - 予想が無い/閾値未満/既にポジションがある場合は何もしない(ナンピン買い増しはしない)
    """
    account = await paper_trading.get_or_create_account(session, kind="ai")

    result = await session.execute(
        select(Instrument).join(Watchlist, Watchlist.instrument_id == Instrument.id)
    )
    instruments = result.scalars().all()

    orders: list[PaperOrder] = []

    for instrument in instruments:
        prediction = await _latest_prediction(session, instrument.id)
        if prediction is None:
            continue

        position = await paper_trading.get_position(session, account.id, instrument.id)
        holding = position.quantity if position else 0

        try:
            price = await paper_trading.get_current_price(session, instrument)
        except RuntimeError as exc:
            logger.warning("price fetch failed for %s: %s", instrument.code, exc)
            continue

        if (
            holding == 0
            and prediction.direction == "up"
            and prediction.confidence >= settings.auto_trader_buy_confidence_threshold
        ):
            budget = min(account.cash_jpy, settings.auto_trader_max_position_jpy)
            quantity = int(budget // price)
            if quantity < 1:
                continue
            try:
                order = await paper_trading.place_order(
                    session,
                    account_id=account.id,
                    instrument_id=instrument.id,
                    side="buy",
                    quantity=quantity,
                    fill_price=price,
                    reason=_reason(prediction),
                    prediction_id=prediction.id,
                )
            except paper_trading.InsufficientFundsError:
                continue
            orders.append(order)

        elif (
            holding > 0
            and prediction.direction == "down"
            and prediction.confidence >= settings.auto_trader_sell_confidence_threshold
        ):
            try:
                order = await paper_trading.place_order(
                    session,
                    account_id=account.id,
                    instrument_id=instrument.id,
                    side="sell",
                    quantity=holding,
                    fill_price=price,
                    reason=_reason(prediction),
                    prediction_id=prediction.id,
                )
            except paper_trading.InsufficientSharesError:
                continue
            orders.append(order)

    return orders
