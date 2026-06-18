"""Universe artifact loading + binary-aware placement.

Self-contained: builds a tiny artifact from the contract DDL and inserts a
binary system (Manticore-like) and a single-star system, then checks the
ephemeris places stars and planets sensibly. No dependency on the compiler tool.
"""

from __future__ import annotations

import pathlib
import sqlite3
from datetime import UTC, datetime

import pytest

from hvsim.universe import (
    AU_M,
    LMIN_M,
    Universe,
    body_positions,
    inter_system_distance,
    resolve_position,
    star_positions,
)

DDL = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "universe-artifact" / "schema.sql"
WHEN = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def artifact_path(tmp_path) -> str:
    db = tmp_path / "u.db"
    con = sqlite3.connect(db)
    con.executescript(DDL.read_text())
    con.execute("INSERT INTO schema_meta (version) VALUES ('test')")

    def add_system(sid: str, name: str, binary: int) -> None:
        con.execute(
            "INSERT INTO star_systems (id,name,canon,is_binary) VALUES (?,?,1,?)",
            (sid, name, binary),
        )

    def add_star(sid: str, system: str, role: str, mass: float) -> None:
        con.execute(
            "INSERT INTO stars (id,system_id,name,role,mass_solar,canon) VALUES (?,?,?,?,?,1)",
            (sid, system, sid, role, mass),
        )

    def add_planet(sid: str, system: str, star: str, a_au: float, period: float) -> None:
        con.execute(
            "INSERT INTO bodies (id,system_id,parent_star_id,name,type,orbit_index,canon,"
            "orbit_determined,a_au,e,i_deg,l_deg,long_peri_deg,long_node_deg,period_days) "
            "VALUES (?,?,?,?,'planet',3,1,1,?,0.0,0,0,0,0,?)",
            (sid, system, star, sid, a_au, period),
        )

    # Binary system (Manticore numbers) + a planet around the primary.
    add_system("manticore", "Manticore", 1)
    con.execute(
        "INSERT INTO binaries (system_id,eccentricity,barycenter_a_lmin,barycenter_b_lmin,"
        "separation_periastron_lmin,separation_apastron_lmin,canon) VALUES (?,?,?,?,?,?,1)",
        ("manticore", 0.12, 333, 406, 650, 827),
    )
    add_star("manticore:a", "manticore", "primary", 1.12)
    add_star("manticore:b", "manticore", "secondary", 0.92)
    add_planet("manticore:manticore", "manticore", "manticore:a", 1.5, 632)

    # Single-star system + a planet.
    add_system("yeltsin", "Yeltsin", 0)
    add_star("yeltsin:s", "yeltsin", "primary", 1.3)
    add_planet("yeltsin:grayson", "yeltsin", "yeltsin:s", 1.62, 650)

    # Galactic-frame coordinates + a wormhole junction/link.
    con.execute(
        "UPDATE star_systems SET coord_x_ly=0,coord_y_ly=0,coord_z_ly=512 WHERE id='manticore'"
    )
    con.execute(
        "UPDATE star_systems SET coord_x_ly=21.9,coord_y_ly=0,coord_z_ly=533.9 WHERE id='yeltsin'"
    )
    con.execute(
        "INSERT INTO wormhole_junctions (id,name,host_system_id,canon) VALUES (?,?,?,1)",
        ("mj", "Manticore Junction", "manticore"),
    )
    con.execute(
        "INSERT INTO wormhole_links (id,junction_id,from_system_id,to_system_id,distance_ly,"
        "transit,canon) VALUES (?,?,?,?,?,?,1)",
        ("wl", "mj", "manticore", "yeltsin", 99, "instant"),
    )

    con.commit()
    con.close()
    return str(db)


@pytest.fixture
def universe(artifact_path: str) -> Universe:
    return Universe.open(artifact_path)


def test_binary_separation_in_canon_range(universe: Universe) -> None:
    sp = star_positions(universe, "manticore", WHEN)
    ra = sp["manticore:a"].norm()
    rb = sp["manticore:b"].norm()
    sep_lmin = (sp["manticore:a"] - sp["manticore:b"]).norm() / LMIN_M
    assert 650.0 <= sep_lmin <= 827.0
    # Phase-independent invariants: stars are collinear through the barycenter
    # (the parts sum to the separation) and split by inverse mass ratio.
    assert (ra + rb) / LMIN_M == pytest.approx(sep_lmin, rel=1e-9)
    assert ra / rb == pytest.approx(0.92 / 1.12, rel=1e-6)


def test_planet_orbits_its_star(universe: Universe) -> None:
    sp = star_positions(universe, "manticore", WHEN)
    bp = body_positions(universe, "manticore", WHEN)
    dist_au = (bp["manticore:manticore"] - sp["manticore:a"]).norm() / AU_M
    assert dist_au == pytest.approx(1.5, abs=1e-6)  # e=0 -> exactly a


def test_single_star_planet(universe: Universe) -> None:
    bp = body_positions(universe, "yeltsin", WHEN)
    assert bp["yeltsin:grayson"].norm() / AU_M == pytest.approx(1.62, abs=1e-6)


def test_resolver_and_determinism(universe: Universe) -> None:
    a = resolve_position(universe, "manticore", "manticore:manticore", WHEN)
    b = resolve_position(universe, "manticore", "manticore:manticore", WHEN)
    assert a == b and a is not None
    # Sol still routes to the JPL ephemeris (no universe needed).
    assert resolve_position(universe, "sol", "saturn", WHEN) is not None
    # The map/UI sends namespaced ``sol:body`` ids (e.g. from /systems/sol/bodies);
    # Sol's ephemeris keys on the bare name, so the prefix is stripped (both work).
    assert resolve_position(universe, "sol", "sol:saturn", WHEN) == resolve_position(
        universe, "sol", "saturn", WHEN
    )


def test_inter_system_distance(universe: Universe) -> None:
    # Directly wormhole-linked -> canon span.
    canon = inter_system_distance(universe, "manticore", "yeltsin")
    assert canon["method"] == "wormhole-canon"
    assert canon["distance_ly"] == 99
    # Not linked -> frame Euclidean (Sol is the origin).
    frame = inter_system_distance(universe, "sol", "manticore")
    assert frame["method"] == "frame"
    assert frame["distance_ly"] == pytest.approx(512.0, abs=0.1)


def test_systems_endpoints(artifact_path: str) -> None:
    from fastapi.testclient import TestClient

    from hvsim.api.app import create_app

    client = TestClient(create_app(database_url="sqlite://", universe_db=artifact_path))
    systems = client.get("/systems").json()
    assert {"manticore", "yeltsin"} <= {s["id"] for s in systems}
    assert next(s for s in systems if s["id"] == "manticore")["coordinates"]["z_ly"] == 512
    bodies = client.get("/systems/manticore/bodies").json()
    assert any(b["id"] == "manticore:manticore" for b in bodies)
    assert client.get("/systems/nope/bodies").status_code == 404
    assert len(client.get("/wormholes").json()) == 1
    assert len(client.get("/junctions").json()) == 1
    dist = client.get("/systems/manticore/distance/yeltsin").json()
    assert dist["distance_ly"] == 99 and dist["method"] == "wormhole-canon"
