import logging

from app.db.session import session_scope
from app.services import strategy_learning

logger = logging.getLogger(__name__)


async def run() -> None:
    async with session_scope() as session:
        summaries = await strategy_learning.recalibrate(session)
        await session.commit()

    for s in summaries:
        logger.info(
            "signal '%s': weight=%.2f accuracy=%.1f%% (n=%d)",
            s["signal_name"], s["weight"], s["accuracy"] * 100, s["sample_size"],
        )
