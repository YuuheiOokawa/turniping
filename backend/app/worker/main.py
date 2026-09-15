import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.bootstrap import seed_default_watchlist
from app.config import get_settings
from app.db.session import session_scope
from app.worker.jobs import news_ingest, outcome_eval, prediction_compute, price_poll, retention

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("turniping.worker")

settings = get_settings()


async def _run_safely(name: str, coro_fn) -> None:
    try:
        await coro_fn()
    except Exception:
        logger.exception("job %s failed", name)


async def _price_poll_job() -> None:
    await _run_safely("price_poll", price_poll.run)


async def _news_ingest_job() -> None:
    await _run_safely("news_ingest", news_ingest.run)


async def _prediction_compute_job() -> None:
    await _run_safely("prediction_compute", prediction_compute.run)


async def _outcome_eval_job() -> None:
    await _run_safely("outcome_eval", outcome_eval.run)


async def _retention_job() -> None:
    await _run_safely("retention", retention.run)


def build_scheduler() -> AsyncIOScheduler:
    # NOTE: each job below must be a real `async def` function (a coroutine
    # function), not a lambda wrapping one. APScheduler's AsyncIOExecutor
    # decides whether to await a job via `iscoroutinefunction(job.func)` —
    # a lambda that merely *returns* a coroutine object fails that check,
    # so the executor runs it in a worker thread instead, the returned
    # coroutine is never awaited, and the job silently does nothing while
    # still logging "executed successfully".
    scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")

    scheduler.add_job(
        _price_poll_job,
        IntervalTrigger(seconds=settings.price_poll_interval_seconds),
        id="price_poll",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _news_ingest_job,
        IntervalTrigger(minutes=settings.news_ingest_interval_minutes),
        id="news_ingest",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _prediction_compute_job,
        IntervalTrigger(minutes=settings.prediction_interval_minutes),
        id="prediction_compute",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _outcome_eval_job,
        IntervalTrigger(minutes=settings.outcome_eval_interval_minutes),
        id="outcome_eval",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _retention_job,
        IntervalTrigger(hours=24),
        id="retention",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


async def main() -> None:
    async with session_scope() as session:
        await seed_default_watchlist(session)

    scheduler = build_scheduler()
    scheduler.start()
    logger.info("turniping worker started")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
