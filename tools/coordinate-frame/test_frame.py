"""Coordinate-frame: direction parsing + reference-chain placement."""

from __future__ import annotations

import math
import pytest

from coordinate_frame import (
    _ARC_MAX_DEG,
    _ARC_MIN_DEG,
    _deflection_rad,
    _direction_unit,
    _jitter_rad,
    solve_frame,
)


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
    # Bearing-arc jitter rotates the direction in-plane but preserves the canon
    # distance: Manticore is still 512 ly from Sol (no longer pinned to the +Z axis).
    mx, my, mz = pos["manticore"]
    assert math.isclose(math.sqrt(mx * mx + my * my + mz * mz), 512.0, abs_tol=1e-6)
    assert my == 0.0  # Y stays reserved (in-plane rotation only)
    # Yeltsin's is placed off Manticore; ~31 ly from it (matches canon).
    yx, yy, yz = pos["yeltsins-star"]
    d = math.sqrt((yx - mx) ** 2 + (yy - my) ** 2 + (yz - mz) ** 2)
    assert math.isclose(d, 31.0, abs_tol=1e-6)


def test_jitter_is_deterministic_and_floored() -> None:
    # Stable across calls/processes (sha256-based, not salted hash()).
    assert _jitter_rad("manticore") == _jitter_rad("manticore")
    assert _jitter_rad("manticore") != _jitter_rad("basilisk")
    # Magnitude always in [3 deg, 22.5 deg]: varied, but never ~on the cardinal.
    lo, hi = math.radians(_ARC_MIN_DEG), math.radians(_ARC_MAX_DEG)
    for sid in ("sol", "manticore", "basilisk", "sigma-draconis", "trevors-star", "haven", "gregor"):
        assert lo <= abs(_jitter_rad(sid)) <= hi


def test_stored_offset_overrides_hash_with_additive_nudge() -> None:
    # An explicit bearing_offset_deg (the random-at-incorporation pick) is used
    # verbatim; bearing_nudge_deg adds on top. Both +CCW degrees.
    assert _deflection_rad("haven", {"bearing_offset_deg": 12}) == pytest.approx(math.radians(12))
    assert _deflection_rad(
        "haven", {"bearing_offset_deg": 12, "bearing_nudge_deg": 3}
    ) == pytest.approx(math.radians(15))
    # No stored offset -> the floored hash fallback.
    assert _deflection_rad("haven", {}) == _jitter_rad("haven")


def test_pure_north_systems_are_spread_off_axis() -> None:
    # Two pure-"north" systems would both land at X=0 without the arc; the jitter
    # gives each its own X so the galaxy map isn't a vertical column.
    systems = {
        "a": {"distance_ly": 500, "direction": "galactic north", "reference": "Sol"},
        "b": {"distance_ly": 500, "direction": "galactic north", "reference": "Sol"},
    }
    pos = solve_frame(systems)
    assert pos["a"][0] != 0.0 and pos["b"][0] != 0.0  # both off the +Z axis
    assert pos["a"][0] != pos["b"][0]  # and distinct from each other
    # Re-running yields identical coordinates (determinism).
    assert solve_frame(systems) == pos
