#!/usr/bin/env bash
# docker compose with the two env files:  ./scripts/compose.sh up -d --build --wait
source "$(dirname "$0")/_env.sh"
exec "${COMPOSE[@]}" "$@"
