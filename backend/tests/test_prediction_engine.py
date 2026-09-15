from app.services.prediction_engine import combine_prediction


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
