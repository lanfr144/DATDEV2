#!/usr/bin/env bash
# Usage: source scripts/_env.sh <dev|staging|prod>
# Loads .env (common) then .env.<env> (secrets + ports) and prepares COMPOSE.
set -euo pipefail
UNIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$UNIT_DIR"
ENV_NAME=${1:-dev}
case "$ENV_NAME" in dev|staging|prod) ;; *) echo "environment must be dev, staging or prod"; exit 2;; esac
for f in .env ".env.$ENV_NAME"; do
  [ -f "$f" ] || { echo "missing $f: cp $f.example $f and set the secrets"; exit 1; }
done
set -a; . ./.env; . "./.env.$ENV_NAME"; set +a
COMPOSE=(docker compose --env-file .env --env-file ".env.$ENV_NAME")
