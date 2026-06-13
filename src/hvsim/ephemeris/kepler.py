"""Keplerian orbit propagation — the reusable math under the body registry.

Pure functions, no service or network. ``_orbital_to_xyz`` turns a set of
Keplerian elements + a solved mean anomaly into Cartesian coordinates (in the
same length unit as the semi-major axis); it is shared by heliocentric planet
orbits and planetocentric moon orbits. ``planet_position_m`` evaluates a planet's
**heliocentric ecliptic-J2000** position in **SI metres**.

Algorithm per the JPL approximate-positions note (see ``elements.py``). Times are
treated as UTC; TDB−UTC (~69 s in 2026) is ~1e-5 AU, negligible here.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from .elements import PLANETS

# 1 astronomical unit in metres (IAU 2012 definition).
AU_M = 1.495978707e11

_J2000_JD = 2451545.0
_DAYS_PER_CENTURY = 36525.0
_UNIX_EPOCH_JD = 2440587.5


def julian_date(when: datetime) -> float:
    """Julian Date for an instant (naive datetimes are assumed to be UTC)."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.timestamp() / 86400.0 + _UNIX_EPOCH_JD


def days_since_j2000(when: datetime) -> float:
    return julian_date(when) - _J2000_JD


def centuries_since_j2000(when: datetime) -> float:
    return days_since_j2000(when) / _DAYS_PER_CENTURY


def _solve_kepler(mean_anomaly: float, e: float) -> float:
    """Solve M = E − e·sin E for the eccentric anomaly E (radians) via Newton."""
    e_anom = mean_anomaly if e < 0.8 else math.pi
    for _ in range(64):
        delta = (e_anom - e * math.sin(e_anom) - mean_anomaly) / (1.0 - e * math.cos(e_anom))
        e_anom -= delta
        if abs(delta) < 1e-13:
            break
    return e_anom


def _orbital_to_xyz(
    a: float,
    e: float,
    incl: float,
    arg_peri: float,
    node: float,
    mean_anom: float,
) -> tuple[float, float, float]:
    """Cartesian position from Keplerian elements (radians; output in units of ``a``)."""
    e_anom = _solve_kepler(mean_anom, e)
    x_orb = a * (math.cos(e_anom) - e)
    y_orb = a * math.sqrt(1.0 - e * e) * math.sin(e_anom)

    cw, sw = math.cos(arg_peri), math.sin(arg_peri)
    co, so = math.cos(node), math.sin(node)
    ci, si = math.cos(incl), math.sin(incl)

    x = (cw * co - sw * so * ci) * x_orb + (-sw * co - cw * so * ci) * y_orb
    y = (cw * so + sw * co * ci) * x_orb + (-sw * so + cw * co * ci) * y_orb
    z = (sw * si) * x_orb + (cw * si) * y_orb
    return (x, y, z)


def planet_position_m(name: str, when: datetime) -> tuple[float, float, float]:
    """Heliocentric ecliptic-J2000 position of a planet at ``when``, in metres."""
    el = PLANETS[name]
    t = centuries_since_j2000(when)

    a = el.a + el.a_dot * t
    e = el.e + el.e_dot * t
    incl = math.radians(el.I + el.I_dot * t)
    node = math.radians(el.long_node + el.long_node_dot * t)
    long_peri = el.long_peri + el.long_peri_dot * t
    arg_peri = math.radians(long_peri) - node
    mean_anom = math.radians(((el.L + el.L_dot * t - long_peri + 180.0) % 360.0) - 180.0)

    x, y, z = _orbital_to_xyz(a, e, incl, arg_peri, node, mean_anom)
    return (x * AU_M, y * AU_M, z * AU_M)
