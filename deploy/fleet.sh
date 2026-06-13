#!/usr/bin/env bash
# Print the fleet as a text roster (ships + current flight-plan state).
# A stopgap for the Sol map's label crowding (kwi #57).
# Usage: ./deploy/fleet.sh [API_BASE_URL]   (default: http://kubsdb:4667)
set -euo pipefail

API="${1:-http://kubsdb:4667}"

python3 - "$API" <<'PY'
import json, sys, urllib.request

api = sys.argv[1]
ships = json.load(urllib.request.urlopen(api + "/ships"))
if not ships:
    print("no ships filed")
    sys.exit(0)

hdr = f"{'SHIP':22} {'ACCEL':>6} {'PHASE':11} {'SPEED':>8} {'PROG':>5} {'DEST':14} ETA (UTC)"
print(hdr)
print("-" * len(hdr))
for s in sorted(ships, key=lambda s: s["name"]):
    st = s["state"]
    pct = st.get("percent_complete")
    pct = f"{round(pct * 100)}%" if pct is not None else "-"
    eta = st["eta"][:19].replace("T", " ") if st.get("eta") else "-"
    dest = st.get("destination") or "-"
    print(
        f"{s['name']:22} {s['max_accel_g']:>5.0f}g {st['phase']:11} "
        f"{st['velocity']['fraction_c']:>7.3f}c {pct:>5} {dest:14} {eta}"
    )
PY
