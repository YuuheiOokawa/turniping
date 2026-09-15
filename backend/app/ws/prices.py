import asyncio
import contextlib

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.redis_client import get_redis
from app.ws.tickets import consume_ticket

router = APIRouter(tags=["ws"])


@router.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket, ticket: str = Query(...), codes: str = Query("")) -> None:
    valid = await consume_ticket(ticket)
    if not valid:
        await websocket.close(code=4401)
        return

    watched = [c.strip() for c in codes.split(",") if c.strip()]
    if not watched:
        await websocket.close(code=4400)
        return

    await websocket.accept()
    redis = get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(*(f"prices:{code}" for code in watched))

    async def forward() -> None:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            await websocket.send_text(message["data"])

    forward_task = asyncio.create_task(forward())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await forward_task
        await pubsub.unsubscribe()
        await pubsub.close()
