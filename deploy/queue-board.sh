#!/usr/bin/env bash
# Print a wormhole junction's live transit queue (the "you are #3" board).
# Usage: ./deploy/queue-board.sh [JUNCTION_ID] [API_BASE_URL] [AT_ISO8601]
#   defaults: manticore-junction  http://kubsdb:4667  (server "now")
set -euo pipefail

JUNCTION="${1:-manticore-junction}"
API="${2:-http://kubsdb:4667}"
AT="${3:-}"

python3 - "$JUNCTION" "$API" "$AT" <<'PY'
import json, sys, urllib.parse, urllib.request

junction, api, at = sys.argv[1], sys.argv[2], sys.argv[3]
path = f"/junctions/{junction}/queue"
if at:
    path += "?at=" + urllib.parse.quote(at)
try:
    q = json.load(urllib.request.urlopen(api + path))
except Exception as e:  # noqa: BLE001
    sys.exit(f"queue board unavailable ({e}) - is the service up and the artifact loaded?")


def eta(s):
    return s["transit_eta"][:19].replace("T", " ") if s.get("transit_eta") else "-"


knob = q.get("traffic_intensity")
when = q["when"][:19].replace("T", " ")
print(f"{q['junction_id']} - transit queue @ {when}  (traffic_intensity {knob})")
entries = q["entries"]
if not entries:
    print("  (empty - immediate transit)")
else:
    for e in entries:
        who = e["transponder"] or "(phantom)"
        print(f"  #{e['position']:<3d} {who:<12s} {e['mass_tons']:>12,.0f} t   transit {eta(e)}")
    reals = [e for e in entries if e["transponder"]]
    print(f"  {len(reals)} tracked ship(s) of {len(entries)} in queue")
PY
