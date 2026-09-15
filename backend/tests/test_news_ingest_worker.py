import datetime as dt

from sqlalchemy import select

from app.db.models.news import NewsArticle
from app.services.news_ingest import RawArticle
from app.worker.jobs.news_ingest import _upsert_article


def _article(url: str, published_at: dt.datetime | None) -> RawArticle:
    return RawArticle(
        source="test",
        url=url,
        title="テスト記事",
        summary="",
        published_at=published_at,  # type: ignore[arg-type]
    )


async def test_one_bad_article_does_not_abort_the_batch(session):
    """A single article that fails to insert (e.g. a DB constraint violation)
    must not take down the whole ingestion cycle via a poisoned transaction —
    this regression covers the StringDataRightTruncationError incident where
    one over-long Google News URL silently zeroed out an entire news_ingest run.
    """
    good_before = _article("https://example.com/before", dt.datetime.now(dt.timezone.utc))
    bad = _article("https://example.com/bad", None)  # published_at NOT NULL violation
    good_after = _article("https://example.com/after", dt.datetime.now(dt.timezone.utc))

    result_before = await _upsert_article(session, good_before)
    result_bad = await _upsert_article(session, bad)
    result_after = await _upsert_article(session, good_after)

    assert result_before is not None
    assert result_bad is None
    assert result_after is not None

    await session.commit()

    result = await session.execute(select(NewsArticle.url))
    stored_urls = set(result.scalars().all())
    assert stored_urls == {"https://example.com/before", "https://example.com/after"}
