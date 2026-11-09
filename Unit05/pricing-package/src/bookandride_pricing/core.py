"""The business rule, without FastAPI, database or configuration: easy to test
and to reuse in the monolith (U03), the rentals service (U04) or a batch job."""

PRICE_PER_MINUTE = 0.25
DAILY_CAP = 12.0
MINUTES_PER_DAY = 24 * 60


def calculate_price(minutes: int, price_per_minute: float = PRICE_PER_MINUTE,
                    daily_cap: float = DAILY_CAP) -> float:
    """EUR 0.25 per started minute, at most EUR 12 per day of 24 h."""
    if minutes < 0:
        raise ValueError("minutes must be >= 0")
    full_days, remaining = divmod(minutes, MINUTES_PER_DAY)
    return round(full_days * daily_cap + min(remaining * price_per_minute, daily_cap), 2)
