"""
Release information of THIS running instance (DEVOP2 Unit 04, semantic versioning).

APP_VERSION is baked into the image at build time (build arg -> ENV), so an
image tag = one immutable version: datdev2/rentals:1.1.0 is always 1.1.0.

In a real project each version is a Git tag and the code differs between tags.
To keep ONE codebase for the lab, the changes of each version are switched on
by the version number (feature flags tied to the version):

    1.0.0  initial release (extracted from the Unit 03 monolith)
    1.1.0  MINOR: new optional field "price_detail" in POST /rentals/stop
           -> backward compatible: old clients ignore the extra field
    2.0.0  MAJOR: "price_eur" (float) REPLACED by "price_cents" (int)
           -> breaking: a client that reads price_eur crashes

COLOR (blue / green) only says on which slot the instance runs; FAULT_RATE
injects errors to simulate a bad release (canary that must be rolled back).
"""
import os

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
COLOR = os.getenv("COLOR", "blue")
FAULT_RATE = float(os.getenv("FAULT_RATE", "0"))      # 0.3 = 30 % of the stops fail


def version_tuple(version: str = APP_VERSION) -> tuple[int, int, int]:
    major, minor, patch = (int(x) for x in version.split("."))
    return major, minor, patch


FEATURES = {
    "price_detail": version_tuple() >= (1, 1, 0),
    "price_cents": version_tuple() >= (2, 0, 0),
}
