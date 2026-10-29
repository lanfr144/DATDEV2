#!/usr/bin/env bash
# =============================================================================
# Unit 04 - end-to-end test through the gateway (./scripts/compose.sh up -d --wait)
# Gateway features (DATOP2 U04) + release observability (DEVOP2 U04). Exit 1 on failure.
# =============================================================================
source "$(dirname "$0")/_env.sh"
set +e
GW="http://localhost:${GATEWAY_PORT}"
K1=(-H "X-API-Key: ${API_KEY_USER1}"); K2=(-H "X-API-Key: ${API_KEY_USER2}"); J=(-H 'Content-Type: application/json')
fail=0
check() { if [ "$2" = "$3" ]; then echo "OK   $1 ($3)"; else echo "FAIL $1: expected $2, got $3"; fail=1; fi; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
json() { python3 -c "import json,sys;d=json.load(sys.stdin);print($1)"; }

check "gateway /health"                   200 "$(code "$GW/health")"
check "GET /books (public)"               200 "$(code "$GW/books")"
ISBN="978-$(date +%s)$((RANDOM % 9))"
BOOK="{\"title\":\"Gateway test\",\"author\":\"CI\",\"year\":2026,\"isbn\":\"$ISBN\",\"price\":3}"
check "POST /books without key"           401 "$(code -X POST "$GW/books" "${J[@]}" -d "$BOOK")"
check "POST /books with key"              201 "$(code -X POST "$GW/books" "${J[@]}" "${K1[@]}" -d "$BOOK")"
check "/rentals without key"              401 "$(code "$GW/rentals")"
R=$(curl -s -D - -X POST "$GW/rentals/start" "${J[@]}" "${K1[@]}" -H 'X-User-Id: 2' -d "{\"bike_id\":\"BIKE-$RANDOM$RANDOM\"}")
check "start: 201 + Location"             yes "$(echo "$R" | grep -qi '^location: /rentals/' && echo yes || echo no)"
RID=$(echo "$R" | tail -1 | json 'd["rental_id"]')
check "spoofed X-User-Id ignored (user 1)" 1  "$(echo "$R" | tail -1 | json 'd["user_id"]')"
check "user 2 cannot read it"             404 "$(code "${K2[@]}" "$GW/rentals/$RID")"
check "answer says which release"         yes "$(curl -s -D - -o /dev/null "${K1[@]}" "$GW/rentals/$RID" | grep -qi '^x-app-version: [0-9]' && echo yes || echo no)"
check "unknown route -> JSON 404"         '{"detail":"Unknown route"}' "$(curl -s "$GW/nothing")"
check "rentals not published on the host" no "$("${COMPOSE[@]}" ps rentals-blue rentals-green --format '{{.Ports}}' | grep -q -- '->' && echo yes || echo no)"
codes=$(for i in $(seq 40); do curl -s -o /dev/null -w '%{http_code}\n' "$GW/books/health" & done; wait)
check "rate limit -> some 429"            yes "$(echo "$codes" | grep -q 429 && echo yes || echo no)"
sleep 2
check "429 has Retry-After"               yes "$(for i in $(seq 40); do curl -s -D - -o /dev/null "$GW/books/health" & done | grep -qi '^retry-after: 1' && echo yes; wait)"
sleep 2
UP=$(curl -s "http://localhost:${PROMETHEUS_HOST_PORT}/api/v1/query?query=up%7Bjob%3D%22rentals%22%7D" | json 'sum(int(r["value"][1]) for r in d["data"]["result"])')
check "Prometheus scrapes blue + green"   2 "$UP"
N=$("${COMPOSE[@]}" exec -T logs mongosh --quiet -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin logs_prod --eval 'db.logs.countDocuments({service: {$in: ["books", "rentals"]}, version: {$exists: true}})')
check "JSON logs with version in MongoDB" yes "$([ "${N:-0}" -gt 0 ] && echo yes || echo no)"
exit $fail
