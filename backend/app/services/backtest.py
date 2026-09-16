import asyncio
import bisect
import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.backtest import BacktestSignalSample
from app.db.models.market import Instrument, Watchlist
from app.market_data.yahoo_jp import Candle, YahooFetchError, fetch_candles
from app.services.prediction_engine import combine_prediction, compute_technical_score

logger = logging.getLogger(__name__)

MARKET_INDEX_CODE = "^N225"
BACKTEST_RANGE = "5y"
# MACD(12,26,9)が計算できる最小日数。これより短いとcombine_predictionの
# シグナルが出そろわず、学習データとして不完全になる。
MIN_WARMUP_DAYS = 35
# 過去データ取得(ネットワークI/O)は他ジョブと同様に並行化する。
CONCURRENT_FETCH_LIMIT = 10


def generate_signal_samples(
    closes: list[float],
    dates: list[dt.date],
    *,
    volumes: list[float] | None = None,
    market_closes_by_date: dict[dt.date, float] | None = None,
) -> list[dict]:
    """過去の日足を1日ずつ遡り、その時点で分かっていた情報だけを使って
    (先読み無し)各シグナルの生値を計算し、翌営業日の実際の値動きと
    組み合わせたサンプルを返す。

    重要: day iのシグナルは closes[:i+1](day iまで)だけを使い、
    正解ラベルは closes[i+1] vs closes[i] という「未来の1点」だけを見る。
    combine_prediction自体はライブ予想と全く同じ関数を使うため、
    学習内容とライブ予想のロジックが乖離しない。
    """
    samples: list[dict] = []
    n = len(closes)
    # bisectで日付カットオフを二分探索するため、事前に日付順へソートしておく
    # (n×m の総当たりだと5年分×79銘柄で数分かかりかねないため)。
    market_dates_sorted = sorted(market_closes_by_date) if market_closes_by_date else []
    market_closes_sorted = [market_closes_by_date[d] for d in market_dates_sorted]

    for i in range(MIN_WARMUP_DAYS, n - 1):
        historical_closes = closes[: i + 1]
        historical_volumes = volumes[: i + 1] if volumes else None

        market_score = None
        if market_dates_sorted and dates[i] in market_closes_by_date:
            # その日までの日経平均の終値系列を作り、同じcompute_technical_scoreで
            # 相場全体のスコアを出す(ライブのprediction_compute.pyと同じロジック)。
            cutoff = bisect.bisect_right(market_dates_sorted, dates[i])
            market_series = market_closes_sorted[:cutoff]
            if len(market_series) >= 5:
                market_score, _, _ = compute_technical_score(market_series)

        result = combine_prediction(
            historical_closes,
            volumes=historical_volumes,
            market_score=market_score,
        )
        if result is None:
            continue

        actual_direction = "up" if closes[i + 1] >= closes[i] else "down"
        samples.append(
            {
                "as_of_date": dates[i],
                "signal_contributions": result.signal_contributions,
                "actual_direction": actual_direction,
            }
        )

    return samples


async def _fetch_one(semaphore: asyncio.Semaphore, instrument: Instrument) -> tuple[Instrument, list[Candle]]:
    async with semaphore:
        try:
            candles = await fetch_candles(instrument.code, interval="1d", range_=BACKTEST_RANGE)
        except YahooFetchError as exc:
            logger.warning("backtest fetch failed for %s: %s", instrument.code, exc)
            candles = []
        return instrument, candles


async def run_backtest(session: AsyncSession) -> dict:
    """ウォッチリスト銘柄について過去(既定5年)の日足を取得し、学習用サンプルを
    生成してDBに蓄積する。既に取り込み済みの日付はスキップするため、
    繰り返し実行しても安全(新しく増えた過去データや新規追加銘柄のみ処理)。
    """
    result = await session.execute(
        select(Instrument).join(Watchlist, Watchlist.instrument_id == Instrument.id)
    )
    instruments = result.scalars().all()

    # ネットワーク取得(I/O)はまとめて並行実行し、その後の指標計算(CPU)を
    # 銘柄ごとに区切って実行する。1回のawaitも無いままCPU計算だけを延々と
    # 回すとイベントループを長時間占有し、他ジョブ(答え合わせ等)の
    # スケジュール枠を奪う事故につながるため(過去に実際発生)、
    # 銘柄1件処理するごとに asyncio.sleep(0) で他タスクに制御を譲る。
    semaphore = asyncio.Semaphore(CONCURRENT_FETCH_LIMIT)
    fetch_results = await asyncio.gather(*(_fetch_one(semaphore, i) for i in instruments))
    candles_by_instrument = {instrument.id: candles for instrument, candles in fetch_results}

    market_instrument = next((i for i in instruments if i.code == MARKET_INDEX_CODE), None)
    market_closes_by_date: dict[dt.date, float] = {}
    if market_instrument is not None:
        market_candles = candles_by_instrument.get(market_instrument.id, [])
        market_closes_by_date = {c.ts.date(): c.close for c in market_candles}

    instruments_processed = 0
    samples_inserted = 0

    for instrument in instruments:
        candles = candles_by_instrument.get(instrument.id, [])
        if len(candles) < MIN_WARMUP_DAYS + 2:
            await asyncio.sleep(0)
            continue

        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]
        dates = [c.ts.date() for c in candles]

        is_market_itself = market_instrument is not None and instrument.id == market_instrument.id
        samples = generate_signal_samples(
            closes,
            dates,
            volumes=volumes,
            market_closes_by_date=None if is_market_itself else market_closes_by_date,
        )

        for sample in samples:
            stmt = (
                pg_insert(BacktestSignalSample)
                .values(
                    instrument_id=instrument.id,
                    as_of_date=sample["as_of_date"],
                    signal_contributions=sample["signal_contributions"],
                    actual_direction=sample["actual_direction"],
                )
                .on_conflict_do_nothing(constraint="uq_backtest_sample")
            )
            await session.execute(stmt)

        instruments_processed += 1
        samples_inserted += len(samples)
        await session.flush()
        await asyncio.sleep(0)

    return {"instruments_processed": instruments_processed, "samples_generated": samples_inserted}
