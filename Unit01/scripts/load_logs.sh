#!/usr/bin/env bash
# Loads (again) mongo/logs.ndjson into MongoDB - idempotent, no duplicates.
# Useful when the volume already existed before the seed script was added.
source "$(dirname "$0")/_env.sh"
docker compose exec -T mongo mongosh --quiet --port "$MONGO_PORT" \
  -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin \
  /docker-entrypoint-initdb.d/01-seed-logs.js
