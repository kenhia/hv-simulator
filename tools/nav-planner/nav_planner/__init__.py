"""nav-plan — a thin CLI over the engine's route-finder.

The finder itself now lives in the engine (`hvsim.route.plan_route`, Sprint 026)
so the API can plan over HTTP; this tool is the command-line front-end (`nav-plan`
/ `just plan`) that searches the graph and writes a filed-route JSON. `plan_route`
is re-exported for backward compatibility (and the tool's test).
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from hvsim.route import compile_route, plan_route, to_filed
from hvsim.universe import Universe

__all__ = ["plan_route", "main"]


def _fmt_dur(seconds: float) -> str:
    days = seconds / 86400.0
    return f"{days:.2f} d" if days >= 1.0 else f"{seconds / 3600.0:.2f} h"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="nav-plan", description="Plan a multi-mode route.")
    p.add_argument("--db", default="build/universe.db", help="universe artifact path")
    p.add_argument("--ship", required=True, help="artifact ship id")
    p.add_argument("--from-system", required=True)
    p.add_argument("--from-body", required=True)
    p.add_argument("--to-system", required=True)
    p.add_argument("--to-body", required=True)
    p.add_argument("--out", help="write the filed-route JSON here")
    p.add_argument("--depart", help="ISO-8601 departure (default 1890-01-01)")
    args = p.parse_args(argv)

    u = Universe.open(args.db)
    depart = (
        datetime.fromisoformat(args.depart) if args.depart else datetime(1890, 1, 1, tzinfo=UTC)
    )
    route = plan_route(
        u, args.ship, args.from_system, args.from_body, args.to_system, args.to_body, depart
    )
    transponder = u.transponder(args.ship)
    if transponder is None:
        raise SystemExit(f"ship {args.ship!r} has no transponder")
    filed = to_filed(route, transponder)

    compiled = compile_route(route, u)  # the engine's authoritative clock
    eta_s = (compiled.arrival - compiled.depart_at).total_seconds()
    print(f"Plan for {route.ship.name}: {args.from_system} -> {args.to_system}")
    for leg in route.legs:
        target = leg.to_body or leg.to_system  # body id already includes its system
        print(f"  {leg.mode:9s} -> {target}")
    arrive = f"{compiled.arrival:%Y-%m-%d %H:%M}"
    print(f"  legs: {len(route.legs)}  ETA: {_fmt_dur(eta_s)}  (arrive {arrive})")
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(filed, fh, indent=2)
        print(f"  filed route -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
