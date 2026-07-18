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

from hvsim.des import OpenEndedSegment
from hvsim.des.model import segment_end
from hvsim.flightplan import Ship
from hvsim.kinematics import SPEED_OF_LIGHT
from hvsim.route import (
    NotAtOrigin,
    Route,
    RouteLeg,
    compile_route,
    fly_filed_route,
    from_filed,
    resolve_fleet,
    resolve_route,
    ship_from_artifact,
    simulation_for_route,
    to_filed,
)
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
        "real_cruise_velocity_c,mass_tons,singleton,canon) VALUES "
        "('warbird','Warbird','TSN','BC',600,7,0.6,2500000,0,1)"
    )
    con.execute(
        "INSERT INTO ship_classes (id,name,max_g,max_hyper_band,real_cruise_velocity_c,"
        "mass_tons,singleton,canon) VALUES ('hauler','Hauler',200,4,0.5,5000000,0,1)"
    )
    # war-1 inherits the class; war-2 has a Theta upgrade override; haul-1 is a merchant.
    con.execute(
        "INSERT INTO ships (id,name,class_id,transponder,canon) "
        "VALUES ('war-1','War One','warbird','1.1.1',1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,ovr_max_hyper_band,transponder,canon) "
        "VALUES ('war-2','War Two','warbird',8,'1.1.2',1)"
    )
    con.execute(
        "INSERT INTO ships (id,name,class_id,transponder,canon) "
        "VALUES ('haul-1','Haul One','hauler','1.2.1',1)"
    )

    con.execute(
        "INSERT INTO transit_model (id,formula,coeff_a,coeff_b,buffer_normal_s,buffer_emergency_s,"
        "canon) VALUES (1,'A*sqrt(M)+B*M^2',0.01684,6.9e-13,300,120,0)"
    )
    con.execute(
        "INSERT INTO wormhole_junctions (id,name,host_system_id,traffic_intensity,canon) "
        "VALUES ('bj','BJ','beta',3.0,1)"
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
    # The wormhole leg decomposes into an open-ended queue + the instant transit.
    c = resolve_route(compile_route(_deliverable(WARSHIP), u), u, "1.1.1")
    kinds = [s.kind for s in c.segments]
    assert kinds == [
        "transit",
        "hyper_cruise",
        "wormhole_queue",
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


def test_hyper_cruise_state_reports_band(u: Universe) -> None:
    # During a hyper leg the state carries the active band; velocity is the apparent
    # speed, so real = apparent / multiplier recovers the ship's real cruise (#72).
    c = compile_route(_deliverable(WARSHIP), u)
    sim = simulation_for_route(c, u)
    cruise = c.segments[1]
    st = sim.state(cruise.t_start + timedelta(seconds=cruise.duration_s / 2))
    assert st.phase == "hyper_cruise"
    assert st.band is not None
    assert st.band["band_order"] == 7  # Eta (WARSHIP max_hyper_band)
    mult = st.band["velocity_multiplier"]
    apparent = st.velocity.norm()  # coasting at apparent v_cap = mult x real x c
    assert apparent == pytest.approx(mult * 0.6 * SPEED_OF_LIGHT, rel=1e-9)
    assert apparent / mult == pytest.approx(0.6 * SPEED_OF_LIGHT, rel=1e-9)  # real
    # At rest in-system there is no band.
    assert sim.state(c.depart_at).band is None


def test_state_reports_real_acceleration(u: Universe) -> None:
    # Felt acceleration on the active trajectory (#72): >0 while accelerating, 0 while
    # coasting or at rest; hyper reports the *real* impeller accel (apparent / mult).
    c = compile_route(_deliverable(WARSHIP), u)
    sim = simulation_for_route(c, u)
    runout, cruise = c.segments[0], c.segments[1]  # n-space run-out, then hyper cruise
    assert sim.state(runout.t_start + timedelta(seconds=1)).acceleration_m_s2 > 0
    mid = sim.state(cruise.t_start + timedelta(seconds=cruise.duration_s / 2)).acceleration_m_s2
    assert mid == pytest.approx(0.0, abs=1e-6)  # coasting
    early = sim.state(cruise.t_start + timedelta(seconds=1)).acceleration_m_s2
    assert 0 < early < 1e5  # real impeller g (thousands), not mult x that (millions)
    assert sim.state(c.arrival + timedelta(seconds=10)).acceleration_m_s2 == 0.0  # arrived, at rest


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


def test_wormhole_leg_is_open_ended_until_resolved(u: Universe) -> None:
    # compile_route leaves the queue open; the resolver fixes its end.
    c = compile_route(_deliverable(WARSHIP), u)
    q = c.segments[2]
    assert q.kind == "wormhole_queue"
    assert q.from_system == "beta" and q.to_system == "gamma" and q.junction == "bj"
    assert q.t_end is None  # open-ended
    # The open-ended boundary is the resolver seam: unresolved, segment_end raises.
    with pytest.raises(OpenEndedSegment):
        segment_end(q, q.t_start)


def test_resolved_wormhole_queue_serialises_through_the_buffer(u: Universe) -> None:
    c = resolve_route(compile_route(_deliverable(WARSHIP), u), u, "1.1.1")
    q = c.segments[2]
    assert q.kind == "wormhole_queue" and q.t_end is not None
    # bj knob is 3 -> some phantom ahead; each clears at the 300 s buffer (tau << buffer
    # for these masses), so the wait is a whole number of buffers.
    wait = q.duration_s
    assert wait >= 0.0 and wait % 300.0 == pytest.approx(0.0, abs=1e-6)
    # The instant translation sits right at the transit-open.
    wh = c.segments[3]
    assert wh.kind == "wormhole_transit" and wh.duration_s == pytest.approx(0.0)
    assert wh.t_start == q.t_end


def _worm_route(ship: Ship, depart: datetime) -> Route:
    # A bare junction hop from the junction host system: arrival == depart_at, so
    # queue interleaving is exercised without hyper-leg timing in the way.
    return Route(ship, "beta", "beta:p1", [RouteLeg("wormhole", "gamma")], depart)


def test_wormhole_queue_position_counts_down(u: Universe) -> None:
    c = resolve_route(compile_route(_worm_route(WARSHIP, DEPART), u), u, "1.1.1")
    q = c.segments[0]
    sim = simulation_for_route(c, u)
    seen = [
        sim.state(q.t_start + timedelta(seconds=s)).queue_position
        for s in range(0, int(q.duration_s), 150)
    ]
    assert all(p is not None for p in seen)
    assert seen == sorted(seen, reverse=True)  # monotonically non-increasing
    assert seen[0] >= 1
    # Once the slot opens, the ship has popped through into the destination system.
    after = sim.state(q.t_end + timedelta(seconds=1))
    assert after.phase != "queued"


def test_two_real_ships_interleave_at_a_junction(u: Universe) -> None:
    cA = compile_route(_worm_route(WARSHIP, DEPART), u)
    cB = compile_route(_worm_route(WARSHIP, DEPART), u)
    rA, rB = resolve_fleet([(cA, "1.1.1"), (cB, "1.1.2")], u)
    qA, qB = rA.segments[0], rB.segments[0]
    assert qA.kind == "wormhole_queue" and qB.kind == "wormhole_queue"
    assert qA.t_start == qB.t_start == DEPART  # both arrive together
    # A (lower stable key) goes first; B serialises strictly behind it.
    assert qB.t_end > qA.t_end
    sa = simulation_for_route(rA, u).state(DEPART).queue_position
    sb = simulation_for_route(rB, u).state(DEPART).queue_position
    assert sb > sa  # B is deeper in the queue (behind A)


def test_queue_resolution_is_deterministic(u: Universe) -> None:
    def ends() -> list[datetime]:
        items = [
            (compile_route(_worm_route(WARSHIP, DEPART), u), "1.1.1"),
            (compile_route(_worm_route(WARSHIP, DEPART), u), "1.1.2"),
        ]
        return [r.segments[0].t_end for r in resolve_fleet(items, u)]

    assert ends() == ends()  # same routes + seed -> identical queues


def test_state_after_arrival_in_destination_system(u: Universe) -> None:
    c = resolve_route(compile_route(_deliverable(WARSHIP), u), u, "1.1.1")
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


# --- navigable_location (phase-based) -------------------------------------------


def test_navigable_location_by_phase(u: Universe) -> None:
    c = compile_route(_deliverable(WARSHIP), u)
    sim = simulation_for_route(c, u)
    # Pre-departure: at the origin body.
    assert sim.navigable_location(DEPART - timedelta(hours=1)) == ("alpha", "alpha:p1")
    # Mid-trip (any moving phase): not navigable.
    assert sim.navigable_location(DEPART + (c.arrival - DEPART) * 0.5) is None
    # Arrived: at the destination body.
    assert sim.navigable_location(c.arrival + timedelta(hours=1)) == ("gamma", "gamma:p1")


def test_navigable_location_layover(u: Universe) -> None:
    # An in-system hop with a layover: navigable (at rest at the body) during it.
    route = Route(
        WARSHIP,
        "alpha",
        "alpha:p1",
        [RouteLeg("nspace", "alpha", "alpha:far", layover=timedelta(days=2))],
        DEPART,
    )
    c = compile_route(route, u)
    sim = simulation_for_route(c, u)
    layover = next(s for s in c.segments if s.kind == "layover")
    mid = layover.t_start + timedelta(hours=1)
    assert sim.navigable_location(mid) == ("alpha", "alpha:far")


# --- Filed-route round-trip + the at-origin guard -------------------------------


def _filed(u: Universe, transponder: str = "1.1.1") -> dict:
    legs = list(_deliverable(WARSHIP).legs)
    route = Route(ship_from_artifact(u, "war-1"), "alpha", "alpha:p1", legs, DEPART)
    return to_filed(route, transponder)


def test_filed_route_round_trips(u: Universe) -> None:
    doc = _filed(u)
    route = from_filed(doc, u)
    assert (route.origin_system, route.origin_body) == ("alpha", "alpha:p1")
    assert [(leg.mode, leg.to_system) for leg in route.legs] == [
        ("hyper", "beta"),
        ("wormhole", "gamma"),
        ("hyper", "gamma"),
    ]
    # The reloaded route compiles and flies.
    assert compile_route(route, u).segments


def test_fly_filed_route_guard(u: Universe) -> None:
    doc = _filed(u)
    current = simulation_for_route(compile_route(_deliverable(WARSHIP), u), u)
    # Ship at the origin (pre-departure) -> accepted.
    compiled = fly_filed_route(doc, u, current=current, now=DEPART - timedelta(hours=1))
    assert compiled.segments
    # Ship under way -> rejected (navigable_location is None).
    mid = DEPART + (current_arrival(u) - DEPART) * 0.5
    with pytest.raises(NotAtOrigin):
        fly_filed_route(doc, u, current=current, now=mid)
    # Dev mode bypasses the guard.
    assert fly_filed_route(doc, u, current=current, now=mid, dev=True).segments


def current_arrival(u: Universe) -> datetime:
    return compile_route(_deliverable(WARSHIP), u).arrival
