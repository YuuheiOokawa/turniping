import datetime as dt

from app.services import backtest
from app.services.prediction_engine import combine_prediction


def _dates(n: int, start: dt.date = dt.date(2020, 1, 1)) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range(n)]


def test_no_samples_when_shorter_than_warmup():
    closes = [100.0] * (backtest.MIN_WARMUP_DAYS - 1)
    dates = _dates(len(closes))
    samples = backtest.generate_signal_samples(closes, dates)
    assert samples == []


def test_sample_count_matches_available_days():
    n = backtest.MIN_WARMUP_DAYS + 10
    closes = [100 + i * 0.5 for i in range(n)]
    dates = _dates(n)
    samples = backtest.generate_signal_samples(closes, dates)
    # day indices MIN_WARMUP_DAYS..n-2 inclusive get a sample (need a "next day" label)
    assert len(samples) == n - 1 - backtest.MIN_WARMUP_DAYS


def test_no_lookahead_bias():
    """Day i's sample must be identical to calling combine_prediction with only
    the data available up to and including day i — never anything from day i+1
    onward, since that would leak the future into the "prediction"."""
    n = backtest.MIN_WARMUP_DAYS + 5
    closes = [100 + (i % 7) * 1.3 for i in range(n)]
    dates = _dates(n)
    samples = backtest.generate_signal_samples(closes, dates)

    # Pick the first sample (day = MIN_WARMUP_DAYS) and verify it matches a
    # direct call using only closes[:MIN_WARMUP_DAYS + 1].
    day = backtest.MIN_WARMUP_DAYS
    expected = combine_prediction(closes[: day + 1])
    sample = next(s for s in samples if s["as_of_date"] == dates[day])
    assert sample["signal_contributions"] == expected.signal_contributions


def test_actual_direction_reflects_next_day_close():
    n = backtest.MIN_WARMUP_DAYS + 3
    closes = [100.0] * n
    # Force day (MIN_WARMUP_DAYS) -> day+1 to go down, and the next pair to go up.
    closes[backtest.MIN_WARMUP_DAYS + 1] = 90.0
    closes[backtest.MIN_WARMUP_DAYS + 2] = 95.0
    dates = _dates(n)
    samples = backtest.generate_signal_samples(closes, dates)

    by_date = {s["as_of_date"]: s for s in samples}
    assert by_date[dates[backtest.MIN_WARMUP_DAYS]]["actual_direction"] == "down"
    assert by_date[dates[backtest.MIN_WARMUP_DAYS + 1]]["actual_direction"] == "up"


def test_market_regime_uses_only_market_data_up_to_that_day():
    n = backtest.MIN_WARMUP_DAYS + 5
    closes = [100 + i * 1.2 for i in range(n)]
    dates = _dates(n)

    # A bullish market series for the whole window.
    market_by_date = {d: 100 + i * 2.0 for i, d in enumerate(dates)}

    with_market = backtest.generate_signal_samples(closes, dates, market_closes_by_date=market_by_date)
    without_market = backtest.generate_signal_samples(closes, dates, market_closes_by_date=None)

    assert "market_regime" in with_market[0]["signal_contributions"]
    assert "market_regime" not in without_market[0]["signal_contributions"]
