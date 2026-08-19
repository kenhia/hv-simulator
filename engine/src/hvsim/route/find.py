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

The topology itself is precomputed: :mod:`hvsim.route.graph` reads the artifact's
navigable shape once and caches a predecessor table per (speed class, origin), so
this module's job is reduced to the ship's speed class plus the last mile — the
in-system legs the compiler solves against live body positions (#64).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from hvsim.clock import T_YEAR
from hvsim.flightplan import Ship
from hvsim.universe import Universe

from .graph import HYPER_LEG_OVERHEAD_S, hops, route_graph
from .plan import NSPACE, Route, RouteLeg, ship_from_artifact

HYPER, WORMHOLE = "hyper", "wormhole"
_YEAR_S = T_YEAR.total_seconds()


def speed_class(u: Universe, ship: Ship) -> float:
    """The ship's hyper cost per light-year (s/ly) — its routing speed class.

    ``k = T_year / (band multiplier x real cruise velocity)``. Everything else in a
    hyper edge's weight is the distance and a flat leg overhead, so two ships with
    the same ``k`` route identically and share a cached table.
    """
    band = u.hyperspace_band(ship.max_hyper_band or 4)
    mult = (band or {}).get("velocity_multiplier")
    if not mult:
        raise ValueError(f"band {ship.max_hyper_band} has no velocity multiplier")
    return _YEAR_S / (mult * (ship.hyper_cruise_velocity_c or 0.5))


def hyper_time_s(u: Universe, ship: Ship, a: str, b: str) -> float | None:
    """Estimated hyper travel time (s) for ``ship`` between systems a and b."""
    d = route_graph(u).distance_ly(a, b)
    return None if d is None else d * speed_class(u, ship) + HYPER_LEG_OVERHEAD_S


def _search(u: Universe, ship: Ship, origin: str, dest: str) -> list[tuple[str, str]]:
    """Min-time hops origin->dest as (mode, to_system); raises if unreachable."""
    return hops(route_graph(u), speed_class(u, ship), origin, dest)


def _legs(path: list[tuple[str, str]], dest_system: str, dest_body: str) -> list[RouteLeg]:
    """Turn (mode, system) hops into RouteLegs ending at the destination body."""
    legs = [RouteLeg(mode=mode, to_system=sysid) for mode, sysid in path]
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
