import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://turniping:turniping@localhost:5432/turniping_test"
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401

settings = get_settings()


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        session_local = async_sessionmaker(engine, expire_on_commit=False)
        async with session_local() as s:
            yield s
    finally:
        await engine.dispose()
