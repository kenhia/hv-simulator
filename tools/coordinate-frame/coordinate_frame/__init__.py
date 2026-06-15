"""Fabricate a galactic coordinate frame for the built systems.

Canon gives only qualitative bearings ("512 ly to the galactic north of Sol"),
never absolute coordinates. We define a frame -- **Sol at the origin, +Z galactic
north, +X galactic east** -- and place each system from its
``location`` (distance_ly + direction + reference), resolving reference chains
(Sol -> Manticore -> ...). All `canon:false`; deterministic; first-pass and
hand-tunable later. Writes a `coordinates` block into `data/systems/*.json`.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib

# Galactic compass -> unit axis. +Z north, +X east (Y reserved for future use).
_AXIS = {
    "north": (0.0, 0.0, 1.0),
    "south": (0.0, 0.0, -1.0),
    "east": (1.0, 0.0, 0.0),
    "west": (-1.0, 0.0, 0.0),
}


def _direction_unit(direction: str) -> tuple[float, float, float]:
    """Sum the compass tokens in a direction string and normalise."""
    x = y = z = 0.0
    for token in direction.replace("-", " ").lower().split():
        if token in _AXIS:
            ax, ay, az = _AXIS[token]
            x, y, z = x + ax, y + ay, z + az
    mag = math.sqrt(x * x + y * y + z * z)
    if mag == 0.0:
        return (0.0, 0.0, 1.0)  # default to galactic north
    return (x / mag, y / mag, z / mag)


def solve_frame(systems: dict[str, dict]) -> dict[str, tuple[float, float, float]]:
    """Resolve each system's XYZ (ly) from distance+direction+reference chains."""
    positions: dict[str, tuple[float, float, float]] = {"sol": (0.0, 0.0, 0.0)}
    pending = dict(systems)
    # Fixed-point: place a system once its reference is placed.
    progress = True
    while pending and progress:
        progress = False
        for sid, loc in list(pending.items()):
            ref = (loc.get("reference") or "Sol").lower()
            if ref not in positions:
                continue
            ux, uy, uz = _direction_unit(loc.get("direction") or "north")
            dist = float(loc.get("distance_ly") or 0.0)
            rx, ry, rz = positions[ref]
            positions[sid] = (rx + ux * dist, ry + uy * dist, rz + uz * dist)
            del pending[sid]
            progress = True
    if pending:
        print(f"  warning: could not place (unresolved reference): {', '.join(pending)}")
    return positions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hvsim-frame")
    parser.add_argument("--data", required=True, help="path to the data/ directory")
    args = parser.parse_args(argv)

    systems_dir = pathlib.Path(args.data) / "systems"
    docs = {p: json.loads(p.read_text()) for p in sorted(systems_dir.glob("*.json"))}
    locs = {doc["id"]: (doc.get("location") or {}) for doc in docs.values()}

    positions = solve_frame(locs)
    for path, doc in docs.items():
        pos = positions.get(doc["id"])
        if pos is None:
            continue
        ref = (doc.get("location") or {}).get("reference") or "Sol"
        doc["coordinates"] = {
            "canon": False,
            "frame": "sol-galactic-north",
            "x_ly": round(pos[0], 3),
            "y_ly": round(pos[1], 3),
            "z_ly": round(pos[2], 3),
            "notes": (
                "Fabricated (canon:false) from canon distance+bearing relative to "
                f"{ref}; Sol origin, +Z galactic north, +X galactic east."
            ),
        }
        path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"  {doc['id']:24} ({pos[0]:+.1f}, {pos[1]:+.1f}, {pos[2]:+.1f}) ly")
    print(f"placed {len(positions) - 1} systems in the Sol-galactic frame")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
