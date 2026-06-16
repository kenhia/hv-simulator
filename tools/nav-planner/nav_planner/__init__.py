"""nav_planner — graph search over the universe → a filed multi-mode route.

The route-finder half of the founding split: it picks the *topology* (which
systems, which modes) and emits a filed-route JSON the engine flies; the engine
stays the source of truth for the executed clock. Dijkstra over placed systems,
with **hyper** edges between every pair (weight = the ship's estimated hyper time)
and **wormhole** edges from the link graph (weight ~ the junction buffer, so a
junction hop wins whenever one helps). Depends on the engine for the artifact-read
layer (`Universe`, `effective_ship`) and the `Route` types.
"""

from __future__ import annotations

import argparse
import heapq
import json
import math
from collections import defaultdict
from datetime import UTC, datetime

from hvsim.clock import T_YEAR
from hvsim.flightplan import Ship
from hvsim.route import (
    Route,
    RouteLeg,
    compile_route,
    ship_from_artifact,
    to_filed,
)
from hvsim.universe import Universe

NSPACE, HYPER, WORMHOLE = "nspace", "hyper", "wormhole"
# A flat per-hyper-leg n-space allowance (run-out + approach) so the search
# slightly prefers fewer hyper hops; the engine computes the real overhead.
HYPER_LEG_OVERHEAD_S = 6 * 3600.0
_YEAR_S = T_YEAR.total_seconds()


def _distance_ly(u: Universe, a: str, b: str) -> float | None:
    ca, cb = u.coordinates(a), u.coordinates(b)
    if ca is None or cb is None:
        return None
    return math.dist(ca, cb)


def _hyper_time_s(u: Universe, ship: Ship, a: str, b: str) -> float | None:
    """Estimated hyper travel time (s) for ``ship`` between systems a and b."""
    dist_ly = _distance_ly(u, a, b)
    if dist_ly is None:
        return None
    band = u.hyperspace_band(ship.max_hyper_band or 4)
    mult = (band or {}).get("velocity_multiplier")
    real_v = ship.hyper_cruise_velocity_c or 0.5
    if not mult:
        return None
    apparent_c = mult * real_v
    return dist_ly / apparent_c * _YEAR_S + HYPER_LEG_OVERHEAD_S


def _placed_systems(u: Universe) -> set[str]:
    return {s["id"] for s in u.systems() if u.coordinates(s["id"]) is not None}


def _wormhole_adjacency(u: Universe) -> dict[str, set[str]]:
    # Only true wormholes (transit == "instant") are junction hops; the table also
    # holds hyper_leg / transfer annotations (transit None) that are NOT wormholes.
    adj: dict[str, set[str]] = defaultdict(set)
    for link in u.wormhole_links():
        a, b = link.get("from_system_id"), link.get("to_system_id")
        if a and b and link.get("transit") == "instant":
            adj[a].add(b)
            adj[b].add(a)
    return adj


def _search(u: Universe, ship: Ship, origin: str, dest: str) -> list[tuple[str, str]]:
    """Min-time hops origin->dest as (mode, to_system); raises if unreachable."""
    placed = _placed_systems(u)
    for sysid in (origin, dest):
        if sysid not in placed:
            raise ValueError(f"system {sysid!r} is not placed (no coordinates)")
    worm = _wormhole_adjacency(u)
    buffer_s = (u.transit_model() or {}).get("buffer_normal_s") or 0.0

    dist = {origin: 0.0}
    prev: dict[str, tuple[str, str]] = {}  # node -> (from_node, mode)
    pq: list[tuple[float, str]] = [(0.0, origin)]
    while pq:
        d, node = heapq.heappop(pq)
        if node == dest:
            break
        if d > dist.get(node, math.inf):
            continue
        edges: list[tuple[str, str, float]] = []
        for nb in worm.get(node, ()):  # wormhole edges (cheap)
            if nb in placed:
                edges.append((nb, WORMHOLE, buffer_s))
        for nb in placed:  # hyper edges (all pairs)
            if nb != node:
                t = _hyper_time_s(u, ship, node, nb)
                if t is not None:
                    edges.append((nb, HYPER, t))
        for nb, mode, w in edges:
            nd = d + w
            if nd < dist.get(nb, math.inf):
                dist[nb] = nd
                prev[nb] = (node, mode)
                heapq.heappush(pq, (nd, nb))

    if dest not in prev and dest != origin:
        raise ValueError(f"no route from {origin!r} to {dest!r}")
    hops: list[tuple[str, str]] = []
    node = dest
    while node != origin:
        frm, mode = prev[node]
        hops.append((mode, node))
        node = frm
    hops.reverse()
    return hops


def _legs(hops: list[tuple[str, str]], dest_system: str, dest_body: str) -> list[RouteLeg]:
    """Turn (mode, system) hops into RouteLegs ending at the destination body."""
    legs = [RouteLeg(mode=mode, to_system=sysid) for mode, sysid in hops]
    if not legs:
        # Same-system trip: a single n-space hop to the body.
        return [RouteLeg(NSPACE, dest_system, dest_body)]
    last = legs[-1]
    if last.mode == HYPER:
        # The final hyper leg's approach targets the destination body.
        legs[-1] = RouteLeg(HYPER, last.to_system, dest_body)
    else:
        # Arrived at the destination via wormhole/n-space: add an in-system hop.
        legs.append(RouteLeg(NSPACE, dest_system, dest_body))
    return legs


def plan_route(
    u: Universe,
    ship_id: str,
    origin_system: str,
    origin_body: str,
    dest_system: str,
    dest_body: str,
    depart_at: datetime,
) -> Route:
    """Search the graph and assemble the time-optimal filed Route."""
    ship = ship_from_artifact(u, ship_id)
    hops = _search(u, ship, origin_system, dest_system)
    legs = _legs(hops, dest_system, dest_body)
    return Route(ship, origin_system, origin_body, legs, depart_at)


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
    filed = to_filed(route, args.ship)

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
