"""1-D motion profile along a straight chord of length ``distance``.

Constant-magnitude acceleration with a velocity cap, in one dimension. Two
shapes:

- **brachistochrone** — accelerate to the midpoint, flip, decelerate. Used when
  the peak speed ``√(a·d)`` stays under the cap (always true in-system).
- **accel–coast–decel** — accelerate to ``v_max``, coast, decelerate. Used when
  the brachistochrone peak would exceed the cap (only on very long legs).

Pure and closed-form: ``Profile.state(t)`` evaluates kinematics at any elapsed
time analytically — no integration, no loop.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    """A solved 1-D trip. Times in seconds, distances in metres, accel in m/s²."""

    distance: float
    accel: float
    v_max: float
    v_peak: float  # speed reached at flip / during coast
    t_accel: float  # duration of the accel phase (== decel phase)
    t_coast: float  # duration of the coast phase (0 for a brachistochrone)

    @property
    def t_total(self) -> float:
        return 2.0 * self.t_accel + self.t_coast

    @property
    def coasts(self) -> bool:
        return self.t_coast > 0.0

    def state(self, t: float) -> tuple[float, float, float]:
        """Return ``(distance_travelled, speed, signed_accel)`` at elapsed ``t``.

        ``t`` is clamped to ``[0, t_total]``. ``signed_accel`` is +accel while
        speeding up, 0 while coasting, −accel while slowing down.
        """
        t = min(max(t, 0.0), self.t_total)
        a = self.accel
        d_accel = 0.5 * a * self.t_accel * self.t_accel

        if t <= self.t_accel:
            return (0.5 * a * t * t, a * t, a)

        t_in = t - self.t_accel
        if t_in <= self.t_coast:
            return (d_accel + self.v_peak * t_in, self.v_peak, 0.0)

        t_dec = t_in - self.t_coast
        d_coast = self.v_peak * self.t_coast
        s = d_accel + d_coast + self.v_peak * t_dec - 0.5 * a * t_dec * t_dec
        return (s, self.v_peak - a * t_dec, -a)


def solve_profile(distance: float, accel: float, v_max: float) -> Profile:
    """Solve the fastest flip-and-burn profile over ``distance`` (≥ 0)."""
    if distance < 0.0:
        raise ValueError(f"distance must be non-negative, got {distance}")
    if accel <= 0.0 or v_max <= 0.0:
        raise ValueError(f"accel and v_max must be positive, got {accel}, {v_max}")

    if distance == 0.0:
        return Profile(0.0, accel, v_max, 0.0, 0.0, 0.0)

    v_brach = math.sqrt(accel * distance)  # peak speed if a pure brachistochrone
    if v_brach <= v_max:
        return Profile(distance, accel, v_max, v_brach, v_brach / accel, 0.0)

    # Brachistochrone peak would breach the cap: insert a coast at v_max.
    t_accel = v_max / accel
    d_ramp = v_max * v_max / (2.0 * accel)  # distance covered accelerating (each end)
    t_coast = (distance - 2.0 * d_ramp) / v_max
    return Profile(distance, accel, v_max, v_max, t_accel, t_coast)
