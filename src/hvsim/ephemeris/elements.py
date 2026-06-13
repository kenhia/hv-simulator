"""JPL approximate Keplerian elements for the major planets (1800 AD – 2050 AD).

Source: E.M. Standish, "Keplerian Elements for Approximate Positions of the
Major Planets", JPL Solar System Dynamics
(https://ssd.jpl.nasa.gov/planets/approx_pos.html), Table 1 (1800–2050 set).

Each element is given at the J2000 epoch plus a linear rate per Julian century
(36525 days). Angles are in **degrees**, the semi-major axis in **AU** — the
units of the published table. ``a`` is converted to SI only when a position is
returned (see ``kepler.py``). The 1800–2050 set needs no extra correction terms
for Jupiter–Neptune (unlike the long-span 3000 BC–3000 AD set).

Earth is represented by the **Earth–Moon barycenter** elements, as published;
the offset from Earth's centre to the barycentre (max ~4700 km ≈ 3e-5 AU) is
far below the model's own accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Elements:
    """Keplerian elements at J2000 and their per-century rates (deg, AU)."""

    a: float  # semi-major axis (AU)
    e: float  # eccentricity
    I: float  # inclination to the ecliptic (deg)  # noqa: E741
    L: float  # mean longitude (deg)
    long_peri: float  # longitude of perihelion, ϖ (deg)
    long_node: float  # longitude of ascending node, Ω (deg)

    a_dot: float
    e_dot: float
    I_dot: float
    L_dot: float
    long_peri_dot: float
    long_node_dot: float


# fmt: off
PLANETS: dict[str, Elements] = {
    "mercury": Elements(
        0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593,
        0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081),
    "venus": Elements(
        0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255,
        0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418),
    "earth": Elements(  # Earth–Moon barycenter
        1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0,
        0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0),
    "mars": Elements(
        1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891,
        0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343),
    "jupiter": Elements(
        5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909,
        -0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106),
    "saturn": Elements(
        9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448,
        -0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794),
    "uranus": Elements(
        19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503,
        -0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589),
    "neptune": Elements(
        30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574,
        0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664),
}
# fmt: on

BODIES: frozenset[str] = frozenset(PLANETS)
