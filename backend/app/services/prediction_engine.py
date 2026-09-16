from dataclasses import dataclass, field

from app.services import indicators

# 自己学習(strategy_learning.py)が重みを調整する対象のシグナル名。
# 各シグナルは「正=強気、負=弱気、0/欠落=意見なし」の生の方向性を表す
# (重み適用前の値)。出来高はそれ単体では方向を持たず他シグナルの
# 補強/割引に使うだけなので学習対象には含めない。
LEARNABLE_SIGNALS = ["sma_cross", "rsi", "macd", "bollinger", "sentiment", "market_regime"]


@dataclass(slots=True)
class PredictionResult:
    direction: str  # "up" | "down"
    confidence: float  # 0-100
    technical_score: float  # 0-100 (50 = neutral)
    sentiment_score: float  # -1.0..1.0 (元のニュース平均スコア)
    reference_price: float
    reasons: list[str] = field(default_factory=list)
    # signal_name -> 重み適用前の生の方向シグナル値(自己学習用)
    signal_contributions: dict[str, float] = field(default_factory=dict)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _signed(value: float) -> str:
    return f"+{value:.0f}pt" if value >= 0 else f"{value:.0f}pt"


def compute_technical_score(
    closes: list[float],
    *,
    volumes: list[float] | None = None,
    weights: dict[str, float] | None = None,
) -> tuple[float, list[str], dict[str, float]]:
    """テクニカル指標を合成して0-100のスコアと根拠リスト、シグナル別の生の
    方向値(50が中立)を返す。

    各指標は「閾値を超えたら固定点数」ではなく、指標の実際の大きさに応じて
    連続的に加減点する(乖離率・RSIの50からの距離・MACDヒストグラムの価格比・
    %Bなど)。固定閾値だと同じ組み合わせが何度も同じスコアに落ち着き、
    確信度が特定の値(50%など)に偏って「適当」に見えてしまうため。

    weightsを渡すと、各シグナルの影響力を(自己学習で調整された重みで)
    増減できる。volumesを渡すと、出来高が伴った値動きかどうかで最終的な
    確信度を補強/割引する(商いを伴わない値動きは「だまし」になりやすいため)。
    """
    weights = weights or {}
    delta = 0.0
    reasons: list[str] = []
    contributions: dict[str, float] = {}

    sma_short = indicators.sma(closes, 5)
    sma_long = indicators.sma(closes, 25)
    if sma_short is not None and sma_long is not None and sma_long != 0:
        pct_diff = (sma_short - sma_long) / sma_long * 100
        raw = _clamp(pct_diff * 3, -15, 15)
        contributions["sma_cross"] = raw
        applied = raw * weights.get("sma_cross", 1.0)
        delta += applied
        if applied > 1:
            reasons.append(f"短期移動平均が中期移動平均を{pct_diff:.1f}%上回り上昇トレンド({_signed(applied)})")
        elif applied < -1:
            reasons.append(f"短期移動平均が中期移動平均を{abs(pct_diff):.1f}%下回り下降トレンド({_signed(applied)})")

    rsi_value = indicators.rsi(closes, 14)
    if rsi_value is not None:
        raw = _clamp((50 - rsi_value) / 50 * 10, -10, 10)
        contributions["rsi"] = raw
        applied = raw * weights.get("rsi", 1.0)
        delta += applied
        if rsi_value < 35:
            reasons.append(f"RSIが{rsi_value:.1f}で売られすぎ寄り({_signed(applied)})")
        elif rsi_value > 65:
            reasons.append(f"RSIが{rsi_value:.1f}で買われすぎ寄り({_signed(applied)})")

    macd_result = indicators.macd(closes)
    if macd_result is not None and closes[-1]:
        _macd_line, _signal_line, hist = macd_result
        hist_pct = hist / closes[-1] * 100
        raw = _clamp(hist_pct * 20, -10, 10)
        contributions["macd"] = raw
        applied = raw * weights.get("macd", 1.0)
        delta += applied
        if applied > 1:
            reasons.append(f"MACDがシグナルを上回りモメンタム上向き({_signed(applied)})")
        elif applied < -1:
            reasons.append(f"MACDがシグナルを下回りモメンタム下向き({_signed(applied)})")

    bands = indicators.bollinger(closes, 20)
    if bands is not None and closes:
        lower, _mid, upper = bands
        last = closes[-1]
        band_width = upper - lower
        if band_width > 0:
            percent_b = (last - lower) / band_width
            raw = _clamp((0.5 - percent_b) * 10, -5, 5)
            contributions["bollinger"] = raw
            applied = raw * weights.get("bollinger", 1.0)
            delta += applied
            if percent_b < 0.2:
                reasons.append(f"ボリンジャーバンド下限付近(%B={percent_b:.2f})で反発期待({_signed(applied)})")
            elif percent_b > 0.8:
                reasons.append(f"ボリンジャーバンド上限付近(%B={percent_b:.2f})で反落警戒({_signed(applied)})")

    if volumes and delta != 0:
        vol_ratio = indicators.volume_ratio(volumes)
        if vol_ratio is not None:
            multiplier = None
            if vol_ratio >= 1.5:
                multiplier = 1.15
            elif vol_ratio <= 0.6:
                multiplier = 0.85
            if multiplier is not None:
                before = delta
                delta *= multiplier
                verb = "補強" if multiplier > 1 else "割引"
                reasons.append(
                    f"出来高が平均の{vol_ratio:.1f}倍({'多い' if multiplier > 1 else '少ない'})"
                    f"ため確信度を{verb}({_signed(delta - before)})"
                )

    return _clamp(50 + delta), reasons, contributions


def combine_prediction(
    closes: list[float],
    *,
    sentiment_avg: float = 0.0,
    news_count: int = 0,
    volumes: list[float] | None = None,
    market_score: float | None = None,
    weights: dict[str, float] | None = None,
) -> PredictionResult | None:
    """テクニカルスコア・ニュースセンチメント・出来高・相場全体との整合性を合成して
    上昇/下落予想を作る。

    market_scoreには市場全体(日経平均など)の compute_technical_score の
    結果を渡す。個別銘柄の方向感が相場全体と一致していれば確信度を強め、
    逆行していれば弱める("Don't fight the tape" — 相場全体に逆らう銘柄は
    個別に強い材料がない限り分が悪いという経験則)。

    weightsは各シグナルの信頼度(自己学習で調整)。答え合わせの実績に基づき
    strategy_learning.recalibrate() が定期的に更新する。
    """
    if not closes:
        return None
    weights = weights or {}

    technical_score, reasons, contributions = compute_technical_score(closes, volumes=volumes, weights=weights)
    delta = technical_score - 50

    contributions["sentiment"] = sentiment_avg * 20  # -1..1 -> -20..20点(重み適用前)
    delta += contributions["sentiment"] * weights.get("sentiment", 1.0)

    if news_count > 0:
        if sentiment_avg > 0.15:
            reasons.append(f"直近ニュース{news_count}件のセンチメントがポジティブ")
        elif sentiment_avg < -0.15:
            reasons.append(f"直近ニュース{news_count}件のセンチメントがネガティブ")

    if market_score is not None:
        market_delta = market_score - 50
        contributions["market_regime"] = market_delta
        if market_delta != 0 and delta != 0:
            regime_weight = weights.get("market_regime", 1.0)
            if (delta > 0) == (market_delta > 0):
                bonus = min(abs(market_delta), 15) * 0.3 * regime_weight
                before = delta
                delta += bonus if delta > 0 else -bonus
                reasons.append(f"日経平均も同方向のトレンドで相場全体と整合的({_signed(delta - before)})")
            else:
                damp = abs(delta) * 0.3 * regime_weight
                before = delta
                delta += -damp if delta > 0 else damp
                reasons.append(f"日経平均は逆方向のトレンドで相場全体に逆行({_signed(delta - before)})")

    final_score = _clamp(50 + delta)
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
        signal_contributions=contributions,
    )
