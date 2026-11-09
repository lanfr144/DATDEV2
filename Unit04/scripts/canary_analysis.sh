#!/usr/bin/env bash
# =============================================================================
# Canary analysis: N rentals (start + stop) through the gateway, then the error
# rate PER VERSION, read from the X-App-Version header of each answer.
# Threshold (course: "the threshold at which you would stop the rollout"):
#   error rate of the canary > MAX_ERROR_RATE (default 5 %) -> exit 1 = roll back
#   ./scripts/canary_analysis.sh [requests=40]
# A second source confirms it: the JSON logs in MongoDB (errors per version).
# =============================================================================
source "$(dirname "$0")/_env.sh"
N=${1:-40}; MAX=${MAX_ERROR_RATE:-0.05}
GW="http://localhost:${GATEWAY_PORT}"
rc=0
python3 - "$GW" "$API_KEY_USER1" "$N" "$MAX" <<'PY' || rc=$?   # keep going: show the logs too
import collections, json, sys, time, urllib.request, urllib.error
gw, key, n, max_rate = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])

def call(path, body):
    req = urllib.request.Request(gw + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"X-API-Key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers.get("X-App-Version"), json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("X-App-Version"), {}

stats = collections.defaultdict(lambda: [0, 0])          # version -> [requests, 5xx]
rejected = 0
for i in range(n):
    code, version, body = call("/rentals/start", {"bike_id": f"BIKE-{int(time.time()*1000) % 10**6}{i:03d}"})
    if code != 201:
        continue
    code, version, _ = call("/rentals/stop", {"rental_id": body["rental_id"]})
    if version is None:          # answered by the GATEWAY (429 rate limit, 502...), not by a release
        rejected += 1
        continue
    stats[version][0] += 1
    stats[version][1] += code >= 500
    time.sleep(0.25)             # 2 requests per loop -> ~8 r/s: under the rate limit (10 r/s)
worst = 0.0
for version, (total, errors) in sorted(stats.items()):
    rate = errors / total
    worst = max(worst, rate)
    print(f"  version {version}: {total:3d} stops, {errors:2d} errors -> error rate {rate:.0%}")
if rejected:
    print(f"  {rejected} answers came from the gateway itself (no X-App-Version): not counted")
if sum(total for total, _ in stats.values()) < n // 2:      # too few answers: cannot judge
    print("  not enough answers from the releases: ROLLBACK (no data = no promotion)")
    sys.exit(1)
verdict = "OK, continue the rollout" if worst <= max_rate else "ROLLBACK (error rate above threshold)"
print(f"  threshold {max_rate:.0%}: {verdict}")
sys.exit(0 if worst <= max_rate else 1)
PY
record canary_analysis "$([ $rc = 0 ] && echo ok || echo failed)"     # input of the DORA metrics
echo "  MongoDB logs, HTTP 5xx per version (last 10 min):"
"${COMPOSE[@]}" exec -T logs mongosh --quiet -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" \
  --authenticationDatabase admin logs_prod --eval '
  db.logs.aggregate([
    { $match: { service: "rentals", status: { $gte: 500 }, timestamp: { $gte: new Date(Date.now() - 600000) } } },
    { $group: { _id: "$version", errors: { $sum: 1 } } }, { $sort: { _id: 1 } } ])
  .forEach(r => print(`    ${r._id}: ${r.errors}`))'
exit $rc
