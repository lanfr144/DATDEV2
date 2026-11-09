#!/usr/bin/env bash
# =============================================================================
# Book&Ride - Unit 04 - full release scenario (DEVOP2 Unit 04b parts 1-4, real
# traffic instead of folders). Output saved in docs/release_demo_output.txt.
#
#   1. MINOR 1.1.0 with blue/green: deploy on green, test, switch, roll back, switch again
#   2. MAJOR 2.0.0 with a canary: the release is BAD (30 % errors) -> analysis -> rollback
#   3. PATCH 2.0.1 = the fix (2.0.0 is never re-tagged): canary OK -> promote
#   4. PATCH 2.0.2 with a rolling update: one slot after the other, no downtime
# Starts from: blue 1.0.0 active (./scripts/release.sh status)
# =============================================================================
source "$(dirname "$0")/_env.sh"
R=./scripts/release.sh
GW="http://localhost:${GATEWAY_PORT}"
rent() {   # one rental through the gateway: which version answered, with which fields
  local rid
  rid=$(curl -s -X POST "$GW/rentals/start" -H "X-API-Key: $API_KEY_USER1" -H 'Content-Type: application/json' \
        -d "{\"bike_id\":\"BIKE-$RANDOM$RANDOM\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["rental_id"])')
  curl -s -D /tmp/h.$$ -X POST "$GW/rentals/stop" -H "X-API-Key: $API_KEY_USER1" -H 'Content-Type: application/json' \
       -d "{\"rental_id\":$rid}" | python3 -c "
import json,sys; b=json.load(sys.stdin)
v=[l.split(': ')[1].strip() for l in open('/tmp/h.$$') if l.lower().startswith('x-app-version')]
print(f'  client sees version {v[0] if v else \"?\"}: fields {sorted(k for k in b if k.startswith(\"price\"))}')"
  rm -f /tmp/h.$$
}
step() { echo; echo "### $*"; }
: > "$HISTORY"                               # fresh history for the DORA metrics
{
step "0. initial state";                     record initial; $R status
step "1. MINOR 1.1.0 (new optional field) - blue/green"
$R deploy green 1.1.0
$R switch green;                              rent
echo "  -> problem reported? instant rollback = switch back to blue (still running 1.0.0)"
$R switch blue;                               rent
$R switch green;                              rent
step "2. MAJOR 2.0.0 (price_eur -> price_cents) - canary, BAD release"
$R deploy blue 2.0.0                          # blue is idle now
$R fault blue 0.3                             # simulated defect of this release
$R canary 30
./scripts/canary_analysis.sh 40 || { echo "  -> canary above threshold: ROLLBACK"; $R switch green; }
step "3. PATCH 2.0.1 (the fix; 2.0.0 is NOT re-tagged) - canary OK, promote"
$R deploy blue 2.0.1
$R canary 30
./scripts/canary_analysis.sh 40 && $R promote
rent
step "4. PATCH 2.0.2 - rolling update (blue, check, then green)"
$R rolling 2.0.2
rent; rent
step "final state";                           $R status
step "5. DORA metrics of this scenario (scripts/dora_metrics.py)"
python3 scripts/dora_metrics.py
} 2>&1 | tee docs/release_demo_output.txt
