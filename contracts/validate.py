"""Validate the boundary contracts (run via `just contracts`).

1. Build an empty SQLite database from the universe-artifact DDL in memory — this
   proves the schema parses and its foreign keys/indexes are well-formed.
2. Lint the engine OpenAPI spec with openapi-spec-validator.

Run with the ad-hoc deps: `uv run --with openapi-spec-validator --with pyyaml
python contracts/validate.py`.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

HERE = pathlib.Path(__file__).parent
DDL = HERE / "universe-artifact" / "schema.sql"
OPENAPI = HERE / "engine-openapi.yaml"


def check_ddl() -> int:
    con = sqlite3.connect(":memory:")
    con.executescript(DDL.read_text())
    tables = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    version = con.execute("SELECT version FROM schema_meta").fetchall()
    con.close()
    # schema_meta has no row yet (the compiler inserts it); that's fine.
    print(f"  universe-artifact DDL: OK — {len(tables)} tables {tables}")
    print(f"  schema_meta rows: {len(version)} (compiler will insert version)")
    return 0


def check_openapi() -> int:
    import yaml
    from openapi_spec_validator import validate

    spec = yaml.safe_load(OPENAPI.read_text())
    validate(spec)  # raises on an invalid spec
    paths = len(spec.get("paths", {}))
    print(f"  engine OpenAPI {spec['info']['version']}: OK — {paths} paths")
    return 0


def main() -> int:
    print("Validating boundary contracts:")
    check_ddl()
    check_openapi()
    print("All contracts valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
