#!/usr/bin/env bash
# =============================================================================
# Unit 03 - end-to-end test of the 3 environments (./scripts/up.sh dev|staging|prod)
# Same image everywhere; checks what MUST differ between dev, staging and prod.
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
check() { if [ "$2" = "$3" ]; then echo "OK   $1 ($3)"; else echo "FAIL $1: expected $2, got $3"; fail=1; fi; }
code() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
val() { grep "^$2=" ".env.$1" | cut -d= -f2-; }
mongo_count() {  # mongo_count <env> <filter>  -> number of logs of that environment
  docker compose --env-file .env --env-file ".env.$1" exec -T logs mongosh --quiet \
    -u admin -p "$(val "$1" MONGO_ROOT_PASSWORD)" --authenticationDatabase admin \
    "logs_$1" --eval "db.logs.countDocuments($2)"
}

for env in dev staging prod; do
  API="http://localhost:$(val $env API_HOST_PORT)"
  KEY=$(val $env API_KEY)
  echo "--- $env ($API)"
  check "$env /health env"           "$env" "$(curl -s "$API/health" | python3 -c 'import json,sys;print(json.load(sys.stdin)["env"])')"
  ISBN="978-$(date +%s)$((RANDOM % 9))"
  BODY="{\"title\":\"T\",\"author\":\"A\",\"year\":2020,\"isbn\":\"$ISBN\",\"price\":5}"
  check "$env POST /books no key"    401 "$(code -X POST "$API/books" -H 'Content-Type: application/json' -d "$BODY")"
  check "$env POST /books own key"   201 "$(code -X POST "$API/books" -H 'Content-Type: application/json' -H "X-API-Key: $KEY" -d "$BODY")"
  RID=$(curl -s -X POST "$API/rentals/start" -H 'Content-Type: application/json' -d "{\"bike_id\":\"BIKE-$RANDOM\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["rental_id"])')
  check "$env rental price (config)" 0.25 "$(curl -s -X POST "$API/rentals/stop" -H 'Content-Type: application/json' -d "{\"rental_id\":$RID}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["price_eur"])')"
done

echo "--- differences between environments"
check "dev key refused in prod"      401 "$(code -X POST "http://localhost:$(val prod API_HOST_PORT)/books" -H "X-API-Key: $(val dev API_KEY)" -H 'Content-Type: application/json' -d '{}')"
check "/docs in staging"             200 "$(code "http://localhost:$(val staging API_HOST_PORT)/docs")"
check "/docs in prod (disabled)"     404 "$(code "http://localhost:$(val prod API_HOST_PORT)/docs")"
check "/config in prod (disabled)"   404 "$(code "http://localhost:$(val prod API_HOST_PORT)/config")"
check "dev logs INFO (LOG_LEVEL=DEBUG)"  yes "$([ "$(mongo_count dev '{level:"INFO", env:"dev"}')" -gt 0 ] && echo yes || echo no)"
check "prod logs no INFO (LOG_LEVEL=WARNING)" 0 "$(mongo_count prod '{level:"INFO"}')"
check "prod logs the 401 (WARN)"     yes "$([ "$(mongo_count prod '{level:"WARN", status:401}')" -gt 0 ] && echo yes || echo no)"
check "no dev log in prod database"  0 "$(mongo_count prod '{env:"dev"}')"
exit $fail
