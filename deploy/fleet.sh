#!/usr/bin/env bash
# Print the fleet roster: galaxy routes (transponder-addressed) + Phase-1 Sol ships.
# A stopgap for the map UI (kwi #57; the rich galaxy/Sol map is Phase 2.5).
# Usage: ./deploy/fleet.sh [API_BASE_URL]   (default: http://kubsdb:4667)
set -euo pipefail

API="${1:-http://kubsdb:4667}"

python3 - "$API" <<'PY'
import json, sys, urllib.request

api = sys.argv[1]


def get(path):
    try:
        return json.load(urllib.request.urlopen(api + path))
    except Exception:  # noqa: BLE001 - galaxy /fleet 503s without the artifact
        return None


def eta(s):
    return s["eta"][:19].replace("T", " ") if s.get("eta") else "-"


def pct(s):
    p = s.get("percent_complete")
    return f"{round(p * 100)}%" if p is not None else "-"


shown = False

# Galaxy routes (the primary fleet now): transponder-addressed multi-mode trips.
fleet = get("/fleet")
if fleet and fleet.get("ships"):
    shown = True
    hdr = f"{'XPNDR':>9} {'SHIP':22} {'PHASE':16} {'SYSTEM':16} {'PROG':>5} ETA (UTC)"
    print("GALAXY ROUTES")
    print(hdr)
    print("-" * len(hdr))
    for s in fleet["ships"]:
        loc = s.get("system") or "(interstellar)"
        print(f"{s['transponder']:>9} {s['ship']:22} {s['phase']:16} {loc:16} {pct(s):>5} {eta(s)}")

# Phase-1 Sol user ships (legacy single-system flight plans).
ships = get("/ships") or []
if ships:
    if shown:
        print()
    shown = True
    hdr = f"{'SHIP':22} {'ACCEL':>6} {'PHASE':11} {'SPEED':>8} {'PROG':>5} {'DEST':14} ETA (UTC)"
    print("SOL SHIPS (Phase 1)")
    print(hdr)
    print("-" * len(hdr))
    for s in sorted(ships, key=lambda s: s["name"]):
        st = s["state"]
        print(
            f"{s['name']:22} {s['max_accel_g']:>5.0f}g {st['phase']:11} "
            f"{st['velocity']['fraction_c']:>7.3f}c {pct(st):>5} {st.get('destination') or '-':14} {eta(st)}"
        )

if not shown:
    print("no ships or routes filed")
PY
