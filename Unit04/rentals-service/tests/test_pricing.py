import pytest

from app.pricing import calculate_price, price_detail


@pytest.mark.parametrize("minutes, price", [
    (40, 10.0), (48, 12.0), (100, 12.0),          # cap within one day
    (24 * 60, 12.0), (24 * 60 + 1, 12.25),        # cap applies PER day
    (24 * 60 + 100, 24.0), (2 * 24 * 60 + 120, 36.0), (0, 0.0),
])
def test_price(minutes, price):
    assert calculate_price(minutes) == price


def test_negative_minutes_rejected():
    with pytest.raises(ValueError):
        calculate_price(-5)


def test_price_detail():
    assert price_detail(24 * 60 + 100) == {"full_days": 1, "remaining_minutes": 100,
                                           "price_per_minute": 0.25, "daily_cap": 12.0,
                                           "capped": True}
