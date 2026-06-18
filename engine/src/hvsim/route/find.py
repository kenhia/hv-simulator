"""Route-finding: graph search over the universe → a filed multi-mode Route.

Relocated into the engine (Sprint 026) so the API can plan over HTTP (`POST /plan`)
without a circular dependency on the `nav-planner` tool — finding is now a
first-class engine capability alongside the physics. `tools/nav-planner` is a thin
CLI wrapper that re-exports :func:`plan_route`.

Dijkstra over placed systems: **hyper** edges between every pair (weight = the
ship's estimated hyper time) and **wormhole** edges from the link graph (weight ~
the junction buffer, so a junction hop wins whenever one helps). The finder picks
the *topology* (which systems, which modes); :func:`compile_route` stays the source
of truth for the executed clock.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from datetime import datetime, timedelta

from hvsim.clock import T_YEAR
from hvsim.flightplan import Ship
from hvsim.universe import Universe

from .plan import NSPACE, Route, RouteLeg, ship_from_artifact

HYPER, WORMHOLE = "hyper", "wormhole"
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


def plan_route_multi(
    u: Universe,
    ship_id: str,
    origin_system: str,
    origin_body: str,
    waypoints: list[tuple[str, str, timedelta]],
    depart_at: datetime,
) -> Route:
    """Plan an ordered multi-destination route: origin -> waypoint1 -> waypoint2 ...

    Each ``waypoint`` is ``(system, body, layover)``; the finder runs for every
    consecutive hop and the legs concatenate into one :class:`Route`, the reaching
    leg carrying the layover. The rest of the stack already flies multi-leg routes.
    """
    ship = ship_from_artifact(u, ship_id)
    legs: list[RouteLeg] = []
    cursor = origin_system
    for system, body, layover in waypoints:
        hop_legs = _legs(_search(u, ship, cursor, system), system, body)
        if layover > timedelta(0) and hop_legs:
            last = hop_legs[-1]
            hop_legs[-1] = RouteLeg(last.mode, last.to_system, last.to_body, layover)
        legs.extend(hop_legs)
        cursor = system
    return Route(ship, origin_system, origin_body, legs, depart_at)


def plan_route(
    u: Universe,
    ship_id: str,
    origin_system: str,
    origin_body: str,
    dest_system: str,
    dest_body: str,
    depart_at: datetime,
) -> Route:
    """Search the graph and assemble the time-optimal filed Route (single dest)."""
    return plan_route_multi(
        u, ship_id, origin_system, origin_body, [(dest_system, dest_body, timedelta(0))], depart_at
    )
