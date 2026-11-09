#!/usr/bin/env bash
# Unit 05 - build the wheel of bookandride-pricing and test the INSTALLED wheel
# in a clean image (DEVOP2 U07). No Python needed on the host.
set -euo pipefail
cd "$(dirname "$0")/../pricing-package"
docker build -q -t datdev2/bookandride-pricing:1.0.0 . >/dev/null
docker run --rm datdev2/bookandride-pricing:1.0.0
