#!/usr/bin/env python3
"""Galaxy shakedown over HTTP: plan + file a fleet, watch the board advance.

Plans a few multi-leg routes with the nav-planner, files them at the running
service (`POST /fleet/routes`), sets an accelerated dev clock, then prints the
fleet board across a sweep of sim times (`GET /fleet?at=`). Works against a local
instance or the deployed `kubsdb`.

    cd tools/nav-planner && uv run python ../../tools/shakedown.py [base_url] [db]

Requires the service running with the universe artifact + dev clock
(HVSIM_UNIVERSE_DB set, HVSIM_DEV_CLOCK=1).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from hvsim.route import to_filed
from hvsim.universe import Universe
from nav_planner import plan_route

T0 = datetime(1890, 1, 1, tzinfo=UTC)
# (ship_id, from_system, from_body, to_system, to_body)
FLEET = [
    ("hms-nike-bc-562", "sol", "earth", "yeltsins-star", "yeltsins-star:grayson"),
    ("cms-starhauler", "sol", "earth", "manticore", "manticore:manticore"),
    ("gns-raoul-courvosier-ii-bc-44", "yeltsins-star", "yeltsins-star:grayson", "basilisk", "basilisk:medusa"),
    ("hms-reliant", "manticore", "manticore:manticore", "trevors-star", "trevors-star:san-martin"),
    ("rmms-athena", "manticore", "manticore:manticore", "sigma-draconis", "sigma-draconis:beowulf"),
]


def _req(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 - local/trusted base_url
        return json.loads(resp.read())


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    base = args[0].rstrip("/") if args else "http://localhost:4667"
    db = args[1] if len(args) > 1 else "build/universe.db"
    u = Universe.open(db)

    print(f"== Filing {len(FLEET)} routes at {base} ==")
    for ship_id, fs, fb, ts, tb in FLEET:
        route = plan_route(u, ship_id, fs, fb, ts, tb, T0)
        doc = to_filed(route, u.transponder(ship_id))
        out = _req("POST", f"{base}/fleet/routes", doc)
        legs = " -> ".join(s["kind"] for s in out["segments"])
        print(f"  {out['transponder']:>10s}  {ship_id:30s} {out['total_duration_human']:>10s}  [{legs}]")

    # Best-effort: in dev mode, anchor + accelerate the clock so a plain GET /fleet
    # advances in real time. In production (PUT /clock 403s) the board sweep below
    # time-travels via ?at= instead, so this is optional.
    try:
        _req("PUT", f"{base}/clock", {"jump_to": T0.isoformat(), "rate": 2000})
    except urllib.error.HTTPError as e:
        print(f"  (clock control unavailable: {e.code} — using ?at= sweep)")

    print("\n== Fleet board (sim-time sweep) ==")
    for days in (0, 2, 6, 15, 40):
        when = (T0 + timedelta(days=days)).isoformat()
        fleet = _req("GET", f"{base}/fleet?at={quote(when)}")
        print(f"\n  T+{days:>3}d:")
        for s in fleet["ships"]:
            loc = s["system"] or "(interstellar)"
            pct = f"{(s['percent_complete'] or 0) * 100:5.1f}%"
            print(f"    {s['transponder']:>10s} {s['ship']:24s} {s['phase']:16s} {loc:16s} {pct}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
