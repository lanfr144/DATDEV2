"""
Business rule in its own file: it can be unit-tested without a database.

The price parameters now come from the configuration (config.yaml, per
environment): staging can try a new price without a new release of the code.
"""
from .settings import get_settings

MINUTES_PER_DAY = 24 * 60


def calculate_price(minutes: int, price_per_minute: float | None = None,
                    daily_cap: float | None = None) -> float:
    """€0.25 per started minute, never more than €12 per day (values of config.yaml).

    The cap applies PER DAY: every complete day of 24 h costs DAILY_CAP, and the
    remaining minutes are charged PRICE_PER_MINUTE each, again capped at DAILY_CAP.
      - 40 min        -> 10.00
      - 100 min       -> 12.00  (capped)
      - 24 h + 1 min  -> 12.00 + 0.25 = 12.25
      - 2 days + 2 h  -> 2 x 12 + min(120 x 0.25, 12) = 36.00
    """
    if minutes < 0:
        raise ValueError("minutes must be >= 0")
    settings = get_settings()
    per_minute = settings.PRICE_PER_MINUTE if price_per_minute is None else price_per_minute
    cap = settings.DAILY_CAP if daily_cap is None else daily_cap
    full_days, remaining_minutes = divmod(minutes, MINUTES_PER_DAY)
    last_day = min(remaining_minutes * per_minute, cap)
    return round(full_days * cap + last_day, 2)
