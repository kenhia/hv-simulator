#!/usr/bin/env python3
"""Print a markdown snapshot of the compiled universe artifact.

Used to seed accurate `docs/galaxy-changelog.md` entries (counts + system/class
lists from the artifact, not from memory). Stdlib only.

Usage: python3 tools/galaxy-summary.py build/universe.db
"""

from __future__ import annotations

import sqlite3
import sys


def summary(db_path: str) -> str:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    def count(table: str) -> int:
        return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    version = con.execute("SELECT version FROM schema_meta").fetchone()
    version = version[0] if version else "?"

    # A system is "built" if it has at least one star; otherwise it's a stub.
    with_stars = {r[0] for r in con.execute("SELECT DISTINCT system_id FROM stars")}
    systems = [r["id"] for r in con.execute("SELECT id FROM star_systems ORDER BY id")]
    built = [s for s in systems if s in with_stars]
    stubbed = [s for s in systems if s not in with_stars]
    classes = [r[0] for r in con.execute("SELECT id FROM ship_classes ORDER BY id")]

    lines = [
        f"- **Contract** v{version}",
        f"- **Systems** {len(systems)} — built ({len(built)}): {', '.join(built)}",
        f"  - stubbed ({len(stubbed)}): {', '.join(stubbed) or '—'}",
        f"- **Stars** {count('stars')} · **Bodies** {count('bodies')} · "
        f"**Belts** {count('belts')} · **Places** {count('places')}",
        f"- **Nations** {count('nations')}",
        f"- **Ship classes** {count('ship_classes')}: {', '.join(classes)}",
        f"- **Ships** {count('ships')}",
        f"- **Wormhole** junctions {count('wormhole_junctions')}, "
        f"links {count('wormhole_links')}",
        f"- **Hyperspace** bands {count('hyperspace_bands')}, "
        f"hyper-limits {count('hyper_limits')}",
    ]
    con.close()
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    db = args[0] if args else "build/universe.db"
    print(summary(db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
