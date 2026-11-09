"""The tests live OUTSIDE src/: they import the package exactly like a user,
so a file forgotten in the package makes them fail (the point of the src layout)."""
import pytest

from bookandride_pricing import __version__, calculate_price


@pytest.mark.parametrize("minutes, price", [(0, 0.0), (40, 10.0), (100, 12.0),
                                            (24 * 60 + 1, 12.25), (2 * 24 * 60 + 120, 36.0)])
def test_price(minutes, price):
    assert calculate_price(minutes) == price


def test_negative_minutes_refused():
    with pytest.raises(ValueError):
        calculate_price(-1)


def test_version_comes_from_pyproject():
    assert __version__ == "1.0.0"
