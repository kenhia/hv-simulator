"""queue-demo — file two couriers into a busy wormhole junction, watch the queue.

Both ships arrive at the **Beowulf Terminus of the Manticore Junction** at the
same instant; the FCFS resolver (phantom traffic from the junction's
``traffic_intensity`` knob + the two real ships interleaving by transponder)
fixes each one's transit slot. The demo prints a countdown table as sim time
advances -- ``#N in queue, transit in MM:SS`` ticking down to the pop -- showing
the second ship serialised strictly behind the first.

No game loop: every row is an analytic ``state(when)`` query on the resolved
discrete-event timeline. Artifact path: ``$HVSIM_UNIVERSE_DB`` or argv[1], else
``build/universe.db``.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta

from hvsim.route import (
    Route,
    RouteLeg,
    compile_route,
    resolve_fleet,
    ship_from_artifact,
    simulation_for_route,
)
from hvsim.universe import Universe

DEPART = datetime(1890, 1, 1, tzinfo=UTC)
ORIGIN_SYSTEM, ORIGIN_BODY, DEST = "sigma-draconis", "sigma-draconis:beowulf", "manticore"
# Two RMN cruisers leaving Beowulf together for the Junction.
DEMO_SHIPS = ["hms-fearless-ca-286", "hms-warlock-ca-277"]


def _mmss(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    return f"{total // 60:02d}:{total % 60:02d}"


def render(u: Universe) -> str:
    junction = u.wormhole_link_between(ORIGIN_SYSTEM, DEST) or {}
    jrec = u.wormhole_junction(junction.get("junction_id") or "") or {}

    items = []
    labels = []
    for ship_id in DEMO_SHIPS:
        ship = ship_from_artifact(u, ship_id)
        key = u.transponder(ship_id) or ship_id
        route = Route(ship, ORIGIN_SYSTEM, ORIGIN_BODY, [RouteLeg("wormhole", DEST)], DEPART)
        items.append((compile_route(route, u), key))
        labels.append((ship.name, key))

    resolved = resolve_fleet(items, u)
    sims = [simulation_for_route(c, u) for c in resolved]
    queues = [c.segments[0] for c in resolved]  # the wormhole_queue is the first leg

    lines = [
        f"{jrec.get('name', 'Junction')} -- transit queue "
        f"(traffic_intensity {jrec.get('traffic_intensity')})",
        f"Two RMN cruisers translate in from Beowulf at {DEPART:%Y-%m-%d %H:%M}; "
        "FCFS, ties by transponder.",
        "",
    ]
    header = "  T+      " + "".join(f"{name} ({key}){'':<6}" for name, key in labels)
    lines.append(header)

    last_open = max(q.t_end for q in queues)
    step = max(int((last_open - DEPART).total_seconds() / 10) // 60 * 60, 60)
    when = DEPART
    while when <= last_open:
        cells = []
        for sim, q in zip(sims, queues, strict=True):
            st = sim.state(when)
            if st.phase == "queued":
                cells.append(f"#{st.queue_position:<2d} transit in {_mmss(q.t_end - when)}   ")
            else:
                cells.append("-- transited --        ")
        lines.append(f"  {_mmss(when - DEPART)}   " + "".join(cells))
        when += timedelta(seconds=step)

    lines.append("")
    for (name, key), q in zip(labels, queues, strict=True):
        lines.append(f"  {name} ({key}) pops through to {DEST} at {q.t_end:%H:%M:%S}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    db = args[0] if args else os.environ.get("HVSIM_UNIVERSE_DB", "build/universe.db")
    print(render(Universe.open(db)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
