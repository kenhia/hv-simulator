"""API + persistence: the canonical merchant run over HTTP."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from hvsim.api.app import create_app
from hvsim.clock import SimClock

DEPART = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def make_client(tmp_path):
    """Factory for a TestClient over a temp SQLite db with a frozen clock."""

    def _make(*, dev_clock: bool = False, db_name: str = "t.db", clock: SimClock | None = None):
        db = tmp_path / db_name
        c = clock or SimClock(rate=0.0, sim_epoch=DEPART)  # rate 0 → now() == DEPART
        return TestClient(create_app(f"sqlite:///{db}", clock=c, dev_clock=dev_clock))

    return _make


@pytest.fixture
def client(make_client):
    return make_client()


def _create_ship(client: TestClient) -> str:
    r = client.post(
        "/ships", json={"name": "SS Harrington", "max_accel_g": 250, "max_velocity_c": 0.6}
    )
    assert r.status_code == 201
    return r.json()["id"]


def _file_canonical(client: TestClient, ship_id: str) -> dict:
    r = client.post(
        f"/ships/{ship_id}/flightplan",
        json={
            "waypoints": [
                {"body": "titan-station", "layover_seconds": 21600},
                {"body": "earth"},
            ],
            "depart_at": "2026-01-01T00:00:00Z",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- basics ---------------------------------------------------------------------


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_fetch_ship(client: TestClient) -> None:
    ship_id = _create_ship(client)
    r = client.get(f"/ships/{ship_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "SS Harrington"
    assert body["status"] == "idle"
    assert body["state"]["phase"] == "idle"


# --- canonical flight plan ------------------------------------------------------


def test_canonical_plan_timeline(client: TestClient) -> None:
    ship_id = _create_ship(client)
    plan = _file_canonical(client, ship_id)
    assert [s["kind"] for s in plan["segments"]] == ["transit", "layover", "transit"]
    assert plan["segments"][1]["duration_seconds"] == pytest.approx(6 * 3600)
    assert plan["segments"][1]["body"] == "titan-station"
    # ~33 hours round trip.
    assert 32 * 3600 < plan["total_duration_seconds"] < 35 * 3600
    assert client.get(f"/ships/{ship_id}").json()["status"] == "active"


def test_state_across_phases(client: TestClient) -> None:
    ship_id = _create_ship(client)
    plan = _file_canonical(client, ship_id)

    def phase_at(iso: str) -> dict:
        return client.get(f"/ships/{ship_id}/state", params={"at": iso}).json()

    assert phase_at("2025-12-31T23:00:00Z")["phase"] == "predeparture"
    mid = phase_at("2026-01-01T06:45:00Z")
    assert mid["phase"] == "transit"
    assert mid["velocity"]["fraction_c"] > 0.1  # genuinely moving, in fraction of c
    assert phase_at("2026-01-01T16:00:00Z")["phase"] == "layover"
    after = phase_at(plan["arrival"])
    assert after["phase"] == "arrived"


def test_no_si_leakage_in_state(client: TestClient) -> None:
    ship_id = _create_ship(client)
    _file_canonical(client, ship_id)
    st = client.get(f"/ships/{ship_id}/state", params={"at": "2026-01-01T06:45:00Z"}).json()
    # Position carries km AND au; velocity carries km/s AND fraction of c.
    assert {"km", "au", "distance_from_sun_km", "distance_from_sun_au"} <= st["position"].keys()
    assert {"km_s", "speed_km_s", "fraction_c"} <= st["velocity"].keys()
    assert st["subjective_time_delta_s"] is None  # reserved, relativity deferred


def test_duplicate_plan_conflicts(client: TestClient) -> None:
    ship_id = _create_ship(client)
    _file_canonical(client, ship_id)
    r = client.post(
        f"/ships/{ship_id}/flightplan",
        json={"waypoints": [{"body": "mars"}]},
    )
    assert r.status_code == 409


def test_unknown_body_rejected(client: TestClient) -> None:
    ship_id = _create_ship(client)
    r = client.post(f"/ships/{ship_id}/flightplan", json={"waypoints": [{"body": "pluto"}]})
    assert r.status_code == 422


def test_abort_flightplan(client: TestClient) -> None:
    ship_id = _create_ship(client)
    _file_canonical(client, ship_id)
    assert client.delete(f"/ships/{ship_id}/flightplan").json()["status"] == "aborted"
    assert client.get(f"/ships/{ship_id}").json()["status"] == "idle"
    assert client.get(f"/ships/{ship_id}/flightplan").status_code == 404


# --- persistence ----------------------------------------------------------------


def test_persistence_survives_restart(make_client) -> None:
    first = make_client(db_name="shared.db")
    ship_id = _create_ship(first)
    _file_canonical(first, ship_id)

    # A fresh app against the same file = a "restart": no recompilation needed.
    second = make_client(db_name="shared.db")
    detail = second.get(f"/ships/{ship_id}").json()
    assert detail["status"] == "active"
    plan = second.get(f"/ships/{ship_id}/flightplan").json()
    assert [s["kind"] for s in plan["segments"]] == ["transit", "layover", "transit"]


# --- bodies ---------------------------------------------------------------------


def test_bodies_listing_and_station(client: TestClient) -> None:
    bodies = client.get("/bodies").json()
    names = {b["name"] for b in bodies}
    assert {"earth", "saturn", "titan", "titan-station"} <= names

    station = client.get("/bodies/titan-station/state").json()
    assert station["kind"] == "station"
    assert station["parent"] == "titan"
    assert 9.0 <= station["position"]["distance_from_sun_au"] <= 10.0


# --- clock ----------------------------------------------------------------------


def test_clock_get_always_works(client: TestClient) -> None:
    body = client.get("/clock").json()
    assert body["rate"] == 0.0
    assert body["dev_controls_enabled"] is False


def test_put_clock_gated_off_by_default(client: TestClient) -> None:
    assert client.put("/clock", json={"rate": 10.0}).status_code == 403


def test_root_serves_sol_map(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    body = r.text
    assert "<canvas" in body
    # The page must consume the live endpoints (that's M5's point).
    assert "/bodies" in body and "/ships" in body and "/clock" in body


def test_put_clock_jump_moves_state(make_client) -> None:
    client = make_client(dev_clock=True)
    ship_id = _create_ship(client)
    _file_canonical(client, ship_id)

    # No ?at= → uses the clock. Jump it to mid-transit and re-query.
    r = client.put("/clock", json={"jump_to": "2026-01-01T06:45:00Z"})
    assert r.status_code == 200
    assert client.get(f"/ships/{ship_id}/state").json()["phase"] == "transit"

    client.put("/clock", json={"jump_to": "2026-01-03T00:00:00Z"})
    assert client.get(f"/ships/{ship_id}/state").json()["phase"] == "arrived"
