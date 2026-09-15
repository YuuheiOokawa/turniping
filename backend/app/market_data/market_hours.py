import datetime as dt

import jpholiday

JST = dt.timezone(dt.timedelta(hours=9))

MORNING_OPEN = dt.time(9, 0)
MORNING_CLOSE = dt.time(11, 30)
AFTERNOON_OPEN = dt.time(12, 30)
AFTERNOON_CLOSE = dt.time(15, 0)


def now_jst() -> dt.datetime:
    return dt.datetime.now(JST)


def is_business_day(d: dt.date) -> bool:
    return d.weekday() < 5 and not jpholiday.is_holiday(d)


def is_market_open(moment: dt.datetime | None = None) -> bool:
    """東証(現物)の立会時間中かどうかを判定する。"""
    m = (moment or now_jst()).astimezone(JST)
    if not is_business_day(m.date()):
        return False
    t = m.time()
    return (MORNING_OPEN <= t < MORNING_CLOSE) or (AFTERNOON_OPEN <= t < AFTERNOON_CLOSE)


def next_open(moment: dt.datetime | None = None) -> dt.datetime:
    """次の立会開始時刻(JST)を返す。"""
    m = (moment or now_jst()).astimezone(JST)
    candidate_date = m.date()
    candidate_time = m.time()

    if is_business_day(candidate_date):
        if candidate_time < MORNING_OPEN:
            return dt.datetime.combine(candidate_date, MORNING_OPEN, tzinfo=JST)
        if candidate_time < AFTERNOON_OPEN and candidate_time >= MORNING_CLOSE:
            return dt.datetime.combine(candidate_date, AFTERNOON_OPEN, tzinfo=JST)

    next_day = candidate_date + dt.timedelta(days=1)
    while not is_business_day(next_day):
        next_day += dt.timedelta(days=1)
    return dt.datetime.combine(next_day, MORNING_OPEN, tzinfo=JST)
