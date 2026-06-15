"""3-D straight-chord trajectories and the moving-target intercept.

A :class:`Trajectory` wraps a 1-D :class:`Profile` along the unit vector from
start to end, so ``state(t)`` yields position/velocity/acceleration vectors in
SI units. :func:`solve_intercept` handles a destination that *moves* during the
trip (a planet) by fixed-point iteration on the arrival time.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from .profile import Profile, solve_profile
from .vector import ZERO, Vec3


@dataclass(frozen=True)
class State:
    """Kinematic state at an instant (SI: metres, m/s, m/s²)."""

    position: Vec3
    velocity: Vec3
    acceleration: Vec3


@dataclass(frozen=True)
class Trajectory:
    """A flip-and-burn run along the straight chord from ``origin`` toward ``direction``."""

    origin: Vec3
    direction: Vec3  # unit vector (ZERO for a zero-length trip)
    profile: Profile

    @classmethod
    def between(cls, start: Vec3, end: Vec3, accel: float, v_max: float) -> Trajectory:
        delta = end - start
        dist = delta.norm()
        direction = delta.unit() if dist > 0.0 else ZERO
        return cls(start, direction, solve_profile(dist, accel, v_max))

    @property
    def duration(self) -> float:
        return self.profile.t_total

    def state(self, t: float) -> State:
        s, v, a = self.profile.state(t)
        return State(self.origin + self.direction * s, self.direction * v, self.direction * a)


@dataclass(frozen=True)
class Intercept:
    """Result of a moving-target solve."""

    trajectory: Trajectory
    arrival: datetime
    iterations: int


def solve_intercept(
    start: Vec3,
    target_at: Callable[[datetime], Vec3],
    depart: datetime,
    accel: float,
    v_max: float,
    *,
    tol_s: float = 1e-3,
    max_iter: int = 32,
) -> Intercept:
    """Solve when/where to meet a moving target.

    ``target_at(when)`` returns the target's position at any time (e.g. wrapping
    the ephemeris). Iterate: estimate trip time to where the target is, advance
    the target to that arrival time, re-solve — until the trip time stops moving
    by more than ``tol_s``. Converges in 2–3 steps because the target's speed is
    tiny next to the ship's. Raises if it fails to converge.
    """
    t_trip = Trajectory.between(start, target_at(depart), accel, v_max).duration
    for i in range(1, max_iter + 1):
        target = target_at(depart + timedelta(seconds=t_trip))
        traj = Trajectory.between(start, target, accel, v_max)
        if abs(traj.duration - t_trip) <= tol_s:
            return Intercept(traj, depart + timedelta(seconds=traj.duration), i)
        t_trip = traj.duration
    raise RuntimeError(f"intercept did not converge in {max_iter} iterations")
