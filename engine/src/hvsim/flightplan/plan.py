"""Compile a filed flight plan into absolute-time segments, and query it.

A :class:`FlightPlan` is *filed* (origin body, ordered waypoints, departure
time). :func:`compile_plan` walks the legs — solving a moving-target intercept
for each transit and inserting layover segments — to produce contiguous
absolute-time :class:`Segment`s. :func:`state_at` answers "where is the ship at
time T?" by executing those segments on the discrete-event core
(:mod:`hvsim.des`): replay boundary events up to T, then evaluate the active
segment analytically. There is no simulation loop — events are sparse, one per
segment boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from hvsim.des import Segment, ShipState, Simulation
from hvsim.ephemeris import heliocentric_position
from hvsim.kinematics import Vec3, solve_intercept

from .ship import Ship


def _pos(body: str, when: datetime) -> Vec3:
    return Vec3(*heliocentric_position(body, when))


@dataclass(frozen=True)
class Waypoint:
    """A destination body and how long to stay after arriving."""

    body: str
    layover: timedelta = timedelta(0)


@dataclass(frozen=True)
class FlightPlan:
    """A filed plan: depart ``origin`` at ``depart_at``, visit ``waypoints`` in order."""

    ship: Ship
    origin: str
    waypoints: list[Waypoint]
    depart_at: datetime


@dataclass(frozen=True)
class CompiledPlan:
    """A filed plan plus its solved segments."""

    plan: FlightPlan
    segments: list[Segment] = field(default_factory=list)

    @property
    def depart_at(self) -> datetime:
        return self.plan.depart_at

    @property
    def arrival(self) -> datetime:
        return self.segments[-1].t_end if self.segments else self.plan.depart_at


def compile_plan(plan: FlightPlan) -> CompiledPlan:
    """Compile ``plan`` into contiguous absolute-time segments."""
    accel, v_cap = plan.ship.accel_si, plan.ship.v_cap_si
    when = plan.depart_at
    pos = _pos(plan.origin, when)

    segments: list[Segment] = []
    seq = 0
    for wp in plan.waypoints:
        intercept = solve_intercept(pos, lambda t, b=wp.body: _pos(b, t), when, accel, v_cap)
        segments.append(
            Segment(
                seq,
                "transit",
                when,
                intercept.arrival,
                trajectory=intercept.trajectory,
                system="sol",
            )
        )
        seq += 1
        when = intercept.arrival
        pos = _pos(wp.body, when)

        if wp.layover > timedelta(0):
            end = when + wp.layover
            segments.append(Segment(seq, "layover", when, end, body=wp.body, system="sol"))
            seq += 1
            when = end
            pos = _pos(wp.body, when)

    return CompiledPlan(plan, segments)


def simulation_for(compiled: CompiledPlan) -> Simulation:
    """Build the discrete-event :class:`~hvsim.des.Simulation` for a plan.

    Single-system Sol plan: positions resolve via the Sol JPL ephemeris (the
    default body resolver), so ``system`` is ``"sol"`` throughout.
    """
    plan = compiled.plan
    final_body = plan.waypoints[-1].body if plan.waypoints else plan.origin
    return Simulation(
        segments=tuple(compiled.segments),
        depart_at=plan.depart_at,
        origin_system="sol",
        origin_body=plan.origin,
        final_system="sol",
        final_body=final_body,
    )


def state_at(compiled: CompiledPlan, when: datetime) -> ShipState:
    """Evaluate the ship's state at absolute time ``when`` via the DES core."""
    return simulation_for(compiled).state(when)
