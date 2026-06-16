"""Multi-mode interstellar routes: leg->segment decomposition + the new modes.

Self-contained: builds a tiny artifact from the contract DDL (three systems, a
hyper band, the wormhole buffer, a wormhole link) so the route compiler can be
exercised without the real data/ artifact. Checks the headline behaviours: the
segment decomposition, hyper_cruise timing from the band + distance, the
climb-to-hyper-limit, the wormhole buffer, and that the coast phase finally fires
on a long n-space leg.
"""

from __future__ import annotations

import pathlib
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from hvsim.clock import T_YEAR
from hvsim.flightplan import Ship
from hvsim.route import Route, RouteLeg, compile_route, simulation_for_route
from hvsim.universe import LMIN_M, LY_M, Universe, resolve_position

DDL = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "universe-artifact" / "schema.sql"
DEPART = datetime(1890, 1, 1, tzinfo=UTC)
SHIP = Ship(name="SS Test", max_accel_g=250.0, max_velocity_c=0.6)


@pytest.fixture
def artifact_path(tmp_path) -> str:
    db = tmp_path / "u.db"
    con = sqlite3.connect(db)
    con.executescript(DDL.read_text())
    con.execute("INSERT INTO schema_meta (version) VALUES ('test')")

    def system(sid: str, z_ly: float) -> None:
        con.execute(
            "INSERT INTO star_systems (id,name,canon,is_binary,coord_x_ly,coord_y_ly,coord_z_ly) "
            "VALUES (?,?,1,0,0,0,?)",
            (sid, sid, z_ly),
        )

    def star(sid: str, sysid: str, limit_lmin: float) -> None:
        con.execute(
            "INSERT INTO stars (id,system_id,name,role,mass_solar,hyper_limit_lmin,canon) "
            "VALUES (?,?,?,'primary',1.0,?,1)",
            (sid, sysid, sid, limit_lmin),
        )

    def planet(sid: str, sysid: str, star_id: str, a_au: float) -> None:
        con.execute(
            "INSERT INTO bodies (id,system_id,parent_star_id,name,type,orbit_index,canon,"
            "orbit_determined,a_au,e,i_deg,l_deg,long_peri_deg,long_node_deg,period_days) "
            "VALUES (?,?,?,?,'planet',3,1,1,?,0,0,0,0,0,?)",
            (sid, sysid, star_id, sid, a_au, 365.25 * a_au**1.5),
        )

    # alpha (origin) at the frame origin; beta 40 ly up; gamma 31 ly past beta.
    system("alpha", 0.0)
    system("beta", 40.0)
    system("gamma", 71.0)
    star("alpha:s", "alpha", 20.0)
    star("beta:s", "beta", 20.0)
    star("gamma:s", "gamma", 22.0)
    planet("alpha:p1", "alpha", "alpha:s", 1.0)
    planet("alpha:far", "alpha", "alpha:s", 150.0)  # a long n-space leg (forces coast)
    planet("beta:p1", "beta", "beta:s", 1.0)
    planet("gamma:p1", "gamma", "gamma:s", 1.5)

    # Alpha band + wormhole buffer + a beta<->gamma link.
    con.execute(
        "INSERT INTO hyperspace_bands (band_order,name,entry_velocity_limit_c,apparent_velocity_c,"
        "apparent_canon,canon) VALUES (1,'Alpha',0.3,200,0,1)"
    )
    con.execute(
        "INSERT INTO transit_model (id,formula,coeff_a,coeff_b,buffer_normal_s,buffer_emergency_s,"
        "canon) VALUES (1,'A*sqrt(M)+B*M^2',0.01684,6.9e-13,300,120,0)"
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
def u(artifact_path: str) -> Universe:
    return Universe.open(artifact_path)


def _deliverable(u: Universe) -> Route:
    # alpha ->(hyper)-> beta ->(wormhole)-> gamma:p1  — exercises every mode.
    return Route(
        ship=SHIP,
        origin_system="alpha",
        origin_body="alpha:p1",
        depart_at=DEPART,
        legs=[
            RouteLeg("hyper", "beta"),
            RouteLeg("wormhole", "gamma"),
            RouteLeg("hyper", "gamma", "gamma:p1"),  # in-gamma after the pop-through
        ],
    )


# --- Decomposition --------------------------------------------------------------


def test_route_compiles_expected_segment_kinds(u: Universe) -> None:
    c = compile_route(_deliverable(u), u)
    kinds = [s.kind for s in c.segments]
    # hyper = run-out + cruise (no approach here); wormhole; hyper = run-out + cruise + approach
    assert kinds == [
        "transit",
        "hyper_cruise",
        "wormhole_transit",
        "transit",
        "hyper_cruise",
        "transit",
    ]
    # Segments are contiguous in absolute time.
    for earlier, later in zip(c.segments, c.segments[1:], strict=False):
        assert earlier.t_end == later.t_start


# --- Hyper cruise ---------------------------------------------------------------


def test_hyper_cruise_time_from_band_and_distance(u: Universe) -> None:
    c = compile_route(_deliverable(u), u)
    cruise = c.segments[1]  # alpha -> beta, 40 ly at 200c
    expected_s = 40.0 / 200.0 * T_YEAR.total_seconds()
    assert cruise.duration_s == pytest.approx(expected_s, rel=1e-9)
    # Endpoints are galactic-frame (metres): beta is 40 ly up the z-axis.
    assert cruise.to_pos.norm() == pytest.approx(40.0 * LY_M, rel=1e-9)
    assert cruise.from_pos.norm() == pytest.approx(0.0, abs=1.0)


def test_hyper_cruise_reports_galactic_frame(u: Universe) -> None:
    c = compile_route(_deliverable(u), u)
    sim = simulation_for_route(c, u)
    cruise = c.segments[1]
    mid = cruise.t_start + timedelta(seconds=cruise.duration_s / 2)
    st = sim.state(mid)
    assert st.phase == "hyper_cruise"
    assert st.system is None
    assert st.frame == "galactic"
    # Halfway should be ~20 ly up the z-axis.
    assert st.position.norm() == pytest.approx(20.0 * LY_M, rel=1e-6)


# --- Run out to the hyper limit -------------------------------------------------


def test_run_to_limit_uses_hyper_limit_from_artifact(u: Universe) -> None:
    c = compile_route(_deliverable(u), u)
    run_out = c.segments[0]  # n-space run to the hyper limit (not a band "climb")
    assert run_out.kind == "transit"
    start = resolve_position(u, "alpha", "alpha:p1", DEPART)
    limit_m = 20.0 * LMIN_M
    expected = limit_m - start.norm()
    assert run_out.trajectory.profile.distance == pytest.approx(expected, rel=1e-6)
    # The short run (~1.5 AU) is a brachistochrone — no coast.
    assert not run_out.trajectory.profile.coasts


# --- Wormhole transit -----------------------------------------------------------


def test_wormhole_transit_is_buffer_only(u: Universe) -> None:
    c = compile_route(_deliverable(u), u)
    wh = c.segments[2]
    assert wh.kind == "wormhole_transit"
    assert wh.from_system == "beta" and wh.to_system == "gamma"
    assert wh.duration_s == pytest.approx(300.0)  # buffer_normal_s from the artifact


def test_state_after_arrival_in_destination_system(u: Universe) -> None:
    c = compile_route(_deliverable(u), u)
    sim = simulation_for_route(c, u)
    st = sim.state(c.arrival + timedelta(hours=1))
    assert st.phase == "arrived"
    assert st.system == "gamma"


# --- Coast finally fires --------------------------------------------------------


def test_coast_fires_on_long_nspace_leg(u: Universe) -> None:
    # A ~149 AU in-system hop exceeds the brachistochrone-vs-cap threshold (~88 AU
    # at 250 g / 0.6c), so the accel-coast-decel profile engages — a first.
    route = Route(
        ship=SHIP,
        origin_system="alpha",
        origin_body="alpha:p1",
        depart_at=DEPART,
        legs=[RouteLeg("nspace", "alpha", "alpha:far")],
    )
    c = compile_route(route, u)
    assert len(c.segments) == 1
    assert c.segments[0].trajectory.profile.coasts


# --- Determinism ----------------------------------------------------------------


def test_route_is_deterministic(u: Universe) -> None:
    a = compile_route(_deliverable(u), u)
    b = compile_route(_deliverable(u), u)
    assert [s.kind for s in a.segments] == [s.kind for s in b.segments]
    assert a.arrival == b.arrival
    sim_a, sim_b = simulation_for_route(a, u), simulation_for_route(b, u)
    for frac in (0.0, 0.25, 0.5, 0.75, 1.1):
        when = a.depart_at + (a.arrival - a.depart_at) * frac
        assert sim_a.state(when) == sim_b.state(when)
