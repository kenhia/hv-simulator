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
    assert con.execute("SELECT version FROM schema_meta").fetchone()[0] == "0.3.0"
    # Ids are system-namespaced (no Sol/Manticore "titan" collision).
    bid = con.execute("SELECT id FROM bodies WHERE name='Manticore'").fetchone()[0]
    assert bid == "manticore:manticore"
    # Foreign keys hold (stubbed where referents are unbuilt).
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    # Hyperspace band model (Weber chart) compiled: Theta multiplier 5000.
    theta = con.execute(
        "SELECT velocity_multiplier FROM hyperspace_bands WHERE name='Theta'"
    ).fetchone()[0]
    assert theta == 5000
    assert con.execute("SELECT count(*) FROM hyperspace_model").fetchone()[0] == 1
    # Every class got a max_hyper_band; warships cruise 0.6c, merchants 0.5c.
    assert con.execute("SELECT count(*) FROM ship_classes WHERE max_hyper_band IS NULL").fetchone()[
        0
    ] == 0
    # Every ship resolves to a class (NOT NULL class_id holds).
    assert con.execute("SELECT count(*) FROM ships WHERE class_id IS NULL").fetchone()[0] == 0
    # Transponders: every ship has one, all distinct; flavored nation codes.
    n_ships = con.execute("SELECT count(*) FROM ships").fetchone()[0]
    assert con.execute("SELECT count(*) FROM ships WHERE transponder IS NOT NULL").fetchone()[
        0
    ] == n_ships
    assert con.execute("SELECT count(DISTINCT transponder) FROM ships").fetchone()[0] == n_ships
    assert con.execute("SELECT code FROM nations WHERE id='solarian-league'").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM nations WHERE code IS NULL").fetchone()[0] == 0
    con.close()


def test_transponder_modified_and_validation(tmp_path) -> None:
    """_assign_transponders derives modified from ovr_* and rejects missing codes."""
    import pytest

    from universe_compiler import _assign_transponders

    con = sqlite3.connect(tmp_path / "t.db")
    con.executescript(DDL.read_text())
    con.execute("INSERT INTO nations (id,name,canon) VALUES ('n','N',1)")
    con.execute("INSERT INTO ship_classes (id,name,affiliation_nation_id,canon) VALUES ('c','C','n',1)")
    con.execute("INSERT INTO ships (id,name,class_id,canon) VALUES ('s1','S1','c',1)")
    con.execute(
        "INSERT INTO ships (id,name,class_id,ovr_max_g,canon) VALUES ('s2','S2','c',999,1)"
    )
    codes = {"nations": {"n": 42}, "classes": {"c": 3}}
    _assign_transponders(con, codes)
    rows = dict(con.execute("SELECT id, transponder FROM ships").fetchall())
    assert rows["s1"] == "42.3.1" and rows["s2"] == "42.3.2"
    mods = dict(con.execute("SELECT id, modified FROM ships").fetchall())
    assert mods["s1"] == 0 and mods["s2"] == 1  # s2 has an override

    # A nation without a registered code is a build error.
    con.execute("INSERT INTO nations (id,name,canon) VALUES ('m','M',1)")
    with pytest.raises(ValueError, match="no transponder code"):
        _assign_transponders(con, codes)
    con.close()


def test_singleton_class_for_classless_ship(tmp_path) -> None:
    """A ship filed without a class gets an auto-created singleton class."""
    import json

    from universe_compiler import _load_ship_classes, _load_ships

    con = sqlite3.connect(tmp_path / "s.db")
    con.executescript(DDL.read_text())
    _load_ship_classes(con, {"classes": []})
    _load_ships(con, {"ships": [{"id": "lone-ship", "name": "Lone Ship"}]})
    row = con.execute(
        "SELECT class_id FROM ships WHERE id='lone-ship'"
    ).fetchone()
    assert row[0] == "lone-ship-class"
    cls = con.execute(
        "SELECT name, singleton FROM ship_classes WHERE id='lone-ship-class'"
    ).fetchone()
    assert cls == ("Lone Ship class", 1)
    con.close()


def test_unknown_class_is_rejected(tmp_path) -> None:
    import pytest

    from universe_compiler import _load_ship_classes, _load_ships

    con = sqlite3.connect(tmp_path / "x.db")
    con.executescript(DDL.read_text())
    _load_ship_classes(con, {"classes": []})
    with pytest.raises(ValueError, match="unknown class"):
        _load_ships(con, {"ships": [{"id": "s1", "name": "S1", "class_id": "ghost"}]})
    con.close()
