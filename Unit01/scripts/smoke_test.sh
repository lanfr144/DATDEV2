#!/usr/bin/env bash
# =============================================================================
# Unit 01 - end-to-end test of the running stack (docker compose up -d --wait)
# Checks the HTTP status codes and the three log queries; exit code 1 on failure.
# =============================================================================
source "$(dirname "$0")/_env.sh"
API="http://localhost:${API_HOST_PORT}"
fail=0
check() {  # check <description> <expected> <actual>
  if [ "$2" = "$3" ]; then echo "OK   $1 ($3)"; else echo "FAIL $1: expected $2, got $3"; fail=1; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }

check "GET /health"                200 "$(code "$API/health")"
check "mongo-express /status"      200 "$(code "http://localhost:${EXPRESS_HOST_PORT}/status")"
ISBN="999-$(date +%s)"
LOC=$(curl -s -D - -o /dev/null -X POST "$API/books" -H 'Content-Type: application/json' \
      -d "{\"title\":\"Smoke\",\"author\":\"Test\",\"year\":2026,\"isbn\":\"$ISBN\"}" \
      | tr -d '\r' | awk -F': ' 'tolower($1)=="location"{print $2}')
check "POST /books -> Location"    yes "$([ -n "$LOC" ] && echo yes || echo no)"
check "POST same ISBN"             409 "$(code -X POST "$API/books" -H 'Content-Type: application/json' -d "{\"title\":\"S\",\"author\":\"T\",\"year\":2026,\"isbn\":\"$ISBN\"}")"
check "POST invalid body"          422 "$(code -X POST "$API/books" -H 'Content-Type: application/json' -d '{"title":"x"}')"
check "DELETE $LOC"                204 "$(code -X DELETE "$API$LOC")"
check "GET deleted book"           404 "$(code "$API$LOC")"
Q1=$(curl -s "$API/logs/stats?now=2025-09-18T10:00:00Z" | python3 -c 'import json,sys;print(json.load(sys.stdin)["q1_errors_last_hours"]["count"])')
check "Q1 ERRORs in the last 24 h" 3 "$Q1"
check "API logs stored in MongoDB" yes "$(curl -s "$API/logs?service=books-api&limit=1" | grep -q books-api && echo yes || echo no)"
exit $fail
