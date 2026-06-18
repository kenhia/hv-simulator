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
import hashlib
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

# Artistic license (canon:false): canon gives only a coarse compass bearing, so we
# treat each cardinal as a wedge and spread systems within it. "Galactic north" =
# anywhere in the NW-NE arc about due north. Without this every pure-cardinal
# system lands on one axis (X=0 for north) and the galaxy map renders as a vertical
# column. The offset is a pure in-plane (X-Z) rotation, so canon distance is
# preserved and Y stays reserved (~0).
#
# The deflection magnitude is bounded to [_ARC_MIN, _ARC_MAX]: a >=3 deg floor so no
# system ever sits ~on the cardinal (looks unplaced), capped at 22.5 deg (half the
# 90 deg NW-NE wedge). Per Ken's #79 note: vary it per system and never repeat a
# constant angle (a fixed repeated offset looks as unnatural as all-90 deg). A new
# system stores its chosen deflection (`location.bearing_offset_deg`, random at
# incorporation, then frozen for stable coords); absent that, a stable per-id hash
# is the fallback (still varied + floored, reproducible across runs).
_ARC_MIN_DEG = 3.0
_ARC_MAX_DEG = 22.5


def _jitter_rad(system_id: str) -> float:
    """Fallback in-plane bearing deflection for a system with no stored offset.

    Stable hash of the id (not Python's per-process-salted ``hash()``) -> a signed
    magnitude in [3 deg, 22.5 deg], so it is varied per system, never ~on-axis, and
    reproducible across runs. Independent hash slices drive sign and magnitude.
    """
    h = int(hashlib.sha256(system_id.encode()).hexdigest()[:16], 16)
    mag_frac = (h & 0xFFFFFFFF) / 0xFFFFFFFF  # [0, 1]
    sign = -1.0 if (h >> 32) & 1 else 1.0
    mag = _ARC_MIN_DEG + mag_frac * (_ARC_MAX_DEG - _ARC_MIN_DEG)
    return math.radians(sign * mag)


def _deflection_rad(system_id: str, loc: dict) -> float:
    """The system's in-plane deflection: a stored ``bearing_offset_deg`` (the random-
    at-incorporation pick, frozen in data) if present, else the floored hash; plus an
    optional additive ``bearing_nudge_deg`` hand-tune. Both canon:false, +CCW."""
    base = loc.get("bearing_offset_deg")
    theta = math.radians(float(base)) if base is not None else _jitter_rad(system_id)
    return theta + math.radians(float(loc.get("bearing_nudge_deg") or 0.0))


def _rotate_in_plane(unit: tuple[float, float, float], theta: float) -> tuple[float, float, float]:
    """Rotate a unit vector by ``theta`` in the galactic plane (about the Y axis)."""
    x, y, z = unit
    c, s = math.cos(theta), math.sin(theta)
    return (x * c - z * s, y, x * s + z * c)


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
            # Deflect the placement about its reference within the bearing arc
            # (stored per-system offset or floored hash, + optional nudge); see
            # _deflection_rad. A pure in-plane rotation, so canon distance holds.
            theta = _deflection_rad(sid, loc)
            ux, uy, uz = _rotate_in_plane(_direction_unit(loc.get("direction") or "north"), theta)
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
