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


def compute_technical_score(closes: list[float]) -> tuple[float, list[str]]:
    """テクニカル指標を合成して0-100のスコアと根拠リストを返す(50が中立)。"""
    score = 50.0
    reasons: list[str] = []

    sma_short = indicators.sma(closes, 5)
    sma_long = indicators.sma(closes, 25)
    if sma_short is not None and sma_long is not None:
        if sma_short > sma_long:
            score += 15
            reasons.append("短期移動平均(5)が中期移動平均(25)を上回っており上昇トレンド傾向")
        else:
            score -= 15
            reasons.append("短期移動平均(5)が中期移動平均(25)を下回っており下降トレンド傾向")

    rsi_value = indicators.rsi(closes, 14)
    if rsi_value is not None:
        if rsi_value < 30:
            score += 10
            reasons.append(f"RSIが{rsi_value:.1f}と売られすぎ水準(反発期待)")
        elif rsi_value > 70:
            score -= 10
            reasons.append(f"RSIが{rsi_value:.1f}と買われすぎ水準(反落警戒)")

    macd_result = indicators.macd(closes)
    if macd_result is not None:
        macd_line, signal_line, _hist = macd_result
        if macd_line > signal_line:
            score += 10
            reasons.append("MACDがシグナルラインを上回り上昇モメンタム")
        else:
            score -= 10
            reasons.append("MACDがシグナルラインを下回り下降モメンタム")

    bands = indicators.bollinger(closes, 20)
    if bands is not None and closes:
        lower, _mid, upper = bands
        last = closes[-1]
        if last < lower:
            score += 5
            reasons.append("ボリンジャーバンド下限を下回り反発期待")
        elif last > upper:
            score -= 5
            reasons.append("ボリンジャーバンド上限を上回り反落警戒")

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
