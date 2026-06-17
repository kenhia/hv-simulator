"""Multi-mode interstellar routes: file legs, compile to discrete-event segments.

A :class:`Route` is an ordered list of mode-tagged :class:`RouteLeg`s from an
origin ``(system, body)``. :func:`compile_route` walks them against the
``Universe`` — reading hyper limits, band apparent velocity, inter-system
distances, and the wormhole buffer **from the artifact** — and emits the DES
:class:`~hvsim.des.Segment` sequence the core executes. Three modes:

- ``nspace`` — an in-system hop (brachistochrone/coast); the coast phase fires on
  long legs.
- ``hyper`` — a system→system leg, decomposed into a **run out** past the origin
  star's hyper limit (n-space impeller leg), **hyper_cruise** across the
  interstellar distance, and an **approach** in to the target body. The cruise is
  a normal impeller accel/coast/decel — but in *apparent* terms: apparent velocity
  = real velocity x the band multiplier, so the leg runs at apparent accel =
  impeller_accel x mult up to apparent v_cap = ship.hyper_cruise_velocity_c x mult
  (warship 0.6c / merchant 0.5c) over the galactic-frame distance. (NB: "run out"/
  "approach" are the mundane n-space legs to and from the hyper limit — *not* the
  Honorverse band "climb/descent", which is translating between hyperspace bands.)
- ``wormhole`` — a junction translation: instant + the fixed safety buffer.

v1 simplifications (documented): band-climb time + the per-band translation
bleed-off are treated as noise (the ship just flies its max band). The
run-out and the hyper cruise both decelerate to rest at the hyper limit, which
trivially satisfies the translation-velocity limits (<=0.3c entering Alpha from
n-space, <=0.2c x mult exiting) — modelling translate-while-moving at those caps is
a future refinement. A wormhole leg fires from wherever the ship is (no explicit
hop to the nexus). Route-*finding* lives in the `tools/nav-planner` tool, which
emits a filed route (see `to_filed` / `from_filed`); routes can also be hand-filed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from hvsim.des import Segment, Simulation
from hvsim.flightplan import Ship
from hvsim.kinematics import SPEED_OF_LIGHT, Vec3, solve_intercept
from hvsim.kinematics.trajectory import Trajectory
from hvsim.queue import DEFAULT_SHIP_MASS_T, SIM_SEED, JunctionServer
from hvsim.universe import LMIN_M, LY_M, Universe, resolve_position

NSPACE, HYPER, WORMHOLE = "nspace", "hyper", "wormhole"
_ZAXIS = Vec3(0.0, 0.0, 1.0)  # arbitrary radial when a position is at the star centre

# Fallbacks when a ship carries no band profile (a plain in-system Ship): a
# generic merchant — Delta band at 0.5c. Real ships supply their own via the
# artifact (Universe.effective_ship -> Ship).
DEFAULT_MAX_BAND = 4
DEFAULT_CRUISE_VELOCITY_C = 0.5


@dataclass(frozen=True)
class RouteLeg:
    """One filed leg: reach ``to_body`` in ``to_system`` by ``mode``."""

    mode: str  # nspace | hyper | wormhole
    to_system: str
    to_body: str | None = None  # None => stop at the hyper limit / junction
    layover: timedelta = timedelta(0)


@dataclass(frozen=True)
class Route:
    """A filed multi-mode route."""

    ship: Ship
    origin_system: str
    origin_body: str
    legs: list[RouteLeg]
    depart_at: datetime


@dataclass(frozen=True)
class CompiledRoute:
    """A filed route plus its solved segments and terminal context."""

    route: Route
    segments: list[Segment] = field(default_factory=list)
    final_system: str | None = None
    final_body: str | None = None

    @property
    def depart_at(self) -> datetime:
        return self.route.depart_at

    @property
    def arrival(self) -> datetime:
        last = self.segments[-1].t_end if self.segments else None
        return last if last is not None else self.route.depart_at


def body_resolver(u: Universe):
    """A (system, body, when) -> Vec3 resolver closing over the artifact."""

    def resolve(system: str, body: str, when: datetime) -> Vec3:
        return resolve_position(u, system, body, when) or Vec3(0.0, 0.0, 0.0)

    return resolve


def _galactic_m(u: Universe, system_id: str) -> Vec3:
    c = u.coordinates(system_id)
    if c is None:
        raise ValueError(f"system {system_id!r} has no galactic coordinates")
    return Vec3(c[0] * LY_M, c[1] * LY_M, c[2] * LY_M)


def compile_route(route: Route, u: Universe) -> CompiledRoute:  # noqa: C901 - linear leg walk
    """Compile a filed multi-mode route into DES segments."""
    accel, v_cap = route.ship.accel_si, route.ship.v_cap_si
    resolve = body_resolver(u)

    # Hyper cruise (Weber chart): apparent velocity = velocity_multiplier(band) x
    # real velocity. So the ship flies a normal impeller accel/coast/decel, scaled
    # into apparent terms: apparent accel = impeller accel x mult, apparent v_cap =
    # real cruise velocity x mult. Decelerating to rest at each limit satisfies the
    # translation-velocity limits by construction.
    cruise_band = route.ship.max_hyper_band or DEFAULT_MAX_BAND
    real_v = route.ship.hyper_cruise_velocity_c or DEFAULT_CRUISE_VELOCITY_C
    band = u.hyperspace_band(cruise_band)
    if band is None or band.get("velocity_multiplier") is None:
        raise ValueError(f"band {cruise_band} has no velocity multiplier")
    if band.get("unattainable"):
        raise ValueError(f"band {band['name']} is unattainable (needs the streak drive)")
    mult = band["velocity_multiplier"]
    hyper_accel = accel * mult
    hyper_vcap = real_v * SPEED_OF_LIGHT * mult

    when = route.depart_at
    system = route.origin_system
    pos = resolve(system, route.origin_body, when)
    segments: list[Segment] = []
    seq = 0

    def add(seg: Segment) -> None:
        nonlocal seq
        segments.append(seg)
        seq += 1

    for leg in route.legs:
        if leg.mode == NSPACE:
            assert leg.to_body is not None, "nspace leg needs a target body"
            ic = solve_intercept(
                pos, lambda t, b=leg.to_body, s=system: resolve(s, b, t), when, accel, v_cap
            )
            add(Segment(seq, "transit", when, ic.arrival, trajectory=ic.trajectory, system=system))
            when, pos = ic.arrival, resolve(system, leg.to_body, ic.arrival)

        elif leg.mode == HYPER:
            # 1. Run out past the origin star's hyper limit (n-space impeller leg;
            #    NOT a band "climb"). Brachistochrone -> arrives within the
            #    alpha-translation 0.3c ceiling. Per-ship max band: Sprint 015.
            limit_m = (u.hyper_limit_lmin(system) or 0.0) * LMIN_M
            direction = pos.unit() if pos.norm() > 0.0 else _ZAXIS
            limit_point = direction * max(limit_m, pos.norm())
            run_out = Trajectory.between(pos, limit_point, accel, v_cap)
            run_out_arrival = when + timedelta(seconds=run_out.duration)
            add(Segment(seq, "transit", when, run_out_arrival, trajectory=run_out, system=system))
            when = run_out_arrival

            # 2. Hyper cruise: an accel/coast/decel run across the galactic-frame
            #    distance, in apparent terms (accel/v_cap x mult). Reuses the same
            #    flip-and-burn solver as n-space; ends at rest at the destination
            #    limit (translation-out velocity trivially within limits).
            from_gal = _galactic_m(u, system)
            to_gal = _galactic_m(u, leg.to_system)
            cruise_traj = Trajectory.between(from_gal, to_gal, hyper_accel, hyper_vcap)
            cruise_end = when + timedelta(seconds=cruise_traj.duration)
            add(
                Segment(
                    seq,
                    "hyper_cruise",
                    when,
                    cruise_end,
                    trajectory=cruise_traj,
                    from_pos=from_gal,
                    to_pos=to_gal,
                    from_system=system,
                    to_system=leg.to_system,
                )
            )
            when, system = cruise_end, leg.to_system

            # 3. Approach: n-space leg in from the destination's hyper limit to
            #    the target body (again, not a band "descent").
            limit_m = (u.hyper_limit_lmin(system) or 0.0) * LMIN_M
            if leg.to_body is not None:
                target0 = resolve(system, leg.to_body, when)
                entry = (target0.unit() if target0.norm() > 0.0 else _ZAXIS) * limit_m
                ic = solve_intercept(
                    entry, lambda t, b=leg.to_body, s=system: resolve(s, b, t), when, accel, v_cap
                )
                add(
                    Segment(
                        seq,
                        "transit",
                        when,
                        ic.arrival,
                        trajectory=ic.trajectory,
                        system=system,
                    )
                )
                when, pos = ic.arrival, resolve(system, leg.to_body, ic.arrival)
            else:
                pos = _ZAXIS * limit_m

        elif leg.mode == WORMHOLE:
            link = u.wormhole_link_between(system, leg.to_system)
            if link is None:
                raise ValueError(f"no wormhole link {system} -> {leg.to_system}")
            junction = link.get("junction_id")
            # Arrival at the junction is `when`. The transit slot depends on the
            # junction's dynamic state at arrival (phantom + other ships), so the
            # queue segment is OPEN-ENDED: the fleet resolver fixes its t_end (the
            # transit-open) and shifts everything downstream by the wait. Until
            # then, downstream is timed as if the wait were zero.
            add(
                Segment(
                    seq,
                    "wormhole_queue",
                    when,
                    None,
                    from_system=system,
                    to_system=leg.to_system,
                    junction=junction,
                )
            )
            # Instant translation once the slot opens (provisionally at arrival).
            add(
                Segment(
                    seq, "wormhole_transit", when, when, from_system=system, to_system=leg.to_system
                )
            )
            when, system, pos = when, leg.to_system, Vec3(0.0, 0.0, 0.0)

        else:
            raise ValueError(f"unknown leg mode: {leg.mode!r}")

        if leg.layover > timedelta(0) and leg.to_body is not None:
            end = when + leg.layover
            add(Segment(seq, "layover", when, end, body=leg.to_body, system=system))
            when, pos = end, resolve(system, leg.to_body, end)

    final_body = next((leg.to_body for leg in reversed(route.legs) if leg.to_body), None)
    return CompiledRoute(route, segments, final_system=system, final_body=final_body)


# -- The fleet queue resolver (Phase 2c) ---------------------------------------


def _junction_server(u: Universe, junction_id: str, seed: int) -> JunctionServer | None:
    """A :class:`JunctionServer` for ``junction_id`` from the artifact, or None.

    None when the junction carries no ``traffic_intensity`` knob (no queue modelled
    -> transits are instant, the old behaviour minus the unconditional buffer).
    """
    j = u.wormhole_junction(junction_id) if junction_id else None
    if j is None or j.get("traffic_intensity") is None:
        return None
    model = u.transit_model() or {}
    return JunctionServer(
        junction_id=junction_id,
        coeff_a=model.get("coeff_a") or 0.0,
        coeff_b=model.get("coeff_b") or 0.0,
        buffer_s=model.get("buffer_normal_s") or 0.0,
        mean_depth=j["traffic_intensity"],
        seed=seed,
    )


def _shift(segments: list[Segment], start_idx: int, delta: timedelta) -> None:
    """Shift every segment from ``start_idx`` onward by ``delta`` (in place)."""
    if not delta:
        return
    for i in range(start_idx, len(segments)):
        s = segments[i]
        segments[i] = replace(
            s,
            t_start=s.t_start + delta,
            t_end=None if s.t_end is None else s.t_end + delta,
        )


def resolve_fleet_junctions(
    items: list[tuple[CompiledRoute, str]],
    u: Universe,
    *,
    seed: int = SIM_SEED,
) -> tuple[list[CompiledRoute], dict[str, JunctionServer]]:
    """Resolve the fleet's queues *and* return the per-junction servers.

    Same fold as :func:`resolve_fleet`, but also yields the
    ``junction_id -> JunctionServer`` map (only junctions with a traffic knob),
    whose ``.transits`` / ``.snapshot(when)`` back the junction queue board.

    ``items`` pairs each compiled route with its **ship key** (the transponder —
    the phantom-traffic draw is seeded by it). Junction-transit events are folded
    in **global arrival order** (tie: ship key): the earliest *ready* queue (all
    earlier queues in its own route resolved, so its arrival reflects upstream
    waits) resolves first against its junction's server, then its route's
    downstream segments shift by the wait. Returns new CompiledRoutes; a route
    with no wormhole is returned unchanged.
    """
    segs: list[list[Segment]] = [list(c.segments) for c, _ in items]
    keys = [k for _, k in items]
    masses = [(c.route.ship.mass_tons or DEFAULT_SHIP_MASS_T) for c, _ in items]
    built: dict[str, JunctionServer | None] = {}  # cache incl. knob-less (None) junctions

    # All wormhole_queue segments, by route, in order.
    queues: dict[int, list[int]] = {
        ri: [i for i, s in enumerate(route_segs) if s.kind == "wormhole_queue"]
        for ri, route_segs in enumerate(segs)
    }
    resolved: set[tuple[int, int]] = set()
    total = sum(len(v) for v in queues.values())

    while len(resolved) < total:
        # Ready queues: the earliest unresolved queue in each route (its arrival
        # reflects all prior waits). Pick the globally earliest by (arrival, key).
        ready: list[tuple[datetime, str, int, int]] = []
        for ri, idxs in queues.items():
            nxt = next((i for i in idxs if (ri, i) not in resolved), None)
            if nxt is not None:
                ready.append((segs[ri][nxt].t_start, keys[ri], ri, nxt))
        ready.sort(key=lambda r: (r[0], r[1]))
        _, _, ri, si = ready[0]

        seg = segs[ri][si]
        junction_id = seg.junction or ""
        if junction_id not in built:
            built[junction_id] = _junction_server(u, junction_id, seed)  # may be None
        server = built[junction_id]

        arrival = seg.t_start
        if server is None:
            transit_open, ahead = arrival, ()  # no knob -> instant transit
        else:
            res = server.serve(arrival, masses[ri], keys[ri])
            transit_open, ahead = res.transit_open, res.ahead_opens

        segs[ri][si] = replace(seg, t_end=transit_open, queue_ahead=ahead)
        _shift(segs[ri], si + 1, transit_open - arrival)
        resolved.add((ri, si))

    routes = [
        CompiledRoute(c.route, route_segs, final_system=c.final_system, final_body=c.final_body)
        for (c, _), route_segs in zip(items, segs, strict=True)
    ]
    servers = {jid: s for jid, s in built.items() if s is not None}
    return routes, servers


def resolve_fleet(
    items: list[tuple[CompiledRoute, str]],
    u: Universe,
    *,
    seed: int = SIM_SEED,
) -> list[CompiledRoute]:
    """Fix every open-ended ``wormhole_queue`` segment across a set of routes.

    The queue-only view of :func:`resolve_fleet_junctions` (drops the junction
    servers). See it for the folding semantics.
    """
    return resolve_fleet_junctions(items, u, seed=seed)[0]


def resolve_route(
    compiled: CompiledRoute, u: Universe, ship_key: str, *, seed: int = SIM_SEED
) -> CompiledRoute:
    """Resolve a single route's queues in isolation (phantom traffic only).

    Convenience for one-ship paths; cross-ship interleaving needs
    :func:`resolve_fleet` over all concurrently filed routes.
    """
    return resolve_fleet([(compiled, ship_key)], u, seed=seed)[0]


def ship_from_artifact(u: Universe, ship_id: str, *, max_velocity_c: float = 0.6) -> Ship:
    """Build a route :class:`Ship` from an artifact hull's effective stats.

    Pulls effective `max_g` / `max_hyper_band` / `real_cruise_velocity_c`
    (class ⊕ overrides). ``max_velocity_c`` is the n-space cap (not tracked per
    hull; defaults to 0.6c).
    """
    eff = u.effective_ship(ship_id)
    if eff is None:
        raise ValueError(f"unknown ship {ship_id!r}")
    return _ship_from_effective(eff, max_velocity_c)


def ship_from_transponder(u: Universe, transponder: str, *, max_velocity_c: float = 0.6) -> Ship:
    """Build a route :class:`Ship` from the hull squawking ``transponder``."""
    eff = u.effective_ship_by_transponder(transponder)
    if eff is None:
        raise ValueError(f"no ship with transponder {transponder!r}")
    return _ship_from_effective(eff, max_velocity_c)


def _ship_from_effective(eff: dict, max_velocity_c: float) -> Ship:
    return Ship(
        name=eff["name"],
        max_accel_g=eff["max_g"] or 200.0,
        max_velocity_c=max_velocity_c,
        max_hyper_band=eff["max_hyper_band"],
        hyper_cruise_velocity_c=eff["real_cruise_velocity_c"],
        mass_tons=eff.get("mass_tons"),
    )


def simulation_for_route(compiled: CompiledRoute, u: Universe) -> Simulation:
    """Build the discrete-event :class:`~hvsim.des.Simulation` for a route."""
    route = compiled.route
    return Simulation(
        segments=tuple(compiled.segments),
        depart_at=route.depart_at,
        origin_system=route.origin_system,
        origin_body=route.origin_body,
        final_system=compiled.final_system,
        final_body=compiled.final_body,
        resolve_body=body_resolver(u),
    )


# -- Filed-route document (the planner -> engine seam) --------------------------

FILED_ROUTE_SCHEMA = "hvsim.filed-route/v1"


class NotAtOrigin(Exception):
    """A planned route was filed for a ship not at the route's origin."""


def to_filed(route: Route, transponder: str) -> dict:
    """Serialize a route to the filed-route document the engine can reload.

    The ship is carried by **transponder** (the canonical identity); on reload it
    resolves back to effective stats via :func:`ship_from_transponder`.
    """
    return {
        "schema": FILED_ROUTE_SCHEMA,
        "ship": transponder,
        "origin": {"system": route.origin_system, "body": route.origin_body},
        "depart_at": route.depart_at.isoformat(),
        "legs": [
            {
                "mode": leg.mode,
                "to_system": leg.to_system,
                "to_body": leg.to_body,
                "layover_s": leg.layover.total_seconds(),
            }
            for leg in route.legs
        ],
    }


def from_filed(doc: dict, u: Universe) -> Route:
    """Rebuild a :class:`Route` from a filed-route document (resolving the ship)."""
    if doc.get("schema") != FILED_ROUTE_SCHEMA:
        raise ValueError(f"unexpected filed-route schema: {doc.get('schema')!r}")
    ship = ship_from_transponder(u, doc["ship"])
    legs = [
        RouteLeg(
            mode=leg["mode"],
            to_system=leg["to_system"],
            to_body=leg.get("to_body"),
            layover=timedelta(seconds=leg.get("layover_s") or 0.0),
        )
        for leg in doc["legs"]
    ]
    return Route(
        ship=ship,
        origin_system=doc["origin"]["system"],
        origin_body=doc["origin"]["body"],
        legs=legs,
        depart_at=datetime.fromisoformat(doc["depart_at"]),
    )


def fly_filed_route(
    doc: dict,
    u: Universe,
    *,
    current: Simulation | None = None,
    now: datetime | None = None,
    dev: bool = False,
) -> CompiledRoute:
    """Load and compile a filed route, enforcing the at-origin precondition.

    Unless ``dev``, a ship with an active plan (``current``) must be at the route's
    origin (a navigable point) *now* — else :class:`NotAtOrigin`. An idle ship
    (``current is None``) is accepted (its location can't be derived yet). Re-routing
    an in-motion ship is rejected (``navigable_location`` returns None).
    """
    route = from_filed(doc, u)
    if not dev and current is not None:
        at = now if now is not None else route.depart_at
        loc = current.navigable_location(at)
        if loc != (route.origin_system, route.origin_body):
            raise NotAtOrigin(
                f"ship is at {loc}, not the route origin {(route.origin_system, route.origin_body)}"
            )
    return compile_route(route, u)
