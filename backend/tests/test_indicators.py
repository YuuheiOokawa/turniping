from app.services import indicators


def _uptrend_closes(n: int = 40) -> list[float]:
    return [100 + i for i in range(n)]


def _downtrend_closes(n: int = 40) -> list[float]:
    return [100 - i for i in range(n)]


def test_sma_insufficient_data_returns_none():
    assert indicators.sma([1, 2, 3], 5) is None


def test_sma_basic():
    assert indicators.sma([1, 2, 3, 4, 5], 5) == 3.0


def test_rsi_uptrend_is_high():
    rsi = indicators.rsi(_uptrend_closes(), 14)
    assert rsi is not None
    assert rsi > 90


def test_rsi_downtrend_is_low():
    rsi = indicators.rsi(_downtrend_closes(), 14)
    assert rsi is not None
    assert rsi < 10


def test_macd_uptrend_positive_histogram():
    result = indicators.macd(_uptrend_closes())
    assert result is not None
    _macd_line, _signal_line, hist = result
    assert hist > 0


def test_bollinger_bounds_order():
    closes = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105, 100, 101, 99, 102, 98, 103, 97, 104, 96, 105]
    bands = indicators.bollinger(closes, 20)
    assert bands is not None
    lower, mid, upper = bands
    assert lower < mid < upper
