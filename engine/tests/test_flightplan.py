"""Flight-plan compiler + state queries: the canonical merchant run."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest

from hvsim.clock import SimClock
from hvsim.ephemeris import AU_M, heliocentric_position
from hvsim.flightplan import FlightPlan, Ship, Waypoint, compile_plan, state_at

DEPART = datetime(2026, 1, 1, tzinfo=UTC)
MERCHANT = Ship(name="SS Test Merchant", max_accel_g=250.0, max_velocity_c=0.6)


def _dist(a, b) -> float:
    return math.dist(a, b)


def _canonical_plan() -> FlightPlan:
    # Earth → Titan Station (6h layover) → Earth — the project's original use case.
    return FlightPlan(
        ship=MERCHANT,
        origin="earth",
        waypoints=[
            Waypoint("titan-station", timedelta(hours=6)),
            Waypoint("earth"),
        ],
        depart_at=DEPART,
    )


# --- Titan Station ephemeris ----------------------------------------------------


def test_titan_station_resolves_near_saturn() -> None:
    station = heliocentric_position("titan-station", DEPART)
    saturn = heliocentric_position("saturn", DEPART)
    r_au = _dist(station, (0.0, 0.0, 0.0)) / AU_M
    assert 9.0 <= r_au <= 10.0
    assert _dist(station, saturn) < 1.3e6 * 1e3  # within Titan's orbit (~1.22e6 km)


# --- Compilation ----------------------------------------------------------------


def test_canonical_plan_segment_structure() -> None:
    c = compile_plan(_canonical_plan())
    kinds = [s.kind for s in c.segments]
    assert kinds == ["transit", "layover", "transit"]

    # Layover is exactly 6 hours.
    assert c.segments[1].duration_s == pytest.approx(6 * 3600.0)
    # Each transit is roughly half a day.
    assert 10 * 3600 < c.segments[0].duration_s < 16 * 3600
    assert 10 * 3600 < c.segments[2].duration_s < 16 * 3600


def test_segments_are_contiguous_absolute_time() -> None:
    c = compile_plan(_canonical_plan())
    assert c.segments[0].t_start == DEPART
    for earlier, later in zip(c.segments, c.segments[1:], strict=False):
        assert earlier.t_end == later.t_start
    assert c.arrival == c.segments[-1].t_end


# --- State across phases --------------------------------------------------------


def test_state_predeparture_docked_at_origin() -> None:
    c = compile_plan(_canonical_plan())
    st = state_at(c, DEPART - timedelta(hours=1))
    assert st.phase == "predeparture"
    assert st.velocity == (0.0, 0.0, 0.0)
    assert _dist(st.position, heliocentric_position("earth", st.when)) < 1.0


def test_state_midtransit_is_moving() -> None:
    c = compile_plan(_canonical_plan())
    mid = c.segments[0].t_start + timedelta(seconds=c.segments[0].duration_s / 2)
    st = state_at(c, mid)
    assert st.phase == "transit"
    assert st.segment_seq == 0
    assert st.velocity.norm() > 0.0  # genuinely under way


def test_state_during_layover_tracks_station() -> None:
    c = compile_plan(_canonical_plan())
    layover = c.segments[1]
    mid = layover.t_start + timedelta(hours=3)
    st = state_at(c, mid)
    assert st.phase == "layover"
    assert st.velocity == (0.0, 0.0, 0.0)
    assert _dist(st.position, heliocentric_position("titan-station", mid)) < 1.0


def test_state_after_arrival_docked_at_earth() -> None:
    c = compile_plan(_canonical_plan())
    st = state_at(c, c.arrival + timedelta(hours=1))
    assert st.phase == "arrived"
    assert _dist(st.position, heliocentric_position("earth", st.when)) < 1.0


def test_position_continuous_across_boundaries() -> None:
    c = compile_plan(_canonical_plan())
    eps = timedelta(milliseconds=1)
    for boundary in (s.t_end for s in c.segments[:-1]):
        before = state_at(c, boundary - eps).position
        after = state_at(c, boundary + eps).position
        # ~0.18c over 2 ms is ~360 km; intercept matches the target to <1 km.
        assert _dist(before, after) < 1_000e3


# --- SimClock: depart-now and fast-forward --------------------------------------


def test_depart_now_via_clock() -> None:
    clock = SimClock()
    plan = FlightPlan(MERCHANT, "earth", [Waypoint("mars")], clock.now())
    c = compile_plan(plan)
    st = state_at(c, clock.now())  # essentially the departure instant
    assert st.phase == "transit"
    assert _dist(st.position, heliocentric_position("earth", st.when)) < 1e6  # just left Earth


def test_clock_jump_fast_forwards_state() -> None:
    clock = SimClock()
    depart = clock.now()
    c = compile_plan(FlightPlan(MERCHANT, "earth", [Waypoint("titan-station")], depart))

    clock.jump_to(depart + timedelta(seconds=c.segments[0].duration_s / 2))
    assert state_at(c, clock.now()).phase == "transit"

    clock.jump_to(c.arrival + timedelta(hours=1))
    assert state_at(c, clock.now()).phase == "arrived"


def test_clock_rate_change_keeps_time_continuous() -> None:
    clock = SimClock()
    before = clock.now()
    clock.set_rate(3600.0)  # 1 real second = 1 sim hour
    after = clock.now()
    assert abs((after - before).total_seconds()) < 1.0  # no jump at the rate change
    assert clock.rate == 3600.0


# --- Determinism ----------------------------------------------------------------


def test_compilation_deterministic() -> None:
    assert compile_plan(_canonical_plan()).segments == compile_plan(_canonical_plan()).segments


def test_ship_unit_conversions() -> None:
    assert MERCHANT.accel_si == pytest.approx(250.0 * 9.80665)
    assert MERCHANT.v_cap_si == pytest.approx(0.6 * 299_792_458.0)
