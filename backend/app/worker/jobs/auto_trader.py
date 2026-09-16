from app.db.session import session_scope
from app.market_data.market_hours import is_market_open
from app.services import auto_trader, paper_trading


async def run() -> None:
    if not is_market_open():
        return

    async with session_scope() as session:
        await auto_trader.run_auto_trades(session)
        account = await paper_trading.get_or_create_account(session, kind="ai")
        await paper_trading.record_valuation_snapshot(session, account)
        await session.commit()
