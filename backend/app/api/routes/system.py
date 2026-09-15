import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_auth
from app.db.session import get_session
from app.market_data.market_hours import is_market_open, next_open, now_jst
from app.redis_client import get_redis
from app.ws.tickets import create_ticket

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    checks = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    healthy = all(v == "ok" for v in checks.values())
    return {"status": "ok" if healthy else "degraded", "checks": checks}


@router.get("/system/status")
async def system_status() -> dict:
    open_now = is_market_open()
    return {
        "now_jst": now_jst().isoformat(),
        "market_open": open_now,
        "next_open_jst": None if open_now else next_open().isoformat(),
    }


@router.post("/ws-ticket", dependencies=[Depends(require_auth)])
async def issue_ws_ticket() -> dict:
    ticket = await create_ticket()
    return {"ticket": ticket}
