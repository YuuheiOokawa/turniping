from app.db.session import session_scope
from app.services.outcome_tracker import evaluate_due_predictions


async def run() -> None:
    async with session_scope() as session:
        await evaluate_due_predictions(session)
        await session.commit()
