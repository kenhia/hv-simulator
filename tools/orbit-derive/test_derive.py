"""Orbit-derivation: Kepler helpers + the per-system fill honor anchors."""

from __future__ import annotations

import pytest

from orbit_derive import _a_from_period, _derive_system, _period_days


def test_kepler_roundtrip() -> None:
    a = _a_from_period(1.73, 1.12)  # Manticore: 1.73 T-yr around a 1.12 M_sun star
    p_days = _period_days(a, 1.12)
    assert p_days / 365.25 == pytest.approx(1.73, rel=1e-6)


def test_manticore_anchor_in_system_doc() -> None:
    doc = {
        "id": "manticore",
        "stars": [{"id": "manticore-a", "spectral_type": "G0", "mass_solar": 1.12}],
        "bodies": [
            {
                "id": "manticore",
                "type": "planet",
                "parent_star": "manticore-a",
                "orbit_index": 3,
                "orbit": {"determined": False},
            },
            {
                "id": "sphinx",
                "type": "planet",
                "parent_star": "manticore-a",
                "orbit_index": 4,
                "orbit": {"determined": False},
            },
        ],
    }
    filled = _derive_system(doc)
    assert filled == 2
    manticore = next(b for b in doc["bodies"] if b["id"] == "manticore")
    o = manticore["orbit"]
    assert o["determined"] is True and o["canon"] is False
    assert o["period_days"] / 365.25 == pytest.approx(1.73, rel=1e-3)
    # Outer planet sits farther out than the anchor.
    sphinx = next(b for b in doc["bodies"] if b["id"] == "sphinx")
    assert sphinx["orbit"]["a_au"] > o["a_au"]


def test_fabricates_mass_when_missing() -> None:
    doc = {
        "id": "x",
        "stars": [{"id": "x-a", "spectral_type": "F6", "mass_solar": None}],
        "bodies": [
            {
                "id": "p",
                "type": "planet",
                "parent_star": "x-a",
                "orbit_index": 1,
                "orbit": {"determined": False},
            },
        ],
    }
    assert _derive_system(doc) == 1
    assert doc["bodies"][0]["orbit"]["a_au"] > 0
