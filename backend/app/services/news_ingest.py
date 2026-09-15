import asyncio
import datetime as dt
from dataclasses import dataclass
from urllib.parse import quote

import feedparser

GENERAL_FEEDS = [
    # 国内景気・市場
    ("NHK経済", "https://www3.nhk.or.jp/rss/news/cat5.xml"),
    ("GoogleNews-日経平均", "https://news.google.com/rss/search?q=日経平均&hl=ja&gl=JP&ceid=JP:ja"),
    ("GoogleNews-日本株市場", "https://news.google.com/rss/search?q=日本株+市場+東証&hl=ja&gl=JP&ceid=JP:ja"),
    # 世界経済・海外市場(円相場や日本株に影響する海外要因を常時収集)
    ("NHK国際", "https://www3.nhk.or.jp/rss/news/cat6.xml"),
    ("GoogleNews-世界経済", "https://news.google.com/rss/search?q=世界経済+株式市場&hl=ja&gl=JP&ceid=JP:ja"),
    ("GoogleNews-米国株式市場", "https://news.google.com/rss/search?q=NYダウ+米国株式市場&hl=ja&gl=JP&ceid=JP:ja"),
    ("GoogleNews-FRB金利", "https://news.google.com/rss/search?q=FRB+利上げ+利下げ&hl=ja&gl=JP&ceid=JP:ja"),
    ("GoogleNews-為替", "https://news.google.com/rss/search?q=為替+円相場&hl=ja&gl=JP&ceid=JP:ja"),
    ("GoogleNews-原油価格", "https://news.google.com/rss/search?q=原油価格+資源価格&hl=ja&gl=JP&ceid=JP:ja"),
    ("GoogleNews-中国経済", "https://news.google.com/rss/search?q=中国経済+景気&hl=ja&gl=JP&ceid=JP:ja"),
]


@dataclass(slots=True)
class RawArticle:
    source: str
    url: str
    title: str
    summary: str
    published_at: dt.datetime


def _instrument_feed_url(name: str) -> str:
    query = quote(f"{name} 株価")
    return f"https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"


def _parse_feed_sync(source: str, url: str) -> list[RawArticle]:
    parsed = feedparser.parse(url)
    articles: list[RawArticle] = []
    for entry in parsed.entries:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue
        summary = entry.get("summary", "")
        published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if published_struct:
            published_at = dt.datetime(*published_struct[:6], tzinfo=dt.timezone.utc)
        else:
            published_at = dt.datetime.now(dt.timezone.utc)
        articles.append(
            RawArticle(source=source, url=link, title=title, summary=summary, published_at=published_at)
        )
    return articles


async def fetch_feed(source: str, url: str) -> list[RawArticle]:
    return await asyncio.to_thread(_parse_feed_sync, source, url)


async def fetch_general_market_news() -> list[RawArticle]:
    results: list[list[RawArticle]] = await asyncio.gather(
        *(fetch_feed(source, url) for source, url in GENERAL_FEEDS), return_exceptions=False
    )
    articles: list[RawArticle] = []
    for chunk in results:
        articles.extend(chunk)
    return articles


async def fetch_articles_for_instrument(name: str) -> list[RawArticle]:
    return await fetch_feed(f"GoogleNews-{name}", _instrument_feed_url(name))
