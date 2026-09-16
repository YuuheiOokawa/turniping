import inspect

from app.worker.main import build_scheduler


def test_all_jobs_are_real_coroutine_functions():
    """APScheduler's AsyncIOExecutor only awaits a job if
    inspect.iscoroutinefunction(job.func) is True. A lambda that merely
    *returns* a coroutine object fails that check silently: the executor
    runs it in a worker thread, the returned coroutine is never awaited,
    and the job logs "executed successfully" while doing nothing.
    """
    scheduler = build_scheduler()
    jobs = scheduler.get_jobs()
    assert len(jobs) == 7

    for job in jobs:
        assert inspect.iscoroutinefunction(job.func), (
            f"job '{job.id}' is not a coroutine function and will never actually run"
        )
