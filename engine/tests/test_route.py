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

from hvsim.des import OpenEndedSegment, Segment
from hvsim.des.model import segment_end
from hvsim.flightplan import Ship
from hvsim.kinematics import SPEED_OF_LIGHT
from hvsim.route import (
    CompiledRoute,
    NotAtOrigin,
    Route,
    RouteLeg,
    compile_route,
    fly_filed_route,
    from_filed,
    plan_route,
    resolve_fleet,
    resolve_fleet_junctions,
    resolve_route,
    route_graph,
    ship_from_artifact,
    simulation_for_route,
    speed_class,
    to_filed,
)
from hvsim.route.graph import HYPER_LEG_OVERHEAD_S, hops, routing_table
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
        "INSERT INTO wormhole_junctions (id,name,host_system_id,traffic_intensity,"
        "nexus_dist_lmin,nexus_bearing_deg,canon) VALUES ('bj','BJ','beta',3.0,420,30,1)"
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
    # The host-originating wormhole leg (beta hosts bj) decomposes into a run-out to
    # the nexus (transit), the open-ended queue, and the instant transit (Sprint 037).
    c = resolve_route(compile_route(_deliverable(WARSHIP), u), u, "1.1.1")
    kinds = [s.kind for s in c.segments]
    assert kinds == [
        "transit",
        "hyper_cruise",
        "transit",  # run out to the beta nexus before queuing
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
    q = next(s for s in c.segments if s.kind == "wormhole_queue")
    assert q.from_system == "beta" and q.to_system == "gamma" and q.junction == "bj"
    assert q.t_end is None  # open-ended
    # The open-ended boundary is the resolver seam: unresolved, segment_end raises.
    with pytest.raises(OpenEndedSegment):
        segment_end(q, q.t_start)


def test_resolved_wormhole_queue_serialises_through_the_buffer(u: Universe) -> None:
    c = resolve_route(compile_route(_deliverable(WARSHIP), u), u, "1.1.1")
    qi = next(i for i, s in enumerate(c.segments) if s.kind == "wormhole_queue")
    q = c.segments[qi]
    assert q.t_end is not None
    # bj knob is 3 -> some phantom ahead; each clears at the 300 s buffer (tau << buffer
    # for these masses), so the wait is a whole number of buffers.
    wait = q.duration_s
    assert wait >= 0.0 and wait % 300.0 == pytest.approx(0.0, abs=1e-6)
    # The instant translation sits right at the transit-open.
    wh = c.segments[qi + 1]
    assert wh.kind == "wormhole_transit" and wh.duration_s == pytest.approx(0.0)
    assert wh.t_start == q.t_end


# --- Run out to the junction nexus before queuing (Sprint 037, #76) --------------


def test_host_wormhole_runs_out_to_nexus_before_queuing(u: Universe) -> None:
    # A host-originating wormhole leg (beta hosts bj) flies to the nexus first, then
    # queues there — no instant teleport into the queue.
    c = compile_route(_worm_route(WARSHIP, DEPART), u)
    assert [s.kind for s in c.segments] == ["transit", "wormhole_queue", "wormhole_transit"]
    run, q = c.segments[0], c.segments[1]
    assert run.t_end == q.t_start and q.t_start > DEPART  # queue begins after the run-out
    nexus = u.junction_nexus_position("bj")
    start = resolve_position(u, "beta", "beta:p1", DEPART)
    assert run.trajectory.profile.distance == pytest.approx((nexus - start).norm(), rel=1e-6)
    # The queue segment carries the nexus hold point so a queued ship rests there.
    assert q.nexus_pos is not None and (q.nexus_pos - nexus).norm() < 1.0


def test_run_out_to_nexus_is_a_realistic_clock(u: Universe) -> None:
    # 420 lmin (7 light-hours) is a real in-system leg — order of a day, not instant.
    run = compile_route(_worm_route(WARSHIP, DEPART), u).segments[0]
    assert 0.5 * 86_400 < run.duration_s < 2.0 * 86_400


def test_queued_ship_holds_at_the_nexus(u: Universe) -> None:
    # While queued, the ship reports the nexus point in its origin system frame
    # (superseding the old star-centre report), so map + ship agree.
    c = resolve_route(compile_route(_worm_route(WARSHIP, DEPART), u), u, "1.1.1")
    q = _queue_seg(c)
    st = simulation_for_route(c, u).state(q.t_start + timedelta(seconds=1))
    assert st.phase == "queued" and st.system == "beta" and st.frame == "heliocentric"
    nexus = u.junction_nexus_position("bj")
    assert (st.position - nexus).norm() < 1.0


def test_straight_through_transit_skips_the_run_out(u: Universe) -> None:
    # gamma:p1 ->(wormhole)-> beta ->(wormhole)-> gamma. Leg 1 originates at a terminus
    # system (no host nexus in-frame -> no run-out) and emerges at the beta nexus;
    # leg 2 is already at the nexus -> its run-out is skipped. So no transit anywhere.
    route = Route(
        WARSHIP,
        "gamma",
        "gamma:p1",
        [RouteLeg("wormhole", "beta"), RouteLeg("wormhole", "gamma")],
        DEPART,
    )
    kinds = [s.kind for s in compile_route(route, u).segments]
    assert kinds == ["wormhole_queue", "wormhole_transit", "wormhole_queue", "wormhole_transit"]


def _worm_route(ship: Ship, depart: datetime) -> Route:
    # A junction hop from the junction host system (beta hosts bj): the ship runs
    # out to the nexus first (Sprint 037), then queues. Queue interleaving is
    # exercised without hyper-leg timing in the way.
    return Route(ship, "beta", "beta:p1", [RouteLeg("wormhole", "gamma")], depart)


def _queue_seg(c: CompiledRoute) -> Segment:
    return next(s for s in c.segments if s.kind == "wormhole_queue")


def test_wormhole_queue_position_counts_down(u: Universe) -> None:
    c = resolve_route(compile_route(_worm_route(WARSHIP, DEPART), u), u, "1.1.1")
    q = _queue_seg(c)
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
    qA, qB = _queue_seg(rA), _queue_seg(rB)
    # Identical run-outs -> both reach the nexus (and so the queue) together.
    assert qA.t_start == qB.t_start and qA.t_start > DEPART
    # A (lower stable key) goes first; B serialises strictly behind it.
    assert qB.t_end > qA.t_end
    # Both are queued once they reach the nexus (identical run-outs -> same instant).
    sa = simulation_for_route(rA, u).state(qA.t_start).queue_position
    sb = simulation_for_route(rB, u).state(qB.t_start).queue_position
    assert sb > sa  # B is deeper in the queue (behind A)


def test_a_later_filing_cannot_move_an_earlier_ship_slot(u: Universe) -> None:
    # #67: A files first but reaches the junction a few minutes *after* B, which
    # filed later. Arrival-ordered folding let B book first and push A's ETA out;
    # filing-ordered booking must leave A untouched and make B give way instead.
    early, late = DEPART, DEPART + timedelta(hours=1)
    a = compile_route(_worm_route(WARSHIP, DEPART + timedelta(minutes=5)), u)
    b = compile_route(_worm_route(WARSHIP, DEPART), u)
    filed = {"1.1.1": early, "1.1.2": late}

    a_alone = resolve_fleet([(a, "1.1.1")], u, filed_at=filed)[0]
    b_alone = resolve_fleet([(b, "1.1.2")], u, filed_at=filed)[0]
    a_fleet, b_fleet = resolve_fleet([(a, "1.1.1"), (b, "1.1.2")], u, filed_at=filed)

    assert _queue_seg(b_fleet).t_start < _queue_seg(a_fleet).t_start  # B gets there first
    assert _queue_seg(a_fleet).t_end == _queue_seg(a_alone).t_end  # ...but A keeps its slot
    assert a_fleet.arrival == a_alone.arrival  # ...so the ETA A was quoted still holds
    assert _queue_seg(b_fleet).t_end > _queue_seg(b_alone).t_end  # the later filer gives way


def test_queue_positions_agree_with_the_junction_board(u: Universe) -> None:
    # Positions are repaired from the finished calendar, so a ship's reported #N
    # matches what the board shows present ahead of it at that instant.
    items = [
        (compile_route(_worm_route(WARSHIP, DEPART), u), "1.1.1"),
        (compile_route(_worm_route(WARSHIP, DEPART + timedelta(hours=2)), u), "1.1.2"),
    ]
    routes, servers = resolve_fleet_junctions(items, u)
    server = servers["bj"]
    for compiled, tp in zip(routes, ("1.1.1", "1.1.2"), strict=True):
        q = _queue_seg(compiled)
        when = q.t_start + timedelta(seconds=1)
        board = server.snapshot(when)
        reported = simulation_for_route(compiled, u).state(when).queue_position
        assert reported == [t.transponder for t in board].index(tp) + 1


def test_queue_resolution_is_deterministic(u: Universe) -> None:
    def ends() -> list[datetime]:
        items = [
            (compile_route(_worm_route(WARSHIP, DEPART), u), "1.1.1"),
            (compile_route(_worm_route(WARSHIP, DEPART), u), "1.1.2"),
        ]
        return [_queue_seg(r).t_end for r in resolve_fleet(items, u)]

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


# --- Route-finding over the precomputed graph (Sprint 039, #64) -----------------


def test_route_graph_is_built_once_per_artifact(u: Universe) -> None:
    assert route_graph(u) is route_graph(u)
    g = route_graph(u)
    assert g.systems == ("alpha", "beta", "gamma")
    assert g.wormhole_adj == {"beta": ("gamma",), "gamma": ("beta",)}
    assert g.distance_ly("alpha", "beta") == pytest.approx(40.0)
    assert g.distance_ly("beta", "alpha") == g.distance_ly("alpha", "beta")


def test_routing_table_is_cached_per_speed_class(u: Universe) -> None:
    g, k = route_graph(u), speed_class(u, WARSHIP)
    first = routing_table(g, k, "alpha")
    assert routing_table(g, k, "alpha") is first  # same speed class -> the same table
    slower = speed_class(
        u, Ship("Hauler", 200.0, 0.5, max_hyper_band=4, hyper_cruise_velocity_c=0.5)
    )
    assert slower > k  # a Delta merchant costs more seconds per light-year
    assert routing_table(g, slower, "alpha") is not first


def test_finder_prefers_the_junction_hop(u: Universe) -> None:
    # alpha -> gamma is 71 ly direct, or 40 ly of hyper to beta then a ~free
    # wormhole. The junction wins, and the arriving leg is an in-system hop.
    route = plan_route(u, "war-1", "alpha", "alpha:p1", "gamma", "gamma:p1", DEPART)
    assert [(lg.mode, lg.to_system) for lg in route.legs] == [
        ("hyper", "beta"),
        ("wormhole", "gamma"),
        ("nspace", "gamma"),
    ]
    assert route.legs[-1].to_body == "gamma:p1"


def test_found_path_is_time_optimal(u: Universe) -> None:
    # Brute-force every simple path over the 3 placed systems and check the finder
    # returns one of minimum weight (the graph swap must not change the topology).
    g, k = route_graph(u), speed_class(u, WARSHIP)

    def weight(path: list[tuple[str, str]], origin: str) -> float:
        total, node = 0.0, origin
        for mode, nxt in path:
            total += (
                g.distance_ly(node, nxt) * k + HYPER_LEG_OVERHEAD_S
                if mode == "hyper"
                else g.buffer_s
            )
            node = nxt
        return total

    def simple_paths(origin: str, dest: str, seen: tuple[str, ...] = ()):
        for nxt in g.systems:
            if nxt == origin or nxt in seen:
                continue
            modes = ["hyper"] + (["wormhole"] if nxt in g.wormhole_adj.get(origin, ()) else [])
            for mode in modes:
                if nxt == dest:
                    yield [(mode, nxt)]
                else:
                    for rest in simple_paths(nxt, dest, (*seen, origin)):
                        yield [(mode, nxt), *rest]

    for origin in g.systems:
        for dest in g.systems:
            if origin == dest:
                continue
            found = hops(g, k, origin, dest)
            best = min(weight(p, origin) for p in simple_paths(origin, dest))
            assert weight(found, origin) == pytest.approx(best)
