"""Business rule (unchanged since Unit 03): €0.25/started minute, cap €12 per day."""
import os

PRICE_PER_MINUTE = float(os.getenv("PRICE_PER_MINUTE", "0.25"))
DAILY_CAP = float(os.getenv("DAILY_CAP", "12.0"))
MINUTES_PER_DAY = 24 * 60


def calculate_price(minutes: int) -> float:
    """40 min -> 10.00 · 100 min -> 12.00 · 24 h + 1 min -> 12.25 · 2 days + 2 h -> 36.00"""
    if minutes < 0:
        raise ValueError("minutes must be >= 0")
    full_days, remaining_minutes = divmod(minutes, MINUTES_PER_DAY)
    last_day = min(remaining_minutes * PRICE_PER_MINUTE, DAILY_CAP)
    return round(full_days * DAILY_CAP + last_day, 2)


def price_detail(minutes: int) -> dict:
    """Version 1.1.0: how the price was computed (shown to the customer)."""
    full_days, remaining_minutes = divmod(minutes, MINUTES_PER_DAY)
    return {"full_days": full_days, "remaining_minutes": remaining_minutes,
            "price_per_minute": PRICE_PER_MINUTE, "daily_cap": DAILY_CAP,
            "capped": remaining_minutes * PRICE_PER_MINUTE > DAILY_CAP}
