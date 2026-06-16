"""demo-route — file and fly the canonical interstellar run, print the clocks.

Compiles the hand-filed **Sol -> Beowulf -> Manticore -> Yeltsin's Star** route on
the discrete-event core and prints each ship's itinerary + total clock. Flies it
for two contrasting hulls so the hyper-band model shows: a fast battlecruiser
(high band) vs a freighter (low band). The Phase 2b deliverable as a runnable demo.

Universe artifact path: ``$HVSIM_UNIVERSE_DB`` or the first CLI arg, else
``build/universe.db`` relative to the working directory.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

from hvsim.route import (
    CompiledRoute,
    Route,
    RouteLeg,
    compile_route,
    ship_from_artifact,
    simulation_for_route,
)
from hvsim.universe import Universe

DEPART = datetime(1890, 1, 1, tzinfo=UTC)  # PD epoch year (see SimClock)
# Contrasting hulls: a Nike-class battlecruiser (Eta) vs a Starhauler freighter (Delta).
DEMO_SHIPS = ["hms-nike-bc-562", "cms-starhauler"]
LEGS = [
    RouteLeg("hyper", "sigma-draconis"),  # Sol -> Beowulf, hyper bridge
    RouteLeg("wormhole", "manticore"),  # Beowulf Terminus -> Manticore
    RouteLeg("hyper", "yeltsins-star", "yeltsins-star:grayson"),  # -> Grayson
]


def _dur(seconds: float) -> str:
    days = seconds / 86400.0
    return f"{days:7.2f} d" if days >= 1.0 else f"{seconds / 3600.0:7.2f} h"


def render(u: Universe) -> str:
    lines = ["Route: Sol -> Beowulf -> (wormhole) -> Manticore -> Yeltsin's Star / Grayson", ""]
    for ship_id in DEMO_SHIPS:
        ship = ship_from_artifact(u, ship_id)
        route = Route(ship, "sol", "earth", list(LEGS), DEPART)
        c: CompiledRoute = compile_route(route, u)
        band = u.hyperspace_band(ship.max_hyper_band or 4)
        total = (c.arrival - c.depart_at).total_seconds()
        lines.append(
            f"== {ship.name}  (band {band['name']}, real {ship.hyper_cruise_velocity_c}c) =="
        )
        for s in c.segments:
            where = s.system or (f"{s.from_system}->{s.to_system}" if s.from_system else "?")
            lines.append(f"  [{s.seq}] {s.kind:16s} {where:24s} {_dur(s.duration_s)}")
        lines.append(f"  TOTAL: {_dur(total)}  ({total / 86400.0:.1f} days)")
        # A late-trip sample to show cross-system state.
        sim = simulation_for_route(c, u)
        mid = c.depart_at + (c.arrival - c.depart_at) * 0.5
        st = sim.state(mid)
        loc = st.system or "(interstellar)"
        lines.append(f"  midpoint: {st.phase} in {loc} [{st.frame}]")
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    db = args[0] if args else os.environ.get("HVSIM_UNIVERSE_DB", "build/universe.db")
    print(render(Universe.open(db)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
