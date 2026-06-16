"""Galaxy fleet API: file a planner route (by transponder), fly it, board it."""

from __future__ import annotations

import pathlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

from hvsim.api.app import create_app

DDL = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "universe-artifact" / "schema.sql"

# A filed route for war-1 (transponder 1.1.1): alpha -> beta(hyper) -> gamma(wormhole) -> body.
DEPART = "1890-01-01T00:00:00+00:00"
ROUTE = {
    "schema": "hvsim.filed-route/v1",
    "ship": "1.1.1",
    "origin": {"system": "alpha", "body": "alpha:p1"},
    "depart_at": DEPART,
    "legs": [
        {"mode": "hyper", "to_system": "beta"},
        {"mode": "wormhole", "to_system": "gamma"},
        {"mode": "hyper", "to_system": "gamma", "to_body": "gamma:p1"},
    ],
}


@pytest.fixture
def artifact_path(tmp_path) -> str:
    db = tmp_path / "u.db"
    con = sqlite3.connect(db)
    con.executescript(DDL.read_text())
    con.execute("INSERT INTO schema_meta (version) VALUES ('test')")

    def system(sid, z):
        con.execute(
            "INSERT INTO star_systems (id,name,canon,is_binary,coord_x_ly,coord_y_ly,coord_z_ly) "
            "VALUES (?,?,1,0,0,0,?)",
            (sid, sid, z),
        )
        con.execute(
            "INSERT INTO stars (id,system_id,name,role,mass_solar,hyper_limit_lmin,canon) "
            "VALUES (?,?,?,'primary',1.0,20.0,1)",
            (f"{sid}:s", sid, sid),
        )
        con.execute(
            "INSERT INTO bodies (id,system_id,parent_star_id,name,type,orbit_index,canon,"
            "orbit_determined,a_au,e,i_deg,l_deg,long_peri_deg,long_node_deg,period_days) "
            "VALUES (?,?,?,?,'planet',3,1,1,1.0,0,0,0,0,0,365.25)",
            (f"{sid}:p1", sid, f"{sid}:s", sid),
        )

    system("alpha", 0.0)
    system("beta", 40.0)
    system("gamma", 71.0)
    for order, name, mult in [(4, "Delta", 2178), (7, "Eta", 4294)]:
        con.execute(
            "INSERT INTO hyperspace_bands (band_order,name,velocity_multiplier,multiplier_canon,"
            "translation_bleed_off_pct,bleed_off_canon,unattainable,canon) "
            "VALUES (?,?,?,1,60,1,0,1)",
            (order, name, mult),
        )
    con.execute(
        "INSERT INTO hyperspace_model (id,warship_real_velocity_c,merchant_real_velocity_c,"
        "non_crash_translation_c,alpha_entry_max_velocity_c,canon) VALUES (1,0.6,0.5,0.2,0.3,1)"
    )
    con.execute(
        "INSERT INTO ship_classes (id,name,navy,hull_classification,max_g,max_hyper_band,"
        "real_cruise_velocity_c,code,canon) VALUES ('warbird','Warbird','TSN','BC',600,7,0.6,1,1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,hull_code,transponder,canon) "
        "VALUES ('war-1','HMS War','warbird',1,'1.1.1',1)"
    )
    con.execute(
        "INSERT INTO transit_model (id,formula,coeff_a,coeff_b,buffer_normal_s,buffer_emergency_s,"
        "canon) VALUES (1,'A',0.0,0.0,300,120,0)"
    )
    con.execute(
        "INSERT INTO wormhole_junctions (id,name,host_system_id,canon) VALUES ('bj','BJ','beta',1)"
    )
    con.execute(
        "INSERT INTO wormhole_links (id,junction_id,from_system_id,to_system_id,distance_ly,"
        "transit,canon) VALUES ('wl','bj','beta','gamma',31,'instant',1)"
    )
    con.commit()
    con.close()
    return str(db)


@pytest.fixture
def client(artifact_path: str, tmp_path) -> TestClient:
    db = tmp_path / "api.db"
    return TestClient(
        create_app(database_url=f"sqlite:///{db}", universe_db=artifact_path, dev_clock=False)
    )


def test_file_route_and_state(client: TestClient) -> None:
    r = client.post("/fleet/routes", json=ROUTE)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["transponder"] == "1.1.1"
    assert [s["kind"] for s in body["segments"]] == [
        "transit",
        "hyper_cruise",
        "wormhole_transit",
        "transit",
        "hyper_cruise",
        "transit",
    ]
    # State long after departure -> arrived in the destination system.
    st = client.get("/fleet/1.1.1/state").json()
    assert st["phase"] == "arrived"
    assert st["system"] == "gamma"
    assert st["transponder"] == "1.1.1"
    # A mid-trip sample reports the galactic-frame interstellar leg.
    mid = client.get("/fleet/1.1.1/state", params={"at": "1890-01-03T00:00:00+00:00"}).json()
    assert mid["phase"] in ("transit", "hyper_cruise", "wormhole_transit")


def test_fleet_board(client: TestClient) -> None:
    client.post("/fleet/routes", json=ROUTE)
    fleet = client.get("/fleet").json()
    assert len(fleet["ships"]) == 1
    assert fleet["ships"][0]["transponder"] == "1.1.1"
    assert fleet["ships"][0]["ship"] == "HMS War"


def test_unknown_transponder_404(client: TestClient) -> None:
    bad = {**ROUTE, "ship": "9.9.9"}
    assert client.post("/fleet/routes", json=bad).status_code == 404


def test_at_origin_guard(client: TestClient, artifact_path: str, tmp_path) -> None:
    client.post("/fleet/routes", json=ROUTE)  # arrives at gamma (depart 1890)
    # Re-file from alpha while the ship is at gamma -> rejected (not at origin).
    assert client.post("/fleet/routes", json=ROUTE).status_code == 409
    # Dev mode bypasses the guard.
    dev = TestClient(
        create_app(
            database_url=f"sqlite:///{tmp_path / 'dev.db'}",
            universe_db=artifact_path,
            dev_clock=True,
        )
    )
    dev.post("/fleet/routes", json=ROUTE)
    assert dev.post("/fleet/routes", json=ROUTE).status_code == 201


def test_abort_route(client: TestClient) -> None:
    client.post("/fleet/routes", json=ROUTE)
    assert client.delete("/fleet/1.1.1/route").status_code == 200
    assert client.get("/fleet/1.1.1/state").status_code == 404


def test_routes_need_artifact(tmp_path) -> None:
    # No universe_db -> galaxy routes unavailable (503), Phase-1 endpoints unaffected.
    bare = TestClient(create_app(database_url=f"sqlite:///{tmp_path / 'bare.db'}"))
    assert bare.post("/fleet/routes", json=ROUTE).status_code == 503
    assert bare.get("/health").status_code == 200
