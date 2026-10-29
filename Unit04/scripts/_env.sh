#!/usr/bin/env bash
# Loads .env (secrets, ports) + release.env (release state) and defines COMPOSE.
set -euo pipefail
UNIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$UNIT_DIR"
[ -f .env ] || { echo "No .env: run  cp .env.example .env  and set the secrets"; exit 1; }
set -a; . ./.env; . ./release.env; set +a
COMPOSE=(docker compose --env-file .env --env-file release.env)
