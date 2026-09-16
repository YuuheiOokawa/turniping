import datetime as dt
from dataclasses import dataclass

import httpx

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "Mozilla/5.0 (compatible; turniping/0.1; +https://github.com/YuuheiOokawa/turniping)"


class YahooFetchError(RuntimeError):
    pass


@dataclass(slots=True)
class Candle:
    ts: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


async def _get_chart_json(symbol: str, params: dict) -> dict:
    """Yahoo chart APIを叩き、パース済みJSONを返す。

    httpxのトランスポート層例外(タイムアウト・TLSハンドシェイク失敗など)は
    ここで一括してYahooFetchErrorに正規化する。呼び出し元は全員
    `except YahooFetchError` だけ書けばよく、個々の呼び出し元でネットワーク
    例外を握り忘れて銘柄1件の一時的な通信エラーでジョブ全体(79銘柄分の
    予想生成など)が落ちる、という事故を防ぐ。
    """
    try:
        async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(CHART_URL.format(symbol=symbol), params=params)
    except httpx.HTTPError as exc:
        raise YahooFetchError(f"yahoo chart request failed for {symbol}: {exc}") from exc

    if resp.status_code != 200:
        raise YahooFetchError(f"yahoo chart HTTP {resp.status_code} for {symbol}")

    payload = resp.json()
    result = payload.get("chart", {}).get("result")
    if not result:
        error = payload.get("chart", {}).get("error")
        raise YahooFetchError(f"yahoo chart returned no result for {symbol}: {error}")
    return result[0]


async def fetch_candles(symbol: str, *, interval: str = "1d", range_: str = "3mo") -> list[Candle]:
    """Yahoo Finance の公開chart APIから実際のOHLCVを取得する。ライブラリは使わずrawで叩く。"""
    node = await _get_chart_json(symbol, {"interval": interval, "range": range_})

    timestamps = node.get("timestamp") or []
    quote = node.get("indicators", {}).get("quote", [{}])[0]

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    candles: list[Candle] = []
    for i, ts in enumerate(timestamps):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        if o is None or h is None or l is None or c is None:
            continue
        candles.append(
            Candle(
                ts=dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc),
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0.0,
            )
        )
    return candles


async def fetch_latest_price(symbol: str) -> Candle | None:
    """当日の1分足の最終バーを最新値として取得する(市場が開いている前提)。"""
    candles = await fetch_candles(symbol, interval="1m", range_="1d")
    return candles[-1] if candles else None


async def fetch_symbol_meta(symbol: str) -> dict:
    """銘柄名などのメタ情報を取得する(新規銘柄をウォッチリストに追加する際に使用)。"""
    node = await _get_chart_json(symbol, {"interval": "1d", "range": "5d"})
    return node.get("meta", {})
