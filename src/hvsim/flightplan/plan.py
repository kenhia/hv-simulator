"""Compile a filed flight plan into absolute-time segments, and query it.

A :class:`FlightPlan` is *filed* (origin body, ordered waypoints, departure
time). :func:`compile_plan` walks the legs — solving a moving-target intercept
for each transit and inserting layover segments — to produce contiguous
absolute-time :class:`Segment`s. :func:`state_at` then answers "where is the
ship at time T?" by finding the segment covering T and evaluating it. There is
no simulation loop: every query is analytic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from hvsim.ephemeris import heliocentric_position
from hvsim.kinematics import ZERO, Trajectory, Vec3, solve_intercept

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
class Segment:
    """One contiguous piece of a compiled plan, in absolute time."""

    seq: int
    kind: str  # "transit" | "layover"
    t_start: datetime
    t_end: datetime
    trajectory: Trajectory | None = None  # transit only
    body: str | None = None  # layover only

    @property
    def duration_s(self) -> float:
        return (self.t_end - self.t_start).total_seconds()


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


@dataclass(frozen=True)
class ShipState:
    """Where the ship is at a queried instant (SI units)."""

    when: datetime
    position: Vec3
    velocity: Vec3
    phase: str  # "predeparture" | "transit" | "layover" | "arrived"
    segment_seq: int | None
    eta: datetime | None  # end of the current segment / overall arrival


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
            Segment(seq, "transit", when, intercept.arrival, trajectory=intercept.trajectory)
        )
        seq += 1
        when = intercept.arrival
        pos = _pos(wp.body, when)

        if wp.layover > timedelta(0):
            end = when + wp.layover
            segments.append(Segment(seq, "layover", when, end, body=wp.body))
            seq += 1
            when = end
            pos = _pos(wp.body, when)

    return CompiledPlan(plan, segments)


def state_at(compiled: CompiledPlan, when: datetime) -> ShipState:
    """Evaluate the ship's state at absolute time ``when``."""
    plan = compiled.plan
    segments = compiled.segments

    if not segments or when < plan.depart_at:
        return ShipState(when, _pos(plan.origin, when), ZERO, "predeparture", None, plan.depart_at)

    for seg in segments:
        if seg.t_start <= when < seg.t_end:
            if seg.kind == "transit":
                assert seg.trajectory is not None
                st = seg.trajectory.state((when - seg.t_start).total_seconds())
                return ShipState(when, st.position, st.velocity, "transit", seg.seq, seg.t_end)
            assert seg.body is not None
            return ShipState(when, _pos(seg.body, when), ZERO, "layover", seg.seq, seg.t_end)

    # At or past the final segment's end: docked at the last waypoint's body.
    final_body = plan.waypoints[-1].body
    return ShipState(when, _pos(final_body, when), ZERO, "arrived", None, None)
