"""Multi-mode interstellar routes: file legs, compile to discrete-event segments.

A :class:`Route` is an ordered list of mode-tagged :class:`RouteLeg`s from an
origin ``(system, body)``. :func:`compile_route` walks them against the
``Universe`` — reading hyper limits, band apparent velocity, inter-system
distances, and the wormhole buffer **from the artifact** — and emits the DES
:class:`~hvsim.des.Segment` sequence the core executes. Three modes:

- ``nspace`` — an in-system hop (brachistochrone/coast); the coast phase fires on
  long legs.
- ``hyper`` — a system→system leg, decomposed into **climb** out past the origin
  star's hyper limit (n-space), **hyper_cruise** across the interstellar distance
  at the band's apparent velocity, and **descent** in to the target body.
- ``wormhole`` — a junction translation: instant + the fixed safety buffer.

v1 simplifications (documented): the climb is a brachistochrone to the limit
sphere (arrives at rest, trivially within the band entry-velocity limit); a
wormhole leg fires from wherever the ship is (no explicit hop to the nexus).
Route-finding itself is Sprint 015's nav-planner; routes here are hand-filed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from hvsim.clock import T_YEAR
from hvsim.des import Segment, Simulation
from hvsim.flightplan import Ship
from hvsim.kinematics import Vec3, solve_intercept
from hvsim.kinematics.trajectory import Trajectory
from hvsim.universe import LMIN_M, LY_M, Universe, inter_system_distance, resolve_position

NSPACE, HYPER, WORMHOLE = "nspace", "hyper", "wormhole"
_ZAXIS = Vec3(0.0, 0.0, 1.0)  # arbitrary radial when a position is at the star centre


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
    band_order: int = 1  # the cruise band (Alpha by default)


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

    band = u.hyperspace_band(route.band_order)
    if band is None or band.get("apparent_velocity_c") is None:
        raise ValueError(f"band {route.band_order} has no apparent velocity")
    apparent_c = band["apparent_velocity_c"]

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
            # 1. Climb out past the origin star's hyper limit (brachistochrone).
            limit_m = (u.hyper_limit_lmin(system) or 0.0) * LMIN_M
            direction = pos.unit() if pos.norm() > 0.0 else _ZAXIS
            climb_end = direction * max(limit_m, pos.norm())
            climb = Trajectory.between(pos, climb_end, accel, v_cap)
            climb_arrival = when + timedelta(seconds=climb.duration)
            add(Segment(seq, "transit", when, climb_arrival, trajectory=climb, system=system))
            when = climb_arrival

            # 2. Hyper cruise across the interstellar distance at band speed.
            dist = inter_system_distance(u, system, leg.to_system)["distance_ly"]
            if dist is None:
                raise ValueError(f"no distance for {system} -> {leg.to_system}")
            cruise_s = dist / apparent_c * T_YEAR.total_seconds()
            cruise_end = when + timedelta(seconds=cruise_s)
            add(
                Segment(
                    seq,
                    "hyper_cruise",
                    when,
                    cruise_end,
                    from_pos=_galactic_m(u, system),
                    to_pos=_galactic_m(u, leg.to_system),
                    from_system=system,
                    to_system=leg.to_system,
                )
            )
            when, system = cruise_end, leg.to_system

            # 3. Descend from the destination's hyper limit to the target body.
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
            model = u.transit_model()
            buffer_s = (model or {}).get("buffer_normal_s") or 0.0
            end = when + timedelta(seconds=buffer_s)
            add(
                Segment(
                    seq, "wormhole_transit", when, end, from_system=system, to_system=leg.to_system
                )
            )
            when, system, pos = end, leg.to_system, Vec3(0.0, 0.0, 0.0)

        else:
            raise ValueError(f"unknown leg mode: {leg.mode!r}")

        if leg.layover > timedelta(0) and leg.to_body is not None:
            end = when + leg.layover
            add(Segment(seq, "layover", when, end, body=leg.to_body, system=system))
            when, pos = end, resolve(system, leg.to_body, end)

    final_body = next((leg.to_body for leg in reversed(route.legs) if leg.to_body), None)
    return CompiledRoute(route, segments, final_system=system, final_body=final_body)


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
