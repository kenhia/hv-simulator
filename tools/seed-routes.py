#!/usr/bin/env python3
"""Seed repeating couriers so the galaxy runs itself (Sprint 039, #59).

Files a handful of **repeating routes** at a running service: each ship gets a
round trip it flies forever, re-departing after a layover drawn deterministically
from its range. Nothing ticks in the background — the engine walks to whichever
cycle covers the queried instant — so the map simply looks *busy* whenever you
open it, unattended.

    python3 tools/seed-routes.py [base_url]

The service needs the universe artifact (HVSIM_UNIVERSE_DB). Re-running is safe:
each ship's existing route is cleared first.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

# (transponder, label, origin, [destinations], layover hours min-max)
# Each is a loop: origin -> destinations... -> origin, repeated forever.
LOOPS = [
    (
        "1.1.1",
        "Sol inner-system freight run",
        ("sol", "earth"),
        [("sol", "mars")],
        (1.0, 4.0),
    ),
    (
        "347.1.1",
        "Manticore binary shuttle",
        ("manticore", "manticore:manticore"),
        [("manticore", "manticore:sphinx")],
        (2.0, 6.0),
    ),
    (
        "555.1.1",
        "Manticore <-> Trevor's Star junction run",
        ("manticore", "manticore:manticore"),
        [("trevors-star", "trevors-star:san-martin")],
        (4.0, 12.0),
    ),
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

    print(f"== Filing {len(LOOPS)} repeating routes at {base} ==")
    for tp, label, origin, stops, (lo, hi) in LOOPS:
        origin_doc = {"system": origin[0], "body": origin[1]}
        # A cycle is the itinerary plus the leg home, so plan the whole round trip.
        waypoints = [
            {"system": s, "body": b, "layover_s": lo * 3600} for s, b in [*stops, origin]
        ]
        try:
            plan = _req(
                "POST", f"{base}/plan", {"ship": tp, "origin": origin_doc, "waypoints": waypoints}
            )
        except urllib.error.HTTPError as e:
            print(f"  {tp:>10s}  {label}: plan failed ({e.code} {e.read().decode()[:120]})")
            continue

        filed = plan["filed"]
        # A layover range on every leg that reaches a body; the intermediate hyper
        # and wormhole legs get none.
        filed["repeat"] = {
            "layovers": [
                {"min_s": lo * 3600, "max_s": hi * 3600}
                if leg.get("to_body")
                else {"min_s": 0, "max_s": 0}
                for leg in filed["legs"]
            ],
            "cycles": None,  # forever — the whole point
            "seed": abs(hash(tp)) % 100_000,
            "rules": [],
        }

        try:  # clear any prior route so a re-run isn't blocked by the at-origin guard
            _req("DELETE", f"{base}/fleet/{tp}/route")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
        try:
            out = _req("POST", f"{base}/fleet/routes", filed)
        except urllib.error.HTTPError as e:
            print(f"  {tp:>10s}  {label}: file failed ({e.code} {e.read().decode()[:120]})")
            continue
        print(
            f"  {out['transponder']:>10s}  {label:42s} "
            f"cycle {out['total_duration_human']:>10s}  layover {lo:g}-{hi:g} h  forever"
        )

    print("\n== Fleet board ==")
    for s in _req("GET", f"{base}/fleet")["ships"]:
        cyc = f"cycle {s['cycle']}" if s.get("cycle") else "-"
        loc = s["system"] or "(interstellar)"
        print(f"  {s['transponder']:>10s} {s['ship']:24s} {s['phase']:16s} {loc:16s} {cyc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
