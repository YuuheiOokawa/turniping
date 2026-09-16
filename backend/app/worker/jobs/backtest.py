import logging

from app.db.session import session_scope
from app.services import backtest

logger = logging.getLogger(__name__)


async def run() -> None:
    async with session_scope() as session:
        summary = await backtest.run_backtest(session)
        await session.commit()
    logger.info(
        "backtest: %d instruments processed, %d new samples generated",
        summary["instruments_processed"], summary["samples_generated"],
    )
