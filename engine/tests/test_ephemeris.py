"""Ephemeris validation.

Two kinds of checks:

1. **External reference** — positions are compared to state vectors pulled from
   JPL Horizons (heliocentric, ecliptic J2000, Sun-centred ``500@10``). These
   are the ground truth the approximate-element model is judged against.
2. **Physics invariants** — distances stay within each planet's known
   perihelion/aphelion band, Earth is nearest the Sun at northern-winter
   perihelion and farthest at July aphelion, and the function is deterministic.
   These hold independently of any fetched value.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from hvsim.ephemeris import AU_M, PLANET_NAMES, heliocentric_position

# JPL Horizons state vectors (AU), heliocentric ecliptic J2000, fetched 2026-06-13.
# Timescale is TDB; TDB-UTC (~69 s) is ~1e-5 AU, well inside tolerance.
HORIZONS_AU = {
    ("earth", "2026-01-01T00:00:00Z"): (
        -1.742814809205833e-01,
        9.677589202546031e-01,
        -5.944511017526243e-05,
    ),
    ("mars", "2026-01-01T00:00:00Z"): (
        3.405796768622151e-01,
        -1.387002015945254e00,
        -3.741722678770108e-02,
    ),
    ("saturn", "2026-01-01T00:00:00Z"): (
        9.507341652288904e00,
        2.577390400089007e-01,
        -3.829356818352184e-01,
    ),
    ("mars", "2030-01-01T00:00:00Z"): (
        1.278622087587370e00,
        -5.212680377259730e-01,
        -4.227172872477204e-02,
    ),
}

# Position tolerance vs Horizons (AU). The linear-rate approximate elements are
# good to a fraction of an arcminute for the inner planets but only ~arcminutes
# for the giants (Jupiter–Saturn mutual perturbation is not modelled), which at
# Saturn's ~9.5 AU is ~0.01 AU. Measured residuals 2026-06-13: Earth 5e-6,
# Mars 3e-4, Saturn 0.0125 AU. Tolerances bracket those with margin.
TOL_AU = {
    "mercury": 0.005,
    "venus": 0.005,
    "earth": 0.005,
    "mars": 0.005,
    "jupiter": 0.02,
    "saturn": 0.02,
    "uranus": 0.02,
    "neptune": 0.02,
}

# Heliocentric distance bands (AU): (perihelion, aphelion).
PERI_APO = {
    "mercury": (0.307, 0.467),
    "venus": (0.718, 0.728),
    "earth": (0.983, 1.017),
    "mars": (1.381, 1.666),
    "jupiter": (4.950, 5.457),
    "saturn": (9.041, 10.124),
    "uranus": (18.33, 20.11),
    "neptune": (29.81, 30.33),
}


def _at(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def _position_au(body: str, when: datetime) -> tuple[float, float, float]:
    x, y, z = heliocentric_position(body, when)
    return (x / AU_M, y / AU_M, z / AU_M)


@pytest.mark.parametrize(
    ("body", "iso", "ref"),
    [(b, t, v) for (b, t), v in HORIZONS_AU.items()],
)
def test_matches_horizons(body: str, iso: str, ref: tuple[float, float, float]) -> None:
    got = _position_au(body, _at(iso))
    error_au = math.dist(got, ref)
    assert error_au < TOL_AU[body], f"{body} @ {iso}: {error_au:.5f} AU from Horizons"


@pytest.mark.parametrize("body", sorted(PLANET_NAMES))
def test_distance_within_orbit_band(body: str) -> None:
    peri, apo = PERI_APO[body]
    r = math.dist(_position_au(body, _at("2026-01-01T00:00:00Z")), (0.0, 0.0, 0.0))
    assert peri - 0.02 <= r <= apo + 0.02, f"{body} at {r:.3f} AU outside [{peri}, {apo}]"


def test_earth_perihelion_then_aphelion() -> None:
    # Earth reaches perihelion in early January, aphelion in early July.
    r_jan = math.dist(_position_au("earth", _at("2026-01-03T00:00:00Z")), (0, 0, 0))
    r_jul = math.dist(_position_au("earth", _at("2026-07-04T00:00:00Z")), (0, 0, 0))
    assert r_jan < 0.9846
    assert r_jul > 1.0156
    assert r_jan < r_jul


def test_deterministic() -> None:
    when = _at("2027-05-05T12:00:00Z")
    assert heliocentric_position("jupiter", when) == heliocentric_position("jupiter", when)


def test_naive_datetime_treated_as_utc() -> None:
    naive = datetime(2026, 1, 1)  # intentional naive datetime: should be read as UTC
    aware = datetime(2026, 1, 1, tzinfo=UTC)
    assert heliocentric_position("mars", naive) == heliocentric_position("mars", aware)


def test_unknown_body_raises() -> None:
    with pytest.raises(ValueError, match="unknown body"):
        heliocentric_position("pluto", _at("2026-01-01T00:00:00Z"))
