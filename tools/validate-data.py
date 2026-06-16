#!/usr/bin/env python3
"""Validate the authored Honorverse dataset before it's compiled.

Source-data linter (stdlib only) — catches authoring mistakes early and in
`just check`, without needing to compile the artifact. Currently checks ship
identity: every ship resolves to a class, carries a `hull_code`, and the visible
transponder triple `nation.class.hull` is **unique** (no double-assigned hulls).
Add further integrity checks here as the dataset grows.

Usage: python3 tools/validate-data.py [data_dir]   (default: data)
Exit code 0 = clean, 1 = errors found.
"""

from __future__ import annotations

import json
import pathlib
import sys


def validate(data_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []

    codes = json.loads((data_dir / "transponder-codes.json").read_text())
    nation_codes: dict = codes.get("nations", {})
    class_codes: dict = codes.get("classes", {})

    classes = {c["id"]: c for c in json.loads((data_dir / "ships/ship-classes.json").read_text())["classes"]}
    ships = json.loads((data_dir / "ships/ships.json").read_text())["ships"]

    # Nation codes must be unique (transponders are identities).
    seen_nation: dict[int, str] = {}
    for nid, code in nation_codes.items():
        if code in seen_nation:
            errors.append(f"nation code {code} reused by {nid!r} and {seen_nation[code]!r}")
        seen_nation[code] = nid

    # Class codes must be unique within a nation.
    by_nation_class: dict[tuple[str | None, int], str] = {}
    for cid, cls in classes.items():
        if cid not in class_codes:
            errors.append(f"class {cid!r} has no transponder code in transponder-codes.json")
            continue
        nat = cls.get("affiliation_nation_id")
        key = (nat, class_codes[cid])
        if key in by_nation_class:
            errors.append(
                f"class code {class_codes[cid]} reused within nation {nat!r}: "
                f"{cid!r} and {by_nation_class[key]!r}"
            )
        by_nation_class[key] = cid

    # Ships: resolvable class, present hull_code, unique transponder triple.
    triples: dict[str, str] = {}
    for s in ships:
        sid, cid = s["id"], s.get("class_id")
        if not cid:
            continue  # classless -> compiler makes a singleton; nothing to check here
        if cid not in classes:
            errors.append(f"ship {sid!r} references unknown class {cid!r}")
            continue
        hull = s.get("hull_code")
        if not isinstance(hull, int) or hull < 1:
            errors.append(f"ship {sid!r} has a missing/invalid hull_code ({hull!r})")
            continue
        nat = classes[cid].get("affiliation_nation_id")
        ncode = nation_codes.get(nat, 0) if nat else 0
        ccode = class_codes.get(cid)
        triple = f"{ncode}.{ccode}.{hull}"
        if triple in triples:
            errors.append(
                f"duplicate transponder {triple}: {sid!r} collides with {triples[triple]!r}"
            )
        triples[triple] = sid

    return errors


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    data_dir = pathlib.Path(args[0]) if args else pathlib.Path("data")
    errors = validate(data_dir)
    if errors:
        print(f"data validation FAILED ({len(errors)} error(s)):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("data OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
