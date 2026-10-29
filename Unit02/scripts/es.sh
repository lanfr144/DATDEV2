#!/usr/bin/env bash
# es.sh METHOD PATH [JSON file]  -> curl to Elasticsearch, run INSIDE the
# elasticsearch container (the CA certificate is there; no -k needed).
# The password comes from .env, it never appears in the command history.
source "$(dirname "$0")/_env.sh"
method=$1 path=$2 body=${3:-}
args=(-sS --cacert config/certs/ca/ca.crt -u "elastic:${ELASTIC_PASSWORD}" -X "$method"
      "https://localhost:${ES_PORT}${path}")
if [ -n "$body" ]; then
  docker compose exec -T elasticsearch curl "${args[@]}" -H 'Content-Type: application/json' -d @- < "$body"
else
  docker compose exec -T elasticsearch curl "${args[@]}"
fi
