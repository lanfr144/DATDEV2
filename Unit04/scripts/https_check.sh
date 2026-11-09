#!/usr/bin/env bash
# =============================================================================
# Unit 04 - HTTP -> HTTPS redirect (DEVOP2 U11 sheet 22, done by the gateway).
# Recreates the gateway with GATEWAY_FORCE_HTTPS=true, checks the 301, then
# puts the normal setting back. Shows the certificate as a client sees it.
#   ./scripts/https_check.sh
# =============================================================================
source "$(dirname "$0")/_env.sh"
fail=0
check() { if [ "$2" = "$3" ]; then echo "OK   $1 ($3)"; else echo "FAIL $1: expected $2, got $3"; fail=1; fi; }
echo "certificate presented by the gateway:"
echo | openssl s_client -connect "localhost:${GATEWAY_TLS_PORT}" -servername localhost 2>/dev/null \
  | openssl x509 -noout -subject -issuer -enddate | sed 's/^/  /'
GATEWAY_FORCE_HTTPS=true "${COMPOSE[@]}" up -d --no-deps --wait gateway >/dev/null 2>&1
H=$(curl -s -o /dev/null -D - "http://localhost:${GATEWAY_PORT}/books")
check "HTTP /books -> 301"                 yes "$(echo "$H" | grep -q '^HTTP/1.1 301' && echo yes || echo no)"
check "Location = https://...:${GATEWAY_TLS_PORT}/books" yes \
  "$(echo "$H" | grep -qi "^location: https://localhost:${GATEWAY_TLS_PORT}/books" && echo yes || echo no)"
check "HTTP /health NOT redirected"        200 "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${GATEWAY_PORT}/health")"
check "curl -L follows to HTTPS"           200 "$(curl -s -L --cacert gateway/certs/gateway.crt -o /dev/null -w '%{http_code}' "http://localhost:${GATEWAY_PORT}/books")"
"${COMPOSE[@]}" up -d --no-deps --wait gateway >/dev/null 2>&1     # back to GATEWAY_FORCE_HTTPS from .env
exit $fail
