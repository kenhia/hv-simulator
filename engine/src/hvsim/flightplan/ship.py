"""Ship — the performance envelope a flight plan is flown within."""

from __future__ import annotations

from dataclasses import dataclass

from hvsim.kinematics import SPEED_OF_LIGHT, STANDARD_GRAVITY


@dataclass(frozen=True)
class Ship:
    """A ship's identity and limits. Limits are given in human units (g, c)."""

    name: str
    max_accel_g: float
    max_velocity_c: float

    @property
    def accel_si(self) -> float:
        """Maximum acceleration in m/s²."""
        return self.max_accel_g * STANDARD_GRAVITY

    @property
    def v_cap_si(self) -> float:
        """Velocity cap in m/s."""
        return self.max_velocity_c * SPEED_OF_LIGHT
