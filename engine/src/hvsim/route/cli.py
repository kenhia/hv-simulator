"""demo-route — file and fly the canonical interstellar run, print the clocks.

Compiles the hand-filed **Sol -> Beowulf -> Manticore -> Yeltsin's Star** route on
the discrete-event core and prints the itinerary (per-segment clocks) plus a
sampled state timeline. The Phase 2b deliverable as a runnable demo.

Universe artifact path: ``$HVSIM_UNIVERSE_DB`` or the first CLI arg, else
``build/universe.db`` relative to the working directory.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta

from hvsim.flightplan import Ship
from hvsim.route import CompiledRoute, Route, RouteLeg, compile_route, simulation_for_route
from hvsim.universe import Universe

DEPART = datetime(1890, 1, 1, tzinfo=UTC)  # PD epoch year (see SimClock)


def canonical_route(ship: Ship) -> Route:
    """Sol -> Beowulf (hyper) -> Manticore (wormhole) -> Grayson (hyper)."""
    return Route(
        ship=ship,
        origin_system="sol",
        origin_body="earth",
        depart_at=DEPART,
        legs=[
            RouteLeg("hyper", "sigma-draconis"),  # Sol -> Beowulf, hyper bridge
            RouteLeg("wormhole", "manticore"),  # Beowulf Terminus -> Manticore
            RouteLeg("hyper", "yeltsins-star", "yeltsins-star:grayson"),  # -> Grayson
        ],
    )


def _dur(seconds: float) -> str:
    days = seconds / 86400.0
    if days >= 1.0:
        return f"{days:7.2f} d"
    return f"{seconds / 3600.0:7.2f} h"


def render(compiled: CompiledRoute, u: Universe) -> str:
    lines = ["Itinerary  (Sol -> Beowulf -> Manticore -> Yeltsin's Star / Grayson)", ""]
    for s in compiled.segments:
        where = s.system or (f"{s.from_system}->{s.to_system}" if s.from_system else "?")
        lines.append(f"  [{s.seq}] {s.kind:16s} {where:24s} {_dur(s.duration_s)}")
    total = (compiled.arrival - compiled.depart_at).total_seconds()
    lines += [
        "",
        f"  depart : {compiled.depart_at:%Y-%m-%d %H:%M} PD-epoch",
        f"  arrive : {compiled.arrival:%Y-%m-%d %H:%M}",
        f"  TOTAL  : {_dur(total)}  ({total / 86400.0:.1f} days)",
        "",
        "Sampled state:",
    ]
    sim = simulation_for_route(compiled, u)
    span = compiled.arrival - compiled.depart_at
    for frac in (0.0, 0.1, 0.5, 0.9, 1.01):
        when = compiled.depart_at + timedelta(seconds=span.total_seconds() * frac)
        st = sim.state(when)
        elapsed = (when - compiled.depart_at).total_seconds() / 86400.0
        loc = st.system or "(interstellar)"
        lines.append(f"  t+{elapsed:7.1f} d   {st.phase:16s} {loc:16s} [{st.frame}]")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    db = args[0] if args else os.environ.get("HVSIM_UNIVERSE_DB", "build/universe.db")
    u = Universe.open(db)
    ship = Ship(name="SS Tankersley", max_accel_g=250.0, max_velocity_c=0.6)
    compiled = compile_route(canonical_route(ship), u)
    print(render(compiled, u))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
