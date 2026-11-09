"""bookandride_pricing: __init__.py turns the folder into a PACKAGE and defines
its public API (what `from bookandride_pricing import ...` gives)."""
from importlib.metadata import PackageNotFoundError, version

from .core import DAILY_CAP, PRICE_PER_MINUTE, calculate_price

try:
    __version__ = version("bookandride-pricing")   # read from the installed metadata (pyproject)
except PackageNotFoundError:                      # running from the sources, not installed
    __version__ = "0.0.0"

__all__ = ["calculate_price", "PRICE_PER_MINUTE", "DAILY_CAP", "__version__"]
