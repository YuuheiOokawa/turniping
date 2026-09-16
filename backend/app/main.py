import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ai_trading, market, news, paper, predictions, system
from app.bootstrap import seed_default_watchlist
from app.config import get_settings
from app.db.session import session_scope
from app.ws import prices as ws_prices

settings = get_settings()

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("turniping")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env != "development" and settings.app_api_token == "dev-local-token":
        raise RuntimeError("APP_API_TOKEN must be set outside development")

    async with session_scope() as session:
        await seed_default_watchlist(session)

    logger.info("turniping backend started (env=%s)", settings.app_env)
    yield


app = FastAPI(title="turniping API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(news.router, prefix="/api/v1")
app.include_router(paper.router, prefix="/api/v1")
app.include_router(ai_trading.router, prefix="/api/v1")
app.include_router(ws_prices.router)
