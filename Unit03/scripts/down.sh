#!/usr/bin/env bash
# ./scripts/down.sh <dev|staging|prod> [-v] : stop one environment (-v deletes its data)
source "$(dirname "$0")/_env.sh" "${1:-dev}"
shift || true
"${COMPOSE[@]}" down "$@"
