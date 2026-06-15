"""Compile the real dataset to a temp artifact and check structure."""

from __future__ import annotations

import pathlib
import sqlite3

from universe_compiler import compile_universe

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DDL = ROOT / "contracts" / "universe-artifact" / "schema.sql"


def test_compiles_catalog(tmp_path) -> None:
    out = tmp_path / "u.db"
    counts = compile_universe(DATA, DDL, out)
    assert counts["star_systems"] >= 4
    assert counts["bodies"] >= 20
    assert counts["ship_classes"] >= 1

    con = sqlite3.connect(out)
    # schema_meta version recorded.
    assert con.execute("SELECT version FROM schema_meta").fetchone()[0] == "0.1.1"
    # Ids are system-namespaced (no Sol/Manticore "titan" collision).
    bid = con.execute("SELECT id FROM bodies WHERE name='Manticore'").fetchone()[0]
    assert bid == "manticore:manticore"
    # Foreign keys hold (stubbed where referents are unbuilt).
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    con.close()
