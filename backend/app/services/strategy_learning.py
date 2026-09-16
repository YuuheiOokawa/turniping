import datetime as dt
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.backtest import BacktestSignalSample
from app.db.models.prediction import Prediction, PredictionOutcome
from app.db.models.strategy import StrategySignalWeight
from app.services.prediction_engine import LEARNABLE_SIGNALS

# 十分な件数が無いと1回の運不運で重みが暴れるため、最低サンプル数を設ける。
MIN_SAMPLE_SIZE = 20
# Multiplicative Weights (Hedge) の学習率。大きいほど直近の実績に敏感に反応する。
LEARNING_RATE = 0.15
# 1つのシグナルが支配的になりすぎたり、逆に発言権を完全に失って
# 二度と回復できなくなったりしないよう、重みの可動域を制限する。
MIN_WEIGHT = 0.3
MAX_WEIGHT = 2.0


async def load_weights(session: AsyncSession) -> dict[str, float]:
    result = await session.execute(select(StrategySignalWeight))
    return {row.signal_name: row.weight for row in result.scalars().all()}


async def recalibrate(session: AsyncSession) -> list[dict]:
    """ライブの答え合わせ実績 + 過去の日足から生成したバックテストサンプルを
    合わせて振り返り、各シグナルが単独でどれだけ方向を当てられていたかを
    集計し、Multiplicative Weights (Hedge) アルゴリズムで重みを更新する。
    的中率が高いシグナルほど重み(発言力)が増し、外れが多いシグナルほど
    重みが下がる。ブラックボックスなMLではなく、「どのシグナルが何%的中し、
    重みがいくつになったか」を常に説明できる形。

    ライブの答え合わせだけでは(60分先の予想を市場が開いている間しか
    評価できないため)十分な件数が溜まるまでに何日もかかる。過去の日足を
    使ったバックテストサンプルを同じ集計に混ぜることで、統計的な確からしさを
    大幅に前倒しで得られる(ただしバックテストは「翌営業日の終値」、ライブは
    「60分後」という異なる時間軸の近似であることには留意)。
    """
    live_result = await session.execute(
        select(Prediction.signal_contributions, PredictionOutcome.actual_change_pct).join(
            PredictionOutcome, PredictionOutcome.prediction_id == Prediction.id
        )
    )
    live_rows = [
        (contributions, "up" if change_pct >= 0 else "down")
        for contributions, change_pct in live_result.all()
    ]

    backtest_result = await session.execute(
        select(BacktestSignalSample.signal_contributions, BacktestSignalSample.actual_direction)
    )
    all_rows = live_rows + list(backtest_result.all())

    existing = {row.signal_name: row for row in (await session.scalars(select(StrategySignalWeight))).all()}

    summaries: list[dict] = []
    for signal_name in LEARNABLE_SIGNALS:
        hits = 0
        total = 0
        for contributions, actual_direction in all_rows:
            contribution = (contributions or {}).get(signal_name)
            if not contribution:
                continue
            signal_direction = "up" if contribution > 0 else "down"
            total += 1
            if signal_direction == actual_direction:
                hits += 1

        if total < MIN_SAMPLE_SIZE:
            continue

        accuracy = hits / total
        row = existing.get(signal_name)
        current_weight = row.weight if row else 1.0

        # accuracy > 0.5 なら重みを増やし、< 0.5 なら減らす。exp()により
        # 極端な1回の集計で重みが急変しないよう滑らかに調整する。
        new_weight = current_weight * math.exp(LEARNING_RATE * (2 * accuracy - 1))
        new_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, new_weight))

        if row is None:
            row = StrategySignalWeight(signal_name=signal_name)
            session.add(row)
        row.weight = new_weight
        row.sample_size = total
        row.accuracy = accuracy
        row.updated_at = dt.datetime.now(dt.timezone.utc)

        summaries.append(
            {
                "signal_name": signal_name,
                "weight": new_weight,
                "accuracy": accuracy,
                "sample_size": total,
            }
        )

    await session.flush()
    return summaries
