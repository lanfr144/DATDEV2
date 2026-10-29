import pytest

from app.pricing import calculate_price


def test_price_under_cap():
    assert calculate_price(40) == 10.0      # 40 × 0.25 = 10.00


def test_price_at_cap():
    assert calculate_price(48) == 12.0      # 48 × 0.25 = 12.00 exactly


def test_price_over_cap():
    assert calculate_price(100) == 12.0     # 25.00 → capped to 12.00


def test_negative_minutes_rejected():
    with pytest.raises(ValueError):
        calculate_price(-5)


# ---------- stretch goal: the €12 cap applies per day ----------
def test_exactly_one_day_costs_one_cap():
    assert calculate_price(24 * 60) == 12.0         # 1 full day


def test_one_minute_into_the_second_day():
    assert calculate_price(24 * 60 + 1) == 12.25    # 12 + 1 × 0.25


def test_second_day_is_capped_too():
    assert calculate_price(24 * 60 + 100) == 24.0   # 12 + min(25.00, 12)


def test_several_days():
    assert calculate_price(2 * 24 * 60 + 120) == 36.0   # 2 × 12 + min(30.00, 12)


def test_zero_minutes_is_free():
    assert calculate_price(0) == 0.0


# ---------- Unit 03: the price parameters come from the configuration ----------
def test_price_parameters_can_be_changed_by_configuration():
    assert calculate_price(100, price_per_minute=0.10, daily_cap=12.0) == 10.0
    assert calculate_price(100, price_per_minute=0.25, daily_cap=20.0) == 20.0
