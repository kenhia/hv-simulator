"""`where-is` — print the current heliocentric position of a Sol-system body.

Examples::

    where-is saturn
    where-is mars --at 2030-01-01T00:00:00Z

Units are converted to AU and km at this boundary; the core works in SI metres.
"""

from __future__ import annotations

import argparse
import math
import os
from datetime import UTC, datetime

from hvsim.clock import SimClock
from hvsim.ephemeris import AU_M, BODIES, heliocentric_position, list_bodies

_DEFAULT_DB = os.environ.get("HVSIM_UNIVERSE_DB", "build/universe.db")


def _parse_when(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _print_pos(label: str, when: datetime, x: float, y: float, z: float) -> None:
    r = math.sqrt(x * x + y * y + z * z)
    print(f"{label} @ {when.isoformat()}")
    print(f"  position (AU): x={x / AU_M:+.6f}  y={y / AU_M:+.6f}  z={z / AU_M:+.6f}")
    print(f"  distance from primary: {r / AU_M:.6f} AU  ({r / 1e3:,.0f} km)")


def _where_in_system(system: str, body: str | None, when: datetime, db: str) -> int:
    from hvsim.universe import Universe, body_positions, star_positions  # optional dep path

    universe = Universe.open(db)
    if universe.system(system) is None:
        print(
            f"unknown system {system!r}; try one of: "
            f"{', '.join(s['id'] for s in universe.systems())}"
        )
        return 2
    positions = body_positions(universe, system, when)
    stars = star_positions(universe, system, when)
    parent = {b["id"]: b["parent_star_id"] for b in universe.bodies(system)}

    def from_star_au(bid: str) -> float:
        star = stars.get(parent.get(bid))
        return (positions[bid] - star).norm() / AU_M if star else positions[bid].norm() / AU_M

    if body:
        key = body if ":" in body else f"{system}:{body.lower()}"
        if key not in positions:
            print(f"no placeable body {key!r} in {system} (moons/undetermined orbits are skipped)")
            return 2
        v = positions[key]
        ax, ay, az = v.x / AU_M, v.y / AU_M, v.z / AU_M
        print(f"{key} @ {when.isoformat()}")
        print(f"  position (AU, system frame): ({ax:+.4f}, {ay:+.4f}, {az:+.4f})")
        print(f"  distance from parent star ({parent.get(key)}): {from_star_au(key):.6f} AU")
    else:
        print(f"{system} bodies @ {when.isoformat()} (distance from parent star):")
        for bid in sorted(positions):
            print(f"  {bid:<22} {from_star_au(bid):8.4f} AU")
    return 0


def main(argv: list[str] | None = None) -> int:
    bodies = ", ".join(sorted(BODIES))
    parser = argparse.ArgumentParser(
        prog="where-is",
        description="Position of a body — Sol (JPL) by default, or any system via --system.",
    )
    parser.add_argument("body", nargs="?", help=f"Sol body ({bodies}), or a body in --system")
    parser.add_argument("--at", metavar="ISO8601", help="UTC instant (default: now)")
    parser.add_argument("--list", action="store_true", help="list known Sol bodies and exit")
    parser.add_argument("--system", help="resolve in this universe system instead of Sol")
    parser.add_argument(
        "--universe", default=_DEFAULT_DB, help=f"artifact path (default {_DEFAULT_DB})"
    )
    args = parser.parse_args(argv)

    if args.list:
        for info in list_bodies():
            parent = f"  (orbits {info['parent']})" if info["parent"] else ""
            print(f"  {info['name']:<14} {info['kind']}{parent}")
        return 0

    when = _parse_when(args.at) if args.at else SimClock().now()

    if args.system:
        return _where_in_system(args.system, args.body, when, args.universe)

    if not args.body:
        parser.error("a body is required (or pass --list, or --system)")
    body = args.body.lower()
    if body not in BODIES:
        parser.error(f"unknown body {args.body!r}; choose from: {bodies}")
    x, y, z = heliocentric_position(body, when)
    _print_pos(body.capitalize(), when, x, y, z)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
