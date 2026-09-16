"""テクニカル指標計算。closesは古い順(昇順)の終値リストを想定。"""


def sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def ema_series(closes: list[float], period: int) -> list[float]:
    if not closes:
        return []
    k = 2 / (period + 1)
    out = [closes[0]]
    for price in closes[1:]:
        out.append(price * k + out[-1] * (1 - k))
    return out


def ema(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return ema_series(closes, period)[-1]


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[float, float, float] | None:
    if len(closes) < slow + signal:
        return None
    fast_series = ema_series(closes, fast)
    slow_series = ema_series(closes, slow)
    macd_series = [f - s for f, s in zip(fast_series, slow_series)]
    signal_series = ema_series(macd_series, signal)
    macd_line = macd_series[-1]
    signal_line = signal_series[-1]
    return macd_line, signal_line, macd_line - signal_line


def bollinger(closes: list[float], period: int = 20, num_std: float = 2.0) -> tuple[float, float, float] | None:
    if len(closes) < period:
        return None
    window = closes[-period:]
    mid = sum(window) / period
    variance = sum((c - mid) ** 2 for c in window) / period
    std = variance**0.5
    return mid - num_std * std, mid, mid + num_std * std


def volume_ratio(volumes: list[float], period: int = 20) -> float | None:
    """直近出来高 ÷ 直前period日平均出来高。1.0が平均並み、大きいほど商いが伴っている。

    指数(日経平均など)はvolumeが0で記録されることがあるため、平均が0や
    直近値が0の場合はNoneを返して「判断材料なし」として扱う。
    """
    if len(volumes) < period + 1:
        return None
    latest = volumes[-1]
    if not latest or latest <= 0:
        return None
    baseline = [v for v in volumes[-(period + 1) : -1] if v and v > 0]
    if not baseline:
        return None
    avg = sum(baseline) / len(baseline)
    if avg <= 0:
        return None
    return latest / avg
