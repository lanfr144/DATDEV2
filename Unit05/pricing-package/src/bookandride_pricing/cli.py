"""Entry point declared in pyproject.toml ([project.scripts])."""
import sys

from . import __version__, calculate_price


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print(f"bookandride-price {__version__}\nusage: bookandride-price <minutes>")
        return 2
    print(f"{calculate_price(int(sys.argv[1])):.2f}")
    return 0
