from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_auth
from app.db.models.market import Instrument
from app.db.models.news import NewsArticle, NewsInstrumentLink
from app.db.session import get_session

router = APIRouter(prefix="/news", tags=["news"], dependencies=[Depends(require_auth)])


def _serialize(article: NewsArticle) -> dict:
    return {
        "id": article.id,
        "source": article.source,
        "url": article.url,
        "title": article.title,
        "summary": article.summary,
        "published_at": article.published_at.isoformat(),
        "sentiment_score": article.sentiment_score,
        "sentiment_label": article.sentiment_label,
    }


@router.get("")
async def list_news(
    code: str | None = None, limit: int = 50, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    if code:
        result = await session.execute(select(Instrument).where(Instrument.code == code))
        instrument = result.scalar_one_or_none()
        if instrument is None:
            raise HTTPException(status_code=404, detail="instrument not found")
        result = await session.execute(
            select(NewsArticle)
            .join(NewsInstrumentLink, NewsInstrumentLink.news_id == NewsArticle.id)
            .where(NewsInstrumentLink.instrument_id == instrument.id)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
    else:
        result = await session.execute(
            select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(limit)
        )

    return [_serialize(a) for a in result.scalars().all()]
