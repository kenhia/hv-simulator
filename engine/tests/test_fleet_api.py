"""Galaxy fleet API: file a planner route (by transponder), fly it, board it."""

from __future__ import annotations

import pathlib
import sqlite3
import urllib.parse

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
        "real_cruise_velocity_c,mass_tons,code,canon) "
        "VALUES ('warbird','Warbird','TSN','BC',600,7,0.6,2500000,1,1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,hull_code,transponder,canon) "
        "VALUES ('war-1','HMS War','warbird',1,'1.1.1',1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,hull_code,transponder,canon) "
        "VALUES ('war-2','HMS Two','warbird',2,'1.1.2',1)"
    )
    con.execute(
        "INSERT INTO transit_model (id,formula,coeff_a,coeff_b,buffer_normal_s,buffer_emergency_s,"
        "canon) VALUES (1,'A',0.0,0.0,300,120,0)"
    )
    con.execute(
        "INSERT INTO wormhole_junctions (id,name,host_system_id,traffic_intensity,canon) "
        "VALUES ('bj','BJ','beta',3.0,1)"
    )
    con.execute(
        "INSERT INTO wormhole_links (id,junction_id,from_system_id,to_system_id,distance_ly,"
        "transit,canon) VALUES ('wl','bj','beta','gamma',31,'instant',1)"
    )
    con.execute(
        "INSERT INTO places (id,system_id,name,type,rides_on_body_id,canon) "
        "VALUES ('beta:station','beta','Beta Station','naval_station','beta:p1',1)"
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
        "wormhole_queue",
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


# --- Sprint 020: deployed queue board + junction queue endpoint ---------------

WORM_AT = "1890-01-01T00:00:00+00:00"


def _file_wormhole(client: TestClient, transponder: str) -> None:
    """File a bare beta -> gamma junction hop (arrival == depart, so queues interleave)."""
    r = client.post(
        "/fleet/routes",
        json={
            "schema": "hvsim.filed-route/v1",
            "ship": transponder,
            "origin": {"system": "beta", "body": "beta:p1"},
            "depart_at": WORM_AT,
            "legs": [{"mode": "wormhole", "to_system": "gamma"}],
        },
    )
    assert r.status_code == 201, r.text


def _q(when: str) -> str:
    return urllib.parse.quote(when)


def test_fleet_board_interleaves_queue(client: TestClient) -> None:
    _file_wormhole(client, "1.1.1")
    _file_wormhole(client, "1.1.2")
    ships = {s["transponder"]: s for s in client.get(f"/fleet?at={_q(WORM_AT)}").json()["ships"]}
    a, b = ships["1.1.1"], ships["1.1.2"]
    assert a["phase"] == b["phase"] == "queued"
    # Real-ship interleaving: B (higher transponder) sits strictly behind A.
    assert a["queue_position"] is not None and b["queue_position"] > a["queue_position"]


def test_junction_queue_endpoint(client: TestClient) -> None:
    _file_wormhole(client, "1.1.1")
    _file_wormhole(client, "1.1.2")
    q = client.get(f"/junctions/bj/queue?at={_q(WORM_AT)}").json()
    assert q["junction_id"] == "bj" and q["traffic_intensity"] == 3.0
    entries = q["entries"]
    # Positions are 1..N, front-first, with non-decreasing transit ETAs.
    assert [e["position"] for e in entries] == list(range(1, len(entries) + 1))
    etas = [e["transit_eta"] for e in entries]
    assert etas == sorted(etas)
    # Both real ships appear (by transponder), plus phantom (null) traffic ahead.
    tps = [e["transponder"] for e in entries]
    assert "1.1.1" in tps and "1.1.2" in tps
    assert None in tps  # phantom traffic


def test_junction_queue_unknown_404(client: TestClient) -> None:
    assert client.get("/junctions/nope/queue").status_code == 404


def test_junction_queue_metrics(artifact_path: str, tmp_path) -> None:
    dev = TestClient(
        create_app(
            database_url=f"sqlite:///{tmp_path / 'm.db'}",
            universe_db=artifact_path,
            dev_clock=True,
        )
    )
    _file_wormhole(dev, "1.1.1")
    _file_wormhole(dev, "1.1.2")
    dev.put("/clock", json={"jump_to": WORM_AT})  # freeze "now" inside the queue window
    metrics = dev.get("/metrics").text
    prefix = 'hvsim_junction_queue_depth{junction="bj"}'
    line = next(ln for ln in metrics.splitlines() if ln.startswith(prefix))
    assert float(line.rsplit(" ", 1)[1]) == 2.0  # both real ships queued now


# --- Sprint 022: system detail + places (the system-zoom data) ----------------


def test_system_detail(client: TestClient) -> None:
    d = client.get("/systems/beta").json()
    assert d["id"] == "beta" and d["is_binary"] is False
    assert [s["hyper_limit_lmin"] for s in d["stars"]] == [20.0]
    assert d["primary_hyper_limit_lmin"] == 20.0
    assert d["primary_hyper_limit_au"] > 0  # the ring radius the system view draws
    assert client.get("/systems/nope").status_code == 404


def test_system_places(client: TestClient) -> None:
    pl = client.get("/systems/beta/places").json()
    assert [p["id"] for p in pl] == ["beta:station"]
    p = pl[0]
    assert p["rides_on_body_id"] == "beta:p1"
    assert p["position"] is not None  # rides on a body -> co-located with it
    assert client.get("/systems/nope/places").status_code == 404


# --- Sprint 023: route segments for the Ship Timeline -------------------------


def test_fleet_route_segments(client: TestClient) -> None:
    client.post("/fleet/routes", json=ROUTE)
    r = client.get("/fleet/1.1.1/route")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["transponder"] == "1.1.1"
    kinds = [s["kind"] for s in body["segments"]]
    assert "hyper_cruise" in kinds and "wormhole_queue" in kinds
    assert client.get("/fleet/9.9.9/route").status_code == 404


# --- Sprint 026: POST /plan (preview a route, not filed) ----------------------


def test_plan_single_destination(client: TestClient) -> None:
    r = client.post(
        "/plan",
        json={
            "ship": "1.1.1",
            "origin": {"system": "alpha", "body": "alpha:p1"},
            "waypoints": [{"system": "gamma", "body": "gamma:p1"}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["route"]["transponder"] == "1.1.1"
    assert body["route"]["status"] == "planned"
    assert len(body["route"]["segments"]) > 0
    # The returned filed doc commits cleanly to /fleet/routes.
    assert client.post("/fleet/routes", json=body["filed"]).status_code == 201


def test_plan_multi_waypoint_with_layover(client: TestClient) -> None:
    r = client.post(
        "/plan",
        json={
            "ship": "1.1.1",
            "origin": {"system": "alpha", "body": "alpha:p1"},
            "waypoints": [
                {"system": "beta", "body": "beta:p1", "layover_s": 7200},
                {"system": "gamma", "body": "gamma:p1"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    legs = r.json()["filed"]["legs"]
    # Visits beta then gamma; the beta-reaching leg carries the 2 h layover.
    assert any(lg["layover_s"] == 7200 for lg in legs)
    assert legs[-1]["to_body"] == "gamma:p1"


def test_plan_errors(client: TestClient) -> None:
    base = {"origin": {"system": "alpha", "body": "alpha:p1"}}
    assert (
        client.post(
            "/plan", json={**base, "ship": "9.9.9", "waypoints": [{"system": "gamma", "body": "g"}]}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/plan",
            json={**base, "ship": "1.1.1", "waypoints": [{"system": "nowhere", "body": "x"}]},
        ).status_code
        == 422
    )


# --- Sprint 027: ship catalog (the Flight Planner's picker) -------------------


def test_ship_catalog(client: TestClient) -> None:
    by = {s["transponder"]: s for s in client.get("/fleet/ships").json()}
    assert "1.1.1" in by and "1.1.2" in by
    assert by["1.1.1"]["military"] is True  # warbird carries a navy
    assert by["1.1.1"]["under_way"] is False and by["1.1.1"]["location_body"] is None  # idle
    # File a 1890 route; long after departure the ship has ARRIVED -> at rest at the
    # final body, NOT under way (the bug: a stale "active" row read as under way).
    client.post("/fleet/routes", json=ROUTE)
    after = {s["transponder"]: s for s in client.get("/fleet/ships").json()}
    assert after["1.1.1"]["under_way"] is False
    assert after["1.1.1"]["location_body"] == "gamma:p1"  # current navigable point


def test_ship_catalog_under_way(artifact_path: str, tmp_path) -> None:
    dev = TestClient(
        create_app(
            database_url=f"sqlite:///{tmp_path / 'm.db'}", universe_db=artifact_path, dev_clock=True
        )
    )
    dev.post("/fleet/routes", json=ROUTE)
    dev.put("/clock", json={"jump_to": "1890-01-03T00:00:00Z"})  # mid-flight
    by = {s["transponder"]: s for s in dev.get("/fleet/ships").json()}
    assert by["1.1.1"]["under_way"] is True
    assert by["1.1.1"]["location_body"] is None
