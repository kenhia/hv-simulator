"""Body registry and the recursive heliocentric position resolver.

A body is a planet, a moon (orbits a planet), or a station (rides on a parent
body at a fixed offset). ``heliocentric_position(name, when)`` resolves any of
them to a heliocentric ecliptic-J2000 position in SI metres by walking the
parent chain.

Moon orbits are modelled in the ecliptic plane with an approximate phase — see
``sprints/004-flightplan.md``: at Titan's ~1.2e6 km orbit scale this is <0.1% of
interplanetary distances and negligible for flight times. This is a clock
simulator, not a docking simulator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from .elements import PLANET_NAMES
from .kepler import _orbital_to_xyz, days_since_j2000, planet_position_m


@dataclass(frozen=True)
class Moon:
    """A moon on a (simplified, ecliptic-plane) Keplerian orbit around ``parent``."""

    parent: str
    a_m: float  # semi-major axis (metres)
    e: float
    period_days: float
    m0_deg: float = 0.0  # mean anomaly at J2000 (approximate phase)
    incl_deg: float = 0.0
    node_deg: float = 0.0
    arg_peri_deg: float = 0.0


@dataclass(frozen=True)
class Station:
    """A fixed offset (metres) from a parent body — e.g. a station in its space."""

    parent: str
    offset_m: tuple[float, float, float] = (0.0, 0.0, 0.0)


# Titan: a ≈ 1.22187e6 km, e ≈ 0.0288, period ≈ 15.945 d (phase/plane simplified).
MOONS: dict[str, Moon] = {
    "titan": Moon(parent="saturn", a_m=1.221_87e9, e=0.0288, period_days=15.945),
}

STATIONS: dict[str, Station] = {
    "titan-station": Station(parent="titan"),
}

BODIES: frozenset[str] = PLANET_NAMES | frozenset(MOONS) | frozenset(STATIONS)


def _moon_offset_m(moon: Moon, when: datetime) -> tuple[float, float, float]:
    mean_motion = 360.0 / moon.period_days  # deg/day
    mean_anom = math.radians(moon.m0_deg + mean_motion * days_since_j2000(when))
    return _orbital_to_xyz(
        moon.a_m,
        moon.e,
        math.radians(moon.incl_deg),
        math.radians(moon.arg_peri_deg),
        math.radians(moon.node_deg),
        mean_anom,
    )


def heliocentric_position(name: str, when: datetime) -> tuple[float, float, float]:
    """Heliocentric ecliptic-J2000 position of any known body at ``when``, in metres."""
    key = name.lower()
    if key in PLANET_NAMES:
        return planet_position_m(key, when)
    if key in MOONS:
        moon = MOONS[key]
        px, py, pz = heliocentric_position(moon.parent, when)
        ox, oy, oz = _moon_offset_m(moon, when)
        return (px + ox, py + oy, pz + oz)
    if key in STATIONS:
        station = STATIONS[key]
        px, py, pz = heliocentric_position(station.parent, when)
        ox, oy, oz = station.offset_m
        return (px + ox, py + oy, pz + oz)
    raise ValueError(f"unknown body {name!r}; known: {', '.join(sorted(BODIES))}")


def _kind(name: str) -> str:
    if name in PLANET_NAMES:
        return "planet"
    if name in MOONS:
        return "moon"
    return "station"


def list_bodies() -> list[dict[str, str | None]]:
    """All known bodies as ``{name, kind, parent}`` dicts, sorted by name."""
    out: list[dict[str, str | None]] = []
    for name in sorted(BODIES):
        if name in MOONS:
            parent: str | None = MOONS[name].parent
        elif name in STATIONS:
            parent = STATIONS[name].parent
        else:
            parent = None
        out.append({"name": name, "kind": _kind(name), "parent": parent})
    return out
