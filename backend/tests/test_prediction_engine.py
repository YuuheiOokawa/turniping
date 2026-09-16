from app.services.prediction_engine import combine_prediction, compute_technical_score


def test_no_data_returns_none():
    assert combine_prediction([]) is None


def test_strong_uptrend_predicts_up():
    closes = [100 + i * 1.5 for i in range(40)]
    result = combine_prediction(closes)
    assert result is not None
    assert result.direction == "up"
    assert result.confidence > 0
    assert result.reasons


def test_strong_downtrend_predicts_down():
    closes = [200 - i * 1.5 for i in range(40)]
    result = combine_prediction(closes)
    assert result is not None
    assert result.direction == "down"


def test_positive_sentiment_lifts_confidence_from_neutral_baseline():
    # Too few closes for any indicator to fire -> technical_score stays at the neutral 50.
    short_closes = [100.0, 100.0, 100.0]
    neutral = combine_prediction(short_closes, sentiment_avg=0.0)
    positive = combine_prediction(short_closes, sentiment_avg=1.0, news_count=3)
    assert neutral is not None and positive is not None
    assert neutral.direction == "up"  # 50 counts as "up" (>=50)
    assert neutral.confidence == 0
    assert positive.direction == "up"
    assert positive.confidence > neutral.confidence


def test_high_volume_amplifies_technical_score():
    closes = [100 + i * 1.5 for i in range(40)]
    low_volume = [1000.0] * 40
    high_volume = [1000.0] * 39 + [3000.0]  # latest bar is 3x the 20-day average

    quiet_score, _, _ = compute_technical_score(closes, volumes=low_volume)
    loud_score, loud_reasons, _ = compute_technical_score(closes, volumes=high_volume)

    assert loud_score > quiet_score
    assert any("出来高" in r for r in loud_reasons)


def test_low_volume_dampens_technical_score():
    closes = [100 + i * 1.5 for i in range(40)]
    normal_volume = [1000.0] * 40
    thin_volume = [1000.0] * 39 + [200.0]  # latest bar is far below the 20-day average

    normal_score, _, _ = compute_technical_score(closes, volumes=normal_volume)
    thin_score, thin_reasons, _ = compute_technical_score(closes, volumes=thin_volume)

    assert thin_score < normal_score
    assert any("出来高" in r for r in thin_reasons)


def test_market_agreement_boosts_confidence():
    closes = [100 + i * 1.5 for i in range(40)]  # bullish individual stock
    bullish_market = 70.0  # 日経平均も上昇トレンド
    bearish_market = 30.0  # 日経平均は下降トレンド

    no_market = combine_prediction(closes)
    aligned = combine_prediction(closes, market_score=bullish_market)
    against = combine_prediction(closes, market_score=bearish_market)

    assert no_market is not None and aligned is not None and against is not None
    assert aligned.confidence > no_market.confidence
    assert against.confidence < no_market.confidence
    assert any("整合的" in r for r in aligned.reasons)
    assert any("逆行" in r for r in against.reasons)


def test_signal_contributions_are_recorded_with_correct_sign():
    closes = [100 + i * 1.5 for i in range(40)]  # strong uptrend
    result = combine_prediction(closes, sentiment_avg=0.5, news_count=2, market_score=70.0)
    assert result is not None
    assert result.signal_contributions["sma_cross"] > 0
    assert result.signal_contributions["macd"] > 0
    assert result.signal_contributions["sentiment"] > 0
    assert result.signal_contributions["market_regime"] > 0


def test_zero_weight_removes_exactly_that_signals_contribution():
    # combine_prediction's final confidence isn't monotonic in a single
    # weight (zeroing a dominant signal can flip the overall direction),
    # so assert precisely on the additive delta via compute_technical_score
    # instead: zeroing sma_cross's weight must change the score by exactly
    # its raw (pre-weight) contribution, no more, no less.
    closes = [100 + i * 1.5 for i in range(40)]
    default_score, _, contributions = compute_technical_score(closes)
    silenced_score, _, silenced_contributions = compute_technical_score(closes, weights={"sma_cross": 0.0})

    assert default_score - silenced_score == contributions["sma_cross"]
    # contributions には重み適用前の生の値が記録され続ける(学習用)
    assert silenced_contributions["sma_cross"] == contributions["sma_cross"]


def test_amplified_weight_increases_confidence():
    closes = [100 + i * 1.5 for i in range(40)]
    default = combine_prediction(closes)
    boosted = combine_prediction(closes, weights={"sma_cross": 2.0})
    assert default is not None and boosted is not None
    assert boosted.confidence > default.confidence
