#!/usr/bin/env bash
# =============================================================================
# DEVOP2 Unit 03 - exercise 3 deliverable: "terminal output demonstrating three
# runs (dev, staging, prod) with different values".
# Runs `python -m app.settings` in the SAME image with the 3 configurations,
# and saves the output in docs/terminal_output_3_envs.txt.
# Then shows the guard rails: unknown environment, DEBUG forced in prod.
# =============================================================================
source "$(dirname "$0")/_env.sh" dev
IMAGE="datdev2/bookandride:${APP_VERSION}"
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker build -q -t "$IMAGE" api >/dev/null
OUT=docs/terminal_output_3_envs.txt
{
  for env in dev staging prod; do
    echo "\$ APP_ENV=$env python -m app.settings"
    docker run --rm --env-file ".env.$env" "$IMAGE" python -m app.settings 2>&1
    echo
  done
  echo "\$ APP_ENV=qa python -m app.settings          # unknown environment"
  docker run --rm --env-file .env.dev -e APP_ENV=qa "$IMAGE" python -m app.settings 2>&1 | tail -1 || true   # expected failure
  echo
  echo "\$ APP_ENV=prod DEBUG=true python -m app.settings   # forbidden in prod"
  docker run --rm --env-file .env.prod -e DEBUG=true "$IMAGE" python -m app.settings 2>&1 | tail -1 || true   # expected failure
} | tee "$OUT"
echo "(saved in $OUT)"
