"""Fill first-pass Keplerian orbits for Honorverse system bodies.

Canon fixes planet *order* but almost no *geometry*, so we fabricate plausible
in-system orbits (all `canon: false`, `determined: true`) so the engine can place
bodies. Where canon gives an anchor (Manticore's 1.73 T-year; Grayson/Medusa
distances in light-minutes) we honor it and space the rest geometrically.

Writes back to the `data/systems/*.json` source. Deterministic and idempotent.
Planets only this pass (moons stay undetermined). Refine or hand-tune later;
the canon flag keeps the fabrication visible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib

AU_M = 1.495978707e11
LMIN_M = 1.798754748e10

# Fabricated main-sequence mass (M_sun) by spectral class, for stars canon leaves
# without a mass. Coarse; flagged via the orbit canon=false downstream.
_CLASS_MASS = {"O": 16, "B": 4, "A": 1.7, "F": 1.3, "G": 1.0, "K": 0.75, "M": 0.4}

# Per-system anchors: body_id -> ("period_yr"|"a_lm", value). Canon distances.
_ANCHORS: dict[str, dict[str, tuple[str, float]]] = {
    "manticore": {"manticore": ("period_yr", 1.73)},
    "yeltsins-star": {"grayson": ("a_lm", 13.5)},
    "basilisk": {"medusa": ("a_lm", 7.0)},
    "endicott": {"masada": ("a_lm", 3.4)},  # canon: "~1/4 of Grayson"
}

_RATIO = 1.6  # geometric spacing between successive planet orbits (Titius-Bode-ish)
_BASE_INNER_AU = 0.4  # innermost-planet fallback when a star's set has no anchor


def _star_mass(star: dict) -> float:
    if star.get("mass_solar"):
        return float(star["mass_solar"])
    cls = (star.get("spectral_type") or "G")[0].upper()
    return _CLASS_MASS.get(cls, 1.0)


def _a_from_period(period_yr: float, mass_solar: float) -> float:
    return (mass_solar * period_yr * period_yr) ** (1.0 / 3.0)


def _period_days(a_au: float, mass_solar: float) -> float:
    return 365.25 * math.sqrt(a_au**3 / mass_solar)


def _anchor_a_au(kind: str, value: float, mass_solar: float) -> float:
    if kind == "period_yr":
        return _a_from_period(value, mass_solar)
    return value * LMIN_M / AU_M  # a_lm


def _derive_system(doc: dict) -> int:
    """Fill planet orbits in one system doc. Returns count filled."""
    sys_id = doc["id"]
    stars = {s["id"]: s for s in doc.get("stars", [])}
    anchors = _ANCHORS.get(sys_id, {})
    filled = 0

    # Group planets by their parent star, in orbit order.
    by_star: dict[str, list[dict]] = {}
    for body in doc.get("bodies", []):
        if body.get("type") != "planet":
            continue
        by_star.setdefault(body.get("parent_star", ""), []).append(body)

    for star_id, planets in by_star.items():
        planets.sort(key=lambda b: b.get("orbit_index") or 0)
        mass = _star_mass(stars.get(star_id, {}))

        # Establish the a-scale: anchor if this star's set has one, else fallback.
        anchor_idx = anchor_a = None
        for p in planets:
            if p["id"] in anchors:
                kind, val = anchors[p["id"]]
                anchor_idx = p.get("orbit_index") or 1
                anchor_a = _anchor_a_au(kind, val, mass)
                break

        for p in planets:
            idx = p.get("orbit_index") or 1
            if anchor_a is not None:
                a_au = anchor_a * (_RATIO ** (idx - anchor_idx))
            else:
                a_au = _BASE_INNER_AU * (_RATIO ** (idx - 1))

            # Deterministic, gently varied non-circular/inclined placement + phase.
            e = round(0.01 + 0.005 * (idx % 4), 4)
            i_deg = round(0.4 * (idx % 5), 3)
            long_node = float((idx * 53) % 360)
            long_peri = float((idx * 97) % 360)
            seed = hashlib.md5(f"{sys_id}:{p['id']}".encode()).hexdigest()  # stable phase, not security
            l_deg = float(int(seed, 16) % 360)

            p["orbit"] = {
                "canon": False,
                "determined": True,
                "a_au": round(a_au, 6),
                "e": e,
                "i_deg": i_deg,
                "L_deg": round(l_deg, 3),
                "long_peri_deg": long_peri,
                "long_node_deg": long_node,
                "period_days": round(_period_days(a_au, mass), 3),
                "notes": (
                    "Fabricated by orbit-derive (canon:false): "
                    + ("anchored on canon distance/period; " if p["id"] in anchors else "geometric spacing; ")
                    + f"star mass {mass} M_sun"
                    + ("" if stars.get(star_id, {}).get("mass_solar") else " (mass fabricated from spectral class)")
                    + "."
                ),
            }
            filled += 1
    return filled


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hvsim-derive-orbits")
    parser.add_argument("--data", required=True, help="path to the data/ directory")
    args = parser.parse_args(argv)

    systems_dir = pathlib.Path(args.data) / "systems"
    total = 0
    for path in sorted(systems_dir.glob("*.json")):
        doc = json.loads(path.read_text())
        n = _derive_system(doc)
        path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"  {path.name}: filled {n} planet orbits")
        total += n
    print(f"derived {total} planet orbits across {len(list(systems_dir.glob('*.json')))} systems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
