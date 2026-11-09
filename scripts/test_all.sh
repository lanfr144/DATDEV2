#!/usr/bin/env bash
# =============================================================================
# DATDEV2 - run EVERYTHING, Unit after Unit, and write one log:
#   1. unit tests of every service in a clean python:3.12 container (no Python
#      needed on the host, the sources are mounted read-only)
#   2. each Unit with Docker Compose: up --wait, smoke tests, extra demos, down
#      (volumes are kept: data survives, like `docker compose down` in the course)
#   ./scripts/test_all.sh            # from WSL or Git Bash, Docker Desktop running
#   ./scripts/test_all.sh 04 05      # only some Units
# Output: logs/test_all.log (+ the summary at the end). Exit 1 if anything failed.
# =============================================================================
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs
LOG="$ROOT/logs/test_all.log"
UNITS=("${@:-01 02 03 04 05}"); [ $# -eq 0 ] && UNITS=(01 02 03 04 05)
: > "$LOG"
summary=()
step() {   # step <label> <command...> : run, log, remember OK/FAIL
  local label="$1"; shift
  echo -e "\n########## $label ($(date +%T))" | tee -a "$LOG"
  if "$@" >> "$LOG" 2>&1; then summary+=("OK   $label"); echo "OK   $label"
  else summary+=("FAIL $label"); echo "FAIL $label (see $LOG)"; fi
}
pytest_in_docker() {   # pytest_in_docker <UnitXX/service> [command]
  # The WHOLE Unit is mounted (some tests read ../mongo/logs.ndjson) and copied,
  # so nothing is written into the OneDrive folder.
  # "python -m pytest" (not "pytest"): puts the current folder on sys.path, so
  # the tests can `import app` exactly as when run from the service folder
  docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v datdev2-pip-cache:/root/.cache/pip \
    -v "$ROOT/${1%%/*}":/src:ro python:3.12-slim sh -c \
    "cp -r /src /w && cd /w/${1#*/} && pip install -q --root-user-action=ignore -r requirements.txt && ${2:-python -m pytest -q -p no:cacheprovider}"
}
for f in Unit0*/.env.example; do d=$(dirname "$f"); [ -f "$d/.env" ] || cp "$f" "$d/.env"; done
for e in dev staging prod; do [ -f "Unit03/.env.$e" ] || cp "Unit03/.env.$e.example" "Unit03/.env.$e"; done

for u in "${UNITS[@]}"; do case "$u" in
01)
  step "U01 unit tests (api)" pytest_in_docker Unit01/api
  step "U01 compose up"       bash -c "cd Unit01 && docker compose up -d --build --wait"
  step "U01 smoke test"       Unit01/scripts/smoke_test.sh
  step "U01 mongosh queries"  Unit01/scripts/run_queries.sh
  step "U01 gRPC demo"        Unit01/scripts/grpc_demo.sh
  step "U01 down"             bash -c "cd Unit01 && docker compose --profile grpc down" ;;
02)
  step "U02 unit tests (FastAPI)" pytest_in_docker Unit02/api
  step "U02 unit tests (Django)"  pytest_in_docker Unit02/django-books "python manage.py test -v 1"
  step "U02 compose up"       bash -c "cd Unit02 && docker compose up -d --build --wait"
  step "U02 smoke test"       Unit02/scripts/smoke_test.sh
  step "U02 Django lab views" bash -c 'cd Unit02 && . ./.env && curl -sf http://localhost:${DJANGO_HOST_PORT}/hello/ && curl -sf "http://localhost:${DJANGO_HOST_PORT}/v1/books/?search=a" >/dev/null'
  step "U02 down (password)"  bash -c "cd Unit02 && docker compose down"
  step "U02 Kibana with service-account token" bash -c "cd Unit02 && docker compose -f docker-compose.yml -f docker-compose.token.yml up -d --build --wait \
        && docker compose logs es-init | grep -q 'service-account token' && ./scripts/smoke_test.sh"
  step "U02 down (token)"     bash -c "cd Unit02 && docker compose -f docker-compose.yml -f docker-compose.token.yml down" ;;
03)
  step "U03 unit tests"       pytest_in_docker Unit03/api
  step "U03 3 environments up" bash -c "cd Unit03 && for e in dev staging prod; do ./scripts/up.sh \$e || exit 1; done"
  step "U03 smoke test"       Unit03/scripts/smoke_test.sh
  step "U03 down"             bash -c "cd Unit03 && for e in dev staging prod; do ./scripts/down.sh \$e; done" ;;
04)
  step "U04 unit tests (books)"   pytest_in_docker Unit04/books-service
  step "U04 unit tests (rentals)" pytest_in_docker Unit04/rentals-service
  # images of the release scenario are rebuilt from the CURRENT code
  docker image rm datdev2/rentals:1.1.0 datdev2/rentals:2.0.0 datdev2/rentals:2.0.1 datdev2/rentals:2.0.2 >/dev/null 2>&1
  cp Unit04/release.env /tmp/datdev2-release.env.bak
  step "U04 compose up"       Unit04/scripts/compose.sh up -d --build --wait
  step "U04 smoke test"       Unit04/scripts/smoke_test.sh
  step "U04 HTTPS + redirect" Unit04/scripts/https_check.sh
  step "U04 release scenario + DORA" bash -c "Unit04/scripts/release_demo.sh && grep -q 'Change failure rate' Unit04/docs/release_demo_output.txt"
  step "U04 down"             Unit04/scripts/compose.sh down
  cp /tmp/datdev2-release.env.bak Unit04/release.env; rm -f Unit04/.release.previous ;;  # back to the versioned start state
05)
  step "U05 keys + certificate" Unit05/scripts/make_keys.sh
  step "U05 package (wheel)"  Unit05/scripts/package_check.sh
  step "U05 compose up"       bash -c "cd Unit05 && docker compose up -d --build --wait"
  step "U05 smoke test"       Unit05/scripts/smoke_test.sh
  step "U05 down"             bash -c "cd Unit05 && docker compose down" ;;
esac; done

echo -e "\n========== SUMMARY ($(date '+%F %T'))" | tee -a "$LOG"
printf '%s\n' "${summary[@]}" | tee -a "$LOG"
! printf '%s\n' "${summary[@]}" | grep -q '^FAIL'
