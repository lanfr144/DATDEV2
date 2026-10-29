#!/usr/bin/env bash
# Runs the three queries of the course (mongo/queries.js) inside the container.
# The password is read from .env and never typed on the command line by hand.
source "$(dirname "$0")/_env.sh"
docker compose exec -T -e MONGO_DB="$MONGO_DB" mongo mongosh --quiet --port "$MONGO_PORT" \
  -u "$MONGO_ROOT_USER" -p "$MONGO_ROOT_PASSWORD" --authenticationDatabase admin \
  /scripts/queries.js
