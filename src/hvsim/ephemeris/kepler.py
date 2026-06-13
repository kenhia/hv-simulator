"""Propagate Keplerian elements to a heliocentric position.

Pure functions, no service or network. Given a body name and an instant, return
its position in the **heliocentric ecliptic J2000** frame, in **SI metres**
(the project's internal unit; callers convert to AU/km at the boundary).

Pipeline: elements-at-time → mean anomaly → eccentric anomaly (Newton solve) →
position in the orbital plane → rotate into the ecliptic frame. Algorithm per
the JPL approximate-positions note (see ``elements.py`` for the source).

Times are treated as UTC. The published reference frame is TDB; TDB−UTC (~69 s
in 2026) moves Earth ~2000 km ≈ 1e-5 AU, negligible against the model's
arcminute-scale accuracy.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from .elements import BODIES, PLANETS

# 1 astronomical unit in metres (IAU 2012 definition).
AU_M = 1.495978707e11

_J2000_JD = 2451545.0
_DAYS_PER_CENTURY = 36525.0
_UNIX_EPOCH_JD = 2440587.5

__all__ = ["AU_M", "BODIES", "heliocentric_position", "julian_date"]


def julian_date(when: datetime) -> float:
    """Julian Date for an instant (naive datetimes are assumed to be UTC)."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.timestamp() / 86400.0 + _UNIX_EPOCH_JD


def _solve_kepler(mean_anomaly: float, e: float) -> float:
    """Solve M = E − e·sin E for the eccentric anomaly E (radians) via Newton."""
    e_anom = mean_anomaly if e < 0.8 else math.pi
    for _ in range(64):
        delta = (e_anom - e * math.sin(e_anom) - mean_anomaly) / (1.0 - e * math.cos(e_anom))
        e_anom -= delta
        if abs(delta) < 1e-13:
            break
    return e_anom


def heliocentric_position(body: str, when: datetime) -> tuple[float, float, float]:
    """Heliocentric ecliptic-J2000 position of ``body`` at ``when``, in metres."""
    key = body.lower()
    if key not in BODIES:
        raise ValueError(f"unknown body {body!r}; known: {', '.join(sorted(BODIES))}")
    el = PLANETS[key]

    t = (julian_date(when) - _J2000_JD) / _DAYS_PER_CENTURY

    a = el.a + el.a_dot * t
    e = el.e + el.e_dot * t
    incl = math.radians(el.I + el.I_dot * t)
    node = math.radians(el.long_node + el.long_node_dot * t)
    long_peri = el.long_peri + el.long_peri_dot * t
    arg_peri = math.radians(long_peri) - node

    mean_long = el.L + el.L_dot * t
    # Mean anomaly M = L − ϖ, wrapped to [−180°, 180°) before the solve.
    mean_anom = math.radians(((mean_long - long_peri + 180.0) % 360.0) - 180.0)
    e_anom = _solve_kepler(mean_anom, e)

    # Position in the orbital plane (AU): perifocus along +x.
    x_orb = a * (math.cos(e_anom) - e)
    y_orb = a * math.sqrt(1.0 - e * e) * math.sin(e_anom)

    cw, sw = math.cos(arg_peri), math.sin(arg_peri)
    co, so = math.cos(node), math.sin(node)
    ci, si = math.cos(incl), math.sin(incl)

    x = (cw * co - sw * so * ci) * x_orb + (-sw * co - cw * so * ci) * y_orb
    y = (cw * so + sw * co * ci) * x_orb + (-sw * so + cw * co * ci) * y_orb
    z = (sw * si) * x_orb + (cw * si) * y_orb

    return (x * AU_M, y * AU_M, z * AU_M)
