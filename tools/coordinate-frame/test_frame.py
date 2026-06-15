"""Coordinate-frame: direction parsing + reference-chain placement."""

from __future__ import annotations

import math

from coordinate_frame import _direction_unit, solve_frame


def test_direction_unit() -> None:
    assert _direction_unit("galactic north") == (0.0, 0.0, 1.0)
    x, _y, z = _direction_unit("galactic north-east")
    assert x > 0 and z > 0
    assert math.isclose(math.sqrt(x * x + z * z), 1.0, abs_tol=1e-9)  # unit


def test_reference_chain_placement() -> None:
    systems = {
        "manticore": {"distance_ly": 512, "direction": "galactic north", "reference": "Sol"},
        "yeltsins-star": {
            "distance_ly": 31,
            "direction": "galactic north-east",
            "reference": "manticore",
        },
    }
    pos = solve_frame(systems)
    assert pos["manticore"] == (0.0, 0.0, 512.0)
    # Yeltsin's is placed off Manticore; ~31 ly from it (matches canon).
    mx, my, mz = pos["manticore"]
    yx, yy, yz = pos["yeltsins-star"]
    d = math.sqrt((yx - mx) ** 2 + (yy - my) ** 2 + (yz - mz) ** 2)
    assert math.isclose(d, 31.0, abs_tol=1e-6)
