#!/usr/bin/env bash
# Loads .env (secrets, ports) + release.env (release state) and defines COMPOSE.
set -euo pipefail
UNIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$UNIT_DIR"
[ -f .env ] || { echo "No .env: run  cp .env.example .env  and set the secrets"; exit 1; }
set -a; . ./.env; . ./release.env; set +a
COMPOSE=(docker compose --env-file .env --env-file release.env)

# DORA metrics (DEVOP2 U04a §6): every release action appends ONE JSON line to
# docs/release_history.ndjson (who receives the traffic AFTER the action).
# scripts/dora_metrics.py computes the four indicators from this history.
HISTORY="$UNIT_DIR/docs/release_history.ndjson"
record() {   # record <event> [detail]
  printf '{"ts":"%s","event":"%s","mode":"%s","active":"%s","canary":"%s","percent":%s,"blue":"%s","green":"%s","detail":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)" "$1" "${RELEASE_MODE:-}" "${ACTIVE_COLOR:-}" "${CANARY_COLOR:-}" \
    "${CANARY_PERCENT:-0}" "${BLUE_VERSION:-}" "${GREEN_VERSION:-}" "${2:-}" >> "$HISTORY"
}
