#!/usr/bin/env bash
# =============================================================================
# Unit 02 - end-to-end test of the running stack (docker compose up -d --wait)
# FastAPI + Django + MongoDB + shipper + Elasticsearch + Kibana. Exit 1 on failure.
# =============================================================================
source "$(dirname "$0")/_env.sh"
API="http://localhost:${API_HOST_PORT}"
DJ="http://localhost:${DJANGO_HOST_PORT}"
KB="http://localhost:${KIBANA_HOST_PORT}"
fail=0
check() { if [ "$2" = "$3" ]; then echo "OK   $1 ($3)"; else echo "FAIL $1: expected $2, got $3"; fail=1; fi; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
json() { python3 -c "import json,sys;d=json.load(sys.stdin);print($1)"; }

check "FastAPI /health"                 200 "$(code "$API/health")"
check "search engine of the API"        elasticsearch "$(curl -s "$API/health" | json 'd["search_engine"]')"
check "Django /health/"                 200 "$(code "$DJ/health/")"
ISBN="978-$(date +%s)$((RANDOM % 9))"
BODY="{\"title\":\"Smoke test of the shipper\",\"author\":\"Ci Bot\",\"year\":2026,\"isbn\":\"$ISBN\",\"price\":1.5}"
check "POST /books (valid)"             201 "$(code -X POST "$API/books" -H 'Content-Type: application/json' -H 'X-User-Id: smoke' -d "$BODY")"
check "POST /books price=0 (FastAPI)"   422 "$(code -X POST "$API/books" -H 'Content-Type: application/json' -d "${BODY/1.5/0}")"
check "POST /books/ year=2999 (Django)" 400 "$(code -X POST "$DJ/books/" -H 'Content-Type: application/json' -d "${BODY/2026/2999}")"
check "GET /books/not-an-id"            422 "$(code "$API/books/not-an-id")"
sleep 2   # ES refresh (1 s) + BackgroundTask
check "full-text search in ES"          elasticsearch "$(curl -s "$API/books/search?q=shiper%20smoke" | json 'd["engine"]')"
check "fuzzy hit 'shiper' -> shipper"   yes "$(curl -s "$API/books/search?q=shiper%20smoke" | grep -q "$ISBN" && echo yes || echo no)"
check "logs-demo holds 16 documents"    16 "$(./scripts/es.sh GET /logs-demo/_count | json 'd["count"]')"
sleep "$(( SHIP_INTERVAL + 2 ))"   # one cycle of the shipper
check "API log shipped to ES"           yes "$(./scripts/es.sh GET "/${LOGS_INDEX}/_search?q=user_id:smoke" | json '"yes" if d["hits"]["total"]["value"] > 0 else "no"')"
check "Django log shipped to ES"        yes "$(./scripts/es.sh GET "/${LOGS_INDEX}/_search?q=service:books-django" | json '"yes" if d["hits"]["total"]["value"] > 0 else "no"')"
check "Kibana dashboard exists"         200 "$(code -u "elastic:${ELASTIC_PASSWORD}" "$KB/api/saved_objects/dashboard/bookandride-dashboard")"
exit $fail
