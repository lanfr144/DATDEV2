#!/usr/bin/env bash
# =============================================================================
# Book&Ride - Unit 04 - release tool (DEVOP2 Unit 04 strategies, for real)
# =============================================================================
#   release.sh status                     what runs where, how the traffic is split
#   release.sh deploy <color> <version>   build + start <version> on the IDLE slot
#   release.sh fault <color> <rate>       simulate a defect (0.3 = 30 % of stops fail)
#   release.sh switch <color>             blue/green: 100 % of the traffic on <color>
#   release.sh canary <percent>           canary: <percent> % on the idle slot
#   release.sh promote                    canary OK -> the canary slot gets 100 %
#   release.sh rolling <version>          rolling update: blue, check, then green
#   release.sh rollback                   restore the previous release state
#
# Every change: 1) copy release.env to .release.previous  2) edit release.env
# 3) docker compose up on the changed services only. Images are tagged with the
# version and never rebuilt for an existing tag -> rollback needs no build.
# =============================================================================
source "$(dirname "$0")/_env.sh"
GW="http://localhost:${GATEWAY_PORT}"

set_kv() { sed -i "s/^$1=.*/$1=$2/" release.env; }
save()   { cp release.env .release.previous; }
reload() { set -a; . ./release.env; set +a; }
other()  { [ "$1" = blue ] && echo green || echo blue; }
semver() { [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "version must be MAJOR.MINOR.PATCH"; exit 2; }; }
color()  { [[ "$1" =~ ^(blue|green)$ ]] || { echo "color must be blue or green"; exit 2; }; }
up_gateway() { "${COMPOSE[@]}" up -d --no-deps --wait gateway >/dev/null 2>&1; }
up_slot() {    # up_slot <color> : (re)create one slot, build only if the image tag is new
  local version_var="${1^^}_VERSION"
  if docker image inspect "datdev2/rentals:${!version_var}" >/dev/null 2>&1; then
    "${COMPOSE[@]}" up -d --no-deps --wait "rentals-$1" >/dev/null 2>&1
  else
    echo "  building image datdev2/rentals:${!version_var}"
    "${COMPOSE[@]}" up -d --no-deps --build --wait "rentals-$1" >/dev/null 2>&1
  fi
}
slot_version() { curl -s "$GW/internal/$1/rentals/version" | python3 -c 'import json,sys;print(json.load(sys.stdin)["version"])'; }

status() {
  reload
  echo "mode=$RELEASE_MODE active=$ACTIVE_COLOR canary=$CANARY_COLOR($CANARY_PERCENT%)"
  echo "  blue : $(slot_version blue) (fault rate $BLUE_FAULT_RATE)"
  echo "  green: $(slot_version green) (fault rate $GREEN_FAULT_RATE)"
}

case "${1:-status}" in
  status) status ;;

  deploy)
    color "$2"; semver "$3"
    if [ "$RELEASE_MODE" != rolling ] && [ "$2" = "$ACTIVE_COLOR" ]; then
      echo "refused: $2 is LIVE. Deploy on the idle slot ($(other "$2")), test it, then switch."; exit 1
    fi
    save; set_kv "${2^^}_VERSION" "$3"; set_kv "${2^^}_FAULT_RATE" 0; reload
    up_slot "$2"
    echo "deployed $3 on $2 (idle, no user traffic yet): $(curl -s "$GW/internal/$2/rentals/version")" ;;

  fault)
    color "$2"; save; set_kv "${2^^}_FAULT_RATE" "$3"; reload; up_slot "$2"
    echo "$2 now fails ${3} of the stops (simulated defect)" ;;

  switch)
    color "$2"
    # never send users to a slot that is not healthy
    curl -sf "$GW/internal/$2/rentals/version" >/dev/null || { echo "refused: $2 is not healthy"; exit 1; }
    save; set_kv RELEASE_MODE bluegreen; set_kv ACTIVE_COLOR "$2"; reload; up_gateway
    echo "blue/green switch: 100 % of /rentals -> $2 ($(slot_version "$2"))" ;;

  canary)
    [[ "${2:-}" =~ ^[0-9]+$ ]] && [ "$2" -ge 1 ] && [ "$2" -le 99 ] || { echo "percent must be 1-99"; exit 2; }
    save; set_kv RELEASE_MODE canary; set_kv CANARY_COLOR "$(other "$ACTIVE_COLOR")"
    set_kv CANARY_PERCENT "$2"; reload; up_gateway
    echo "canary: $2 % -> $CANARY_COLOR ($(slot_version "$CANARY_COLOR")), rest -> $ACTIVE_COLOR ($(slot_version "$ACTIVE_COLOR"))" ;;

  promote)
    [ "$RELEASE_MODE" = canary ] || { echo "nothing to promote (mode=$RELEASE_MODE)"; exit 1; }
    exec "$0" switch "$CANARY_COLOR" ;;

  rolling)
    semver "$2"; save
    set_kv RELEASE_MODE rolling; reload; up_gateway        # both slots share the traffic
    for c in blue green; do                                  # one batch = one instance
      echo "  batch $c: $(slot_version $c) -> $2"
      set_kv "${c^^}_VERSION" "$2"; set_kv "${c^^}_FAULT_RATE" 0; reload; up_slot "$c"
      # check between batches (course question 3.2): stop if the new instance is bad
      [ "$(slot_version $c)" = "$2" ] || { echo "batch $c failed -> ./scripts/release.sh rollback"; exit 1; }
    done
    echo "rolling update done: blue and green run $2" ;;

  rollback)
    [ -f .release.previous ] || { echo "no previous state"; exit 1; }
    cp .release.previous release.env; reload
    up_slot blue; up_slot green; up_gateway
    echo "rolled back to the previous release state"; status ;;

  *) sed -n '5,13p' "$0"; exit 2 ;;
esac
