"""Ship — the performance envelope a flight plan is flown within."""

from __future__ import annotations

from dataclasses import dataclass

from hvsim.kinematics import SPEED_OF_LIGHT, STANDARD_GRAVITY


@dataclass(frozen=True)
class Ship:
    """A ship's identity and limits. Limits are given in human units (g, c).

    ``max_hyper_band`` (band order) and ``hyper_cruise_velocity_c`` (the ship's
    real velocity while cruising in hyper, per Weber's chart — warship 0.6 /
    merchant 0.5) drive interstellar speed; both default to None for a plain
    in-system ship (the route compiler falls back to a generic merchant).
    """

    name: str
    max_accel_g: float
    max_velocity_c: float
    max_hyper_band: int | None = None
    hyper_cruise_velocity_c: float | None = None
    mass_tons: float | None = None  # hull displacement; drives wormhole transit tau(M)

    @property
    def accel_si(self) -> float:
        """Maximum acceleration in m/s²."""
        return self.max_accel_g * STANDARD_GRAVITY

    @property
    def v_cap_si(self) -> float:
        """Velocity cap in m/s."""
        return self.max_velocity_c * SPEED_OF_LIGHT
