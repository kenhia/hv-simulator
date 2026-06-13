#!/usr/bin/env bash
# Seed a few experimental ships + flight plans on a running hvsim instance.
# Usage: ./deploy/seed.sh [API_BASE_URL]   (default: http://kubsdb:4667)
#
# Ships are named "XSS <name>" (X = eXperimental) so R&D ships are obvious in the
# fleet, with a spread of accelerations from a 100 g heavy transport to a 700 g
# courier. Trips are short-ish inner-system hops so they complete in real time
# within hours (M7 watches them finish).
set -euo pipefail

API="${1:-http://kubsdb:4667}"

mkship() {
  curl -fsS -X POST "$API/ships" -H 'content-type: application/json' -d "$1" \
    | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])'
}
plan() {
  curl -fsS -X POST "$API/ships/$1/flightplan" -H 'content-type: application/json' -d "$2" >/dev/null
}

# Heavy in-system transport — slow and steady.
T=$(mkship '{"name":"XSS Mountbatten","max_accel_g":100,"max_velocity_c":0.6}')
# Tiny courier — trades size and safety for raw acceleration.
C=$(mkship '{"name":"XSS Sphinx Courier","max_accel_g":700,"max_velocity_c":0.6}')
# Mid-weight merchant.
M=$(mkship '{"name":"XSS Wayfarer","max_accel_g":300,"max_velocity_c":0.6}')

plan "$T" '{"waypoints":[{"body":"mars","layover_seconds":7200},{"body":"earth"}]}'
plan "$C" '{"waypoints":[{"body":"venus"},{"body":"earth"}]}'
plan "$M" '{"waypoints":[{"body":"mars"}]}'

echo "seeded 3 XSS ships against $API:"
echo "  XSS Mountbatten    100 g  Earth -> Mars (2h) -> Earth"
echo "  XSS Sphinx Courier 700 g  Earth -> Venus -> Earth"
echo "  XSS Wayfarer       300 g  Earth -> Mars"
