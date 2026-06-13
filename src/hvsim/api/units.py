"""SI -> human-unit conversions for the API boundary."""

from __future__ import annotations

from hvsim.ephemeris import AU_M
from hvsim.kinematics import SPEED_OF_LIGHT, Vec3

from .schemas import PositionOut, Vector3, VelocityOut

_KM = 1.0e3


def position_out(pos: Vec3) -> PositionOut:
    r = pos.norm()
    return PositionOut(
        km=Vector3(x=pos.x / _KM, y=pos.y / _KM, z=pos.z / _KM),
        au=Vector3(x=pos.x / AU_M, y=pos.y / AU_M, z=pos.z / AU_M),
        distance_from_sun_km=r / _KM,
        distance_from_sun_au=r / AU_M,
    )


def velocity_out(vel: Vec3) -> VelocityOut:
    speed = vel.norm()
    return VelocityOut(
        km_s=Vector3(x=vel.x / _KM, y=vel.y / _KM, z=vel.z / _KM),
        speed_km_s=speed / _KM,
        fraction_c=speed / SPEED_OF_LIGHT,
    )


def human_duration(seconds: float) -> str:
    """Format a duration like '1d 9h 31m' (or '6h 0m', '45s')."""
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    days, rem = divmod(total, 86_400)
    hours, rem = divmod(rem, 3_600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if days or hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)
