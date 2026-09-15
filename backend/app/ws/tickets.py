import secrets

from app.redis_client import get_redis

TICKET_PREFIX = "ws-ticket:"
TICKET_TTL_SECONDS = 30


async def create_ticket() -> str:
    ticket = secrets.token_urlsafe(24)
    redis = get_redis()
    await redis.set(f"{TICKET_PREFIX}{ticket}", "1", ex=TICKET_TTL_SECONDS)
    return ticket


async def consume_ticket(ticket: str) -> bool:
    """一度きりのチケットを検証し、成功したら削除する。"""
    redis = get_redis()
    key = f"{TICKET_PREFIX}{ticket}"
    deleted = await redis.delete(key)
    return deleted == 1
