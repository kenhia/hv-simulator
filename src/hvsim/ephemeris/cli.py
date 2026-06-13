"""`where-is` — print the current heliocentric position of a Sol-system body.

Examples::

    where-is saturn
    where-is mars --at 2030-01-01T00:00:00Z

Units are converted to AU and km at this boundary; the core works in SI metres.
"""

from __future__ import annotations

import argparse
import math
from datetime import UTC, datetime

from hvsim.clock import SimClock
from hvsim.ephemeris import AU_M, BODIES, heliocentric_position, list_bodies


def _parse_when(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def main(argv: list[str] | None = None) -> int:
    bodies = ", ".join(sorted(BODIES))
    parser = argparse.ArgumentParser(
        prog="where-is",
        description="Heliocentric ecliptic-J2000 position of a Sol-system body.",
    )
    parser.add_argument("body", nargs="?", help=f"one of: {bodies}")
    parser.add_argument("--at", metavar="ISO8601", help="UTC instant (default: now)")
    parser.add_argument("--list", action="store_true", help="list known bodies and exit")
    args = parser.parse_args(argv)

    if args.list:
        for info in list_bodies():
            parent = f"  (orbits {info['parent']})" if info["parent"] else ""
            print(f"  {info['name']:<14} {info['kind']}{parent}")
        return 0

    if not args.body:
        parser.error("a body is required (or pass --list)")
    body = args.body.lower()
    if body not in BODIES:
        parser.error(f"unknown body {args.body!r}; choose from: {bodies}")

    when = _parse_when(args.at) if args.at else SimClock().now()
    x, y, z = heliocentric_position(body, when)
    r_m = math.sqrt(x * x + y * y + z * z)

    print(f"{body.capitalize()} @ {when.isoformat()}")
    print(f"  position (AU): x={x / AU_M:+.6f}  y={y / AU_M:+.6f}  z={z / AU_M:+.6f}")
    print(f"  position (km): x={x / 1e3:+.3e}  y={y / 1e3:+.3e}  z={z / 1e3:+.3e}")
    print(f"  distance from Sun: {r_m / AU_M:.6f} AU  ({r_m / 1e3:,.0f} km)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
