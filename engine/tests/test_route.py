"""Multi-mode interstellar routes: leg->segment decomposition + the band model.

Self-contained: builds a tiny artifact from the contract DDL (systems, the
Weber hyper-band columns + model row, ship classes/ships with an override, a
wormhole link) so the route compiler can be exercised without the real data/
artifact. Checks the segment decomposition, the Weber band speed model
(apparent = multiplier x real velocity), the climb-to-hyper-limit, the wormhole
buffer, effective-stat (class + override) resolution, band gating, and coast.
"""

from __future__ import annotations

import pathlib
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from hvsim.flightplan import Ship
from hvsim.kinematics import SPEED_OF_LIGHT
from hvsim.route import Route, RouteLeg, compile_route, ship_from_artifact, simulation_for_route
from hvsim.universe import LMIN_M, LY_M, Universe, resolve_position

DDL = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "universe-artifact" / "schema.sql"
DEPART = datetime(1890, 1, 1, tzinfo=UTC)
# A ship that cruises Eta (multiplier 4294) at warship 0.6c.
WARSHIP = Ship("Test Warship", 600.0, 0.6, max_hyper_band=7, hyper_cruise_velocity_c=0.6)


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

    system("alpha", 0.0)
    system("beta", 40.0)
    system("gamma", 71.0)
    star("alpha:s", "alpha", 20.0)
    star("beta:s", "beta", 20.0)
    star("gamma:s", "gamma", 22.0)
    planet("alpha:p1", "alpha", "alpha:s", 1.0)
    planet("alpha:far", "alpha", "alpha:s", 150.0)  # long n-space leg (forces coast)
    planet("beta:p1", "beta", "beta:s", 1.0)
    planet("gamma:p1", "gamma", "gamma:s", 1.5)

    # Hyper bands (Weber chart): Delta, Eta, Theta usable; Iota unattainable.
    for order, name, mult, bleed, unatt in [
        (4, "Delta", 2178, 72, 0),
        (7, "Eta", 4294, 56, 0),
        (8, "Theta", 5000, 52, 0),
        (9, "Iota", 6000, 48, 1),
    ]:
        con.execute(
            "INSERT INTO hyperspace_bands (band_order,name,velocity_multiplier,multiplier_canon,"
            "translation_bleed_off_pct,bleed_off_canon,unattainable,canon) "
            "VALUES (?,?,?,1,?,1,?,1)",
            (order, name, mult, bleed, unatt),
        )
    con.execute(
        "INSERT INTO hyperspace_model (id,warship_real_velocity_c,merchant_real_velocity_c,"
        "non_crash_translation_c,alpha_entry_max_velocity_c,canon) VALUES (1,0.6,0.5,0.2,0.3,1)"
    )

    # A warship class (Eta, 0.6c) + a merchant class (Delta, 0.5c).
    con.execute(
        "INSERT INTO ship_classes (id,name,navy,hull_classification,max_g,max_hyper_band,"
        "real_cruise_velocity_c,singleton,canon) VALUES "
        "('warbird','Warbird','TSN','BC',600,7,0.6,0,1)"
    )
    con.execute(
        "INSERT INTO ship_classes (id,name,max_g,max_hyper_band,real_cruise_velocity_c,"
        "singleton,canon) VALUES ('hauler','Hauler',200,4,0.5,0,1)"
    )
    # war-1 inherits the class; war-2 has a Theta upgrade override; haul-1 is a merchant.
    con.execute("INSERT INTO ships (id,name,class_id,canon) VALUES ('war-1','War One','warbird',1)")
    con.execute(
        "INSERT INTO ships (id,name,class_id,ovr_max_hyper_band,canon) "
        "VALUES ('war-2','War Two','warbird',8,1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,canon) VALUES ('haul-1','Haul One','hauler',1)"
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


def _deliverable(ship: Ship) -> Route:
    # alpha ->(hyper)-> beta ->(wormhole)-> gamma:p1 — exercises every mode.
    return Route(
        ship=ship,
        origin_system="alpha",
        origin_body="alpha:p1",
        depart_at=DEPART,
        legs=[
            RouteLeg("hyper", "beta"),
            RouteLeg("wormhole", "gamma"),
            RouteLeg("hyper", "gamma", "gamma:p1"),
        ],
    )


# --- Decomposition --------------------------------------------------------------


def test_route_compiles_expected_segment_kinds(u: Universe) -> None:
    c = compile_route(_deliverable(WARSHIP), u)
    kinds = [s.kind for s in c.segments]
    assert kinds == [
        "transit",
        "hyper_cruise",
        "wormhole_transit",
        "transit",
        "hyper_cruise",
        "transit",
    ]
    for earlier, later in zip(c.segments, c.segments[1:], strict=False):
        assert earlier.t_end == later.t_start


# --- The Weber band model: apparent = multiplier x real velocity ----------------


def test_hyper_cruise_accel_coast_decel_at_band_speed(u: Universe) -> None:
    c = compile_route(_deliverable(WARSHIP), u)
    cruise = c.segments[1]  # alpha -> beta, 40 ly
    # An interstellar leg reaches the apparent v_cap and coasts.
    assert cruise.trajectory.profile.coasts
    peak = cruise.trajectory.profile.v_peak
    assert peak == pytest.approx(4294 * 0.6 * SPEED_OF_LIGHT, rel=1e-9)  # mult x real x c
    # Duration = the constant-cruise lower bound + a small accel/decel overhead.
    lower = 40.0 * LY_M / peak
    assert lower < cruise.duration_s < lower * 1.2
    assert cruise.to_pos.norm() == pytest.approx(40.0 * LY_M, rel=1e-9)


def test_hyper_cruise_reports_galactic_frame(u: Universe) -> None:
    c = compile_route(_deliverable(WARSHIP), u)
    sim = simulation_for_route(c, u)
    cruise = c.segments[1]
    st = sim.state(cruise.t_start + timedelta(seconds=cruise.duration_s / 2))
    assert st.phase == "hyper_cruise"
    assert st.system is None and st.frame == "galactic"
    assert st.position.norm() == pytest.approx(20.0 * LY_M, rel=1e-6)


def test_higher_band_ship_is_faster(u: Universe) -> None:
    # Same route, Theta ship vs Delta ship: the higher band arrives sooner.
    theta = Ship("Fast", 600.0, 0.6, max_hyper_band=8, hyper_cruise_velocity_c=0.6)
    delta = Ship("Slow", 200.0, 0.5, max_hyper_band=4, hyper_cruise_velocity_c=0.5)
    t_fast = compile_route(_deliverable(theta), u).arrival
    t_slow = compile_route(_deliverable(delta), u).arrival
    assert t_fast < t_slow


def test_unattainable_band_is_rejected(u: Universe) -> None:
    iota = Ship("TooFast", 600.0, 0.6, max_hyper_band=9, hyper_cruise_velocity_c=0.6)
    with pytest.raises(ValueError, match="unattainable"):
        compile_route(_deliverable(iota), u)


# --- Run out to the hyper limit -------------------------------------------------


def test_run_to_limit_uses_hyper_limit_from_artifact(u: Universe) -> None:
    c = compile_route(_deliverable(WARSHIP), u)
    run_out = c.segments[0]
    assert run_out.kind == "transit"
    start = resolve_position(u, "alpha", "alpha:p1", DEPART)
    expected = 20.0 * LMIN_M - start.norm()
    assert run_out.trajectory.profile.distance == pytest.approx(expected, rel=1e-6)
    assert not run_out.trajectory.profile.coasts


# --- Wormhole transit -----------------------------------------------------------


def test_wormhole_transit_is_buffer_only(u: Universe) -> None:
    c = compile_route(_deliverable(WARSHIP), u)
    wh = c.segments[2]
    assert wh.kind == "wormhole_transit"
    assert wh.from_system == "beta" and wh.to_system == "gamma"
    assert wh.duration_s == pytest.approx(300.0)


def test_state_after_arrival_in_destination_system(u: Universe) -> None:
    c = compile_route(_deliverable(WARSHIP), u)
    sim = simulation_for_route(c, u)
    st = sim.state(c.arrival + timedelta(hours=1))
    assert st.phase == "arrived" and st.system == "gamma"


# --- Effective ship stats (class + override) ------------------------------------


def test_effective_ship_resolves_override_over_class(u: Universe) -> None:
    assert u.effective_ship("war-1")["max_hyper_band"] == 7  # inherits class
    assert u.effective_ship("war-2")["max_hyper_band"] == 8  # override wins
    assert u.effective_ship("haul-1")["real_cruise_velocity_c"] == 0.5


def test_ship_from_artifact_carries_band_profile(u: Universe) -> None:
    ship = ship_from_artifact(u, "war-2")
    assert ship.max_hyper_band == 8 and ship.hyper_cruise_velocity_c == 0.6
    # The upgraded hull (Theta) beats the stock hull (Eta) on the same route.
    stock = ship_from_artifact(u, "war-1")
    assert (
        compile_route(_deliverable(ship), u).arrival < compile_route(_deliverable(stock), u).arrival
    )


# --- Coast finally fires --------------------------------------------------------


def test_coast_fires_on_long_nspace_leg(u: Universe) -> None:
    route = Route(WARSHIP, "alpha", "alpha:p1", [RouteLeg("nspace", "alpha", "alpha:far")], DEPART)
    c = compile_route(route, u)
    assert len(c.segments) == 1
    assert c.segments[0].trajectory.profile.coasts


# --- Determinism ----------------------------------------------------------------


def test_route_is_deterministic(u: Universe) -> None:
    a = compile_route(_deliverable(WARSHIP), u)
    b = compile_route(_deliverable(WARSHIP), u)
    assert [s.kind for s in a.segments] == [s.kind for s in b.segments]
    assert a.arrival == b.arrival
    sim_a, sim_b = simulation_for_route(a, u), simulation_for_route(b, u)
    for frac in (0.0, 0.5, 1.1):
        when = a.depart_at + (a.arrival - a.depart_at) * frac
        assert sim_a.state(when) == sim_b.state(when)
