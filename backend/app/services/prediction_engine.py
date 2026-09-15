from dataclasses import dataclass, field

from app.services import indicators


@dataclass(slots=True)
class PredictionResult:
    direction: str  # "up" | "down"
    confidence: float  # 0-100
    technical_score: float  # 0-100 (50 = neutral)
    sentiment_score: float  # -1.0..1.0 (元のニュース平均スコア)
    reference_price: float
    reasons: list[str] = field(default_factory=list)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _signed(value: float) -> str:
    return f"+{value:.0f}pt" if value >= 0 else f"{value:.0f}pt"


def compute_technical_score(closes: list[float]) -> tuple[float, list[str]]:
    """テクニカル指標を合成して0-100のスコアと根拠リストを返す(50が中立)。

    各指標は「閾値を超えたら固定点数」ではなく、指標の実際の大きさに応じて
    連続的に加減点する(乖離率・RSIの50からの距離・MACDヒストグラムの価格比・
    %Bなど)。固定閾値だと同じ組み合わせが何度も同じスコアに落ち着き、
    確信度が特定の値(50%など)に偏って「適当」に見えてしまうため。
    """
    score = 50.0
    reasons: list[str] = []

    sma_short = indicators.sma(closes, 5)
    sma_long = indicators.sma(closes, 25)
    if sma_short is not None and sma_long is not None and sma_long != 0:
        pct_diff = (sma_short - sma_long) / sma_long * 100
        contribution = _clamp(pct_diff * 3, -15, 15)
        score += contribution
        if contribution > 1:
            reasons.append(f"短期移動平均が中期移動平均を{pct_diff:.1f}%上回り上昇トレンド({_signed(contribution)})")
        elif contribution < -1:
            reasons.append(f"短期移動平均が中期移動平均を{abs(pct_diff):.1f}%下回り下降トレンド({_signed(contribution)})")

    rsi_value = indicators.rsi(closes, 14)
    if rsi_value is not None:
        contribution = _clamp((50 - rsi_value) / 50 * 10, -10, 10)
        score += contribution
        if rsi_value < 35:
            reasons.append(f"RSIが{rsi_value:.1f}で売られすぎ寄り({_signed(contribution)})")
        elif rsi_value > 65:
            reasons.append(f"RSIが{rsi_value:.1f}で買われすぎ寄り({_signed(contribution)})")

    macd_result = indicators.macd(closes)
    if macd_result is not None and closes[-1]:
        _macd_line, _signal_line, hist = macd_result
        hist_pct = hist / closes[-1] * 100
        contribution = _clamp(hist_pct * 20, -10, 10)
        score += contribution
        if contribution > 1:
            reasons.append(f"MACDがシグナルを上回りモメンタム上向き({_signed(contribution)})")
        elif contribution < -1:
            reasons.append(f"MACDがシグナルを下回りモメンタム下向き({_signed(contribution)})")

    bands = indicators.bollinger(closes, 20)
    if bands is not None and closes:
        lower, _mid, upper = bands
        last = closes[-1]
        band_width = upper - lower
        if band_width > 0:
            percent_b = (last - lower) / band_width
            contribution = _clamp((0.5 - percent_b) * 10, -5, 5)
            score += contribution
            if percent_b < 0.2:
                reasons.append(f"ボリンジャーバンド下限付近(%B={percent_b:.2f})で反発期待({_signed(contribution)})")
            elif percent_b > 0.8:
                reasons.append(f"ボリンジャーバンド上限付近(%B={percent_b:.2f})で反落警戒({_signed(contribution)})")

    return _clamp(score), reasons


def combine_prediction(
    closes: list[float],
    *,
    sentiment_avg: float = 0.0,
    news_count: int = 0,
) -> PredictionResult | None:
    """テクニカルスコアとニュースセンチメントを合成して上昇/下落予想を作る。"""
    if not closes:
        return None

    technical_score, reasons = compute_technical_score(closes)

    sentiment_points = sentiment_avg * 20  # -1..1 -> -20..20点
    final_score = _clamp(technical_score + sentiment_points)

    if news_count > 0:
        if sentiment_avg > 0.15:
            reasons.append(f"直近ニュース{news_count}件のセンチメントがポジティブ")
        elif sentiment_avg < -0.15:
            reasons.append(f"直近ニュース{news_count}件のセンチメントがネガティブ")

    direction = "up" if final_score >= 50 else "down"
    confidence = _clamp(abs(final_score - 50) * 2)

    if not reasons:
        reasons.append("明確なシグナルが少なく中立的な判断")

    return PredictionResult(
        direction=direction,
        confidence=confidence,
        technical_score=technical_score,
        sentiment_score=sentiment_avg,
        reference_price=closes[-1],
        reasons=reasons,
    )
