"""Transponder identity: nation.class.hull resolution + the engine accessors."""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from hvsim.universe import Universe, format_transponder, parse_transponder

DDL = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "universe-artifact" / "schema.sql"


@pytest.fixture
def u(tmp_path) -> Universe:
    db = tmp_path / "u.db"
    con = sqlite3.connect(db)
    con.executescript(DDL.read_text())
    con.execute("INSERT INTO schema_meta (version) VALUES ('test')")
    con.execute("INSERT INTO nations (id,name,code,canon) VALUES ('manticore','Manticore',347,1)")
    con.execute(
        "INSERT INTO ship_classes (id,name,affiliation_nation_id,max_g,max_hyper_band,"
        "real_cruise_velocity_c,code,canon) VALUES ('nike','Nike','manticore',674,7,0.6,5,1)"
    )
    # Stock hull + an upgraded hull (override -> modified=1, shadows max_g).
    con.execute(
        "INSERT INTO ships (id,name,class_id,hull_code,modified,transponder,canon) "
        "VALUES ('hms-nike','HMS Nike','nike',1,0,'347.5.1',1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,hull_code,modified,transponder,ovr_max_g,canon) "
        "VALUES ('hms-up','HMS Upgraded','nike',2,1,'347.5.2',999,1)"
    )
    con.commit()
    con.close()
    return Universe.open(str(db))


def test_transponder_lookup(u: Universe) -> None:
    assert u.transponder("hms-nike") == "347.5.1"
    assert u.transponder("nope") is None


def test_ship_by_transponder(u: Universe) -> None:
    assert u.ship_by_transponder("347.5.1")["id"] == "hms-nike"
    assert u.ship_by_transponder("0.0.0") is None


def test_transponder_resolves_to_effective_data(u: Universe) -> None:
    eff = u.effective_ship_by_transponder("347.5.1")
    assert eff["id"] == "hms-nike" and eff["max_g"] == 674 and eff["modified"] == 0


def test_modified_hull_shadows_class(u: Universe) -> None:
    eff = u.effective_ship_by_transponder("347.5.2")
    assert eff["modified"] == 1
    assert eff["max_g"] == 999  # override wins over class's 674


def test_parse_and_format() -> None:
    assert parse_transponder("347.5.1") == (347, 5, 1)
    assert format_transponder(347, 5, 1) == "347.5.1"
    with pytest.raises(ValueError):
        parse_transponder("347.5")
