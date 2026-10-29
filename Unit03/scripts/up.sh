#!/usr/bin/env bash
# ./scripts/up.sh <dev|staging|prod> : start ONE environment and wait until healthy
source "$(dirname "$0")/_env.sh" "${1:-dev}"
"${COMPOSE[@]}" up -d --build --wait
echo "$ENV_NAME is up: http://localhost:${API_HOST_PORT}/health"
