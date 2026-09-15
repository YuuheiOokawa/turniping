import datetime as dt

from app.market_data.market_hours import JST, is_business_day, is_market_open, next_open


def test_weekday_morning_session_is_open():
    # 2026-09-16 (Wed) 10:00 JST
    moment = dt.datetime(2026, 9, 16, 10, 0, tzinfo=JST)
    assert is_market_open(moment) is True


def test_lunch_break_is_closed():
    moment = dt.datetime(2026, 9, 16, 12, 0, tzinfo=JST)
    assert is_market_open(moment) is False


def test_weekend_is_closed():
    # 2026-09-19 (Sat)
    moment = dt.datetime(2026, 9, 19, 10, 0, tzinfo=JST)
    assert is_market_open(moment) is False
    assert is_business_day(moment.date()) is False


def test_national_holiday_is_closed():
    # 2026-09-21 (Mon) is 敬老の日 (Respect for the Aged Day)
    moment = dt.datetime(2026, 9, 21, 10, 0, tzinfo=JST)
    assert is_market_open(moment) is False


def test_next_open_after_close_same_day():
    # Friday 16:00 JST -> next open should be the following business day 9:00
    moment = dt.datetime(2026, 9, 18, 16, 0, tzinfo=JST)
    opening = next_open(moment)
    assert opening.time() == dt.time(9, 0)
    assert opening.date() > moment.date()


def test_next_open_during_lunch_is_afternoon_session():
    moment = dt.datetime(2026, 9, 16, 12, 0, tzinfo=JST)
    opening = next_open(moment)
    assert opening == dt.datetime(2026, 9, 16, 12, 30, tzinfo=JST)
