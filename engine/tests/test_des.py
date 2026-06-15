"""The discrete-event core: parity with Phase 1, determinism, and the model.

The headline guarantee of the Sprint 013 re-founding is **zero-drift parity**:
executing the canonical flight plan on the DES core reproduces the original
analytic ``state_at`` exactly. The oracle below is the *frozen pre-DES algorithm*
(a linear scan over segments) kept here so the parity claim is independent of the
production code path the DES now backs.

Tolerance: positions/velocities are compared at abs=1e-6 m — the DES path and the
oracle perform the *identical* float operations (same ``trajectory.state`` and
``heliocentric_position`` calls), so they agree to the bit; the epsilon only
guards against incidental reordering. Phase, segment, and ETA must match exactly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from hvsim.clock import T_YEAR, SimClock
from hvsim.des import (
    Event,
    EventQueue,
    OpenEndedSegment,
    ShipState,
    UnknownSegmentKind,
    evaluate,
    segment_end,
)
from hvsim.ephemeris import heliocentric_position
from hvsim.flightplan import (
    CompiledPlan,
    FlightPlan,
    Segment,
    Ship,
    Waypoint,
    compile_plan,
    simulation_for,
    state_at,
)
from hvsim.kinematics import ZERO, Vec3

DEPART = datetime(2026, 1, 1, tzinfo=UTC)
MERCHANT = Ship(name="SS Test Merchant", max_accel_g=250.0, max_velocity_c=0.6)


def _canonical_plan() -> FlightPlan:
    return FlightPlan(
        ship=MERCHANT,
        origin="earth",
        waypoints=[Waypoint("titan-station", timedelta(hours=6)), Waypoint("earth")],
        depart_at=DEPART,
    )


def _pos(body: str, when: datetime) -> Vec3:
    return Vec3(*heliocentric_position(body, when))


def _oracle_state(compiled: CompiledPlan, when: datetime) -> ShipState:
    """The pre-DES analytic algorithm, frozen as the parity oracle."""
    plan = compiled.plan
    segments = compiled.segments

    if not segments or when < plan.depart_at:
        return ShipState(when, _pos(plan.origin, when), ZERO, "predeparture", None, plan.depart_at)

    for seg in segments:
        if seg.t_start <= when < seg.t_end:
            if seg.kind == "transit":
                assert seg.trajectory is not None
                st = seg.trajectory.state((when - seg.t_start).total_seconds())
                return ShipState(when, st.position, st.velocity, "transit", seg.seq, seg.t_end)
            assert seg.body is not None
            return ShipState(when, _pos(seg.body, when), ZERO, "layover", seg.seq, seg.t_end)

    final_body = plan.waypoints[-1].body
    return ShipState(when, _pos(final_body, when), ZERO, "arrived", None, None)


def _assert_states_match(a: ShipState, b: ShipState) -> None:
    assert a.phase == b.phase
    assert a.segment_seq == b.segment_seq
    assert a.eta == b.eta
    assert a.when == b.when
    assert a.position == pytest.approx(b.position, abs=1e-6)
    assert a.velocity == pytest.approx(b.velocity, abs=1e-6)


# --- Parity: DES state(T) == the frozen analytic oracle -------------------------


def test_des_matches_analytic_oracle_across_dense_sweep() -> None:
    compiled = compile_plan(_canonical_plan())
    sim = simulation_for(compiled)

    span = (compiled.arrival + timedelta(hours=2)) - (DEPART - timedelta(hours=2))
    steps = 300
    for i in range(steps + 1):
        when = DEPART - timedelta(hours=2) + (span * i / steps)
        _assert_states_match(sim.state(when), _oracle_state(compiled, when))


def test_des_matches_oracle_exactly_at_boundaries() -> None:
    compiled = compile_plan(_canonical_plan())
    sim = simulation_for(compiled)
    eps = timedelta(microseconds=1)
    instants = [DEPART]
    for seg in compiled.segments:
        instants += [seg.t_start, seg.t_start + eps, seg.t_end - eps, seg.t_end]
    for when in instants:
        _assert_states_match(sim.state(when), _oracle_state(compiled, when))


def test_state_at_is_the_des_path() -> None:
    # The production entry point now goes through the core; results agree.
    compiled = compile_plan(_canonical_plan())
    mid = compiled.segments[0].t_start + timedelta(seconds=compiled.segments[0].duration_s / 2)
    _assert_states_match(state_at(compiled, mid), simulation_for(compiled).state(mid))


# --- Determinism ----------------------------------------------------------------


def test_state_is_deterministic() -> None:
    compiled = compile_plan(_canonical_plan())
    sim_a = simulation_for(compiled)
    sim_b = simulation_for(compile_plan(_canonical_plan()))
    for hours in (0, 3, 6, 12, 24, 36):
        when = DEPART + timedelta(hours=hours)
        assert sim_a.state(when) == sim_b.state(when)  # identical, field-for-field


def test_replay_independent_of_query_order() -> None:
    # Querying forwards, backwards, or shuffled yields the same per-instant state.
    compiled = compile_plan(_canonical_plan())
    sim = simulation_for(compiled)
    times = [DEPART + timedelta(hours=h) for h in range(0, 40, 2)]
    forward = {t: sim.state(t) for t in times}
    for t in reversed(times):
        assert sim.state(t) == forward[t]


# --- Event queue ----------------------------------------------------------------


def test_event_queue_pops_in_time_then_order() -> None:
    q = EventQueue()
    t0 = DEPART
    # Push out of order, including a tie at t0 broken by `order`.
    q.push(Event(t0 + timedelta(hours=1), 5, "enter"))
    q.push(Event(t0, 2, "enter"))
    q.push(Event(t0, 1, "enter"))
    popped = [(e.t, e.order) for e in (q.pop(), q.pop(), q.pop())]
    assert popped == [(t0, 1), (t0, 2), (t0 + timedelta(hours=1), 5)]
    assert not q


def test_advance_to_is_lazy_and_picks_active_segment() -> None:
    compiled = compile_plan(_canonical_plan())
    sim = simulation_for(compiled)
    assert sim.advance_to(DEPART - timedelta(hours=1)) is None  # nothing entered
    assert sim.advance_to(DEPART).seq == 0
    layover = compiled.segments[1]
    assert sim.advance_to(layover.t_start + timedelta(hours=1)).seq == 1
    assert sim.advance_to(compiled.arrival - timedelta(seconds=1)).seq == 2


# --- The segment model: exhaustive dispatch + the resolver seam -----------------


def test_evaluate_rejects_unknown_kind() -> None:
    bogus = Segment(seq=0, kind="warp", t_start=DEPART, t_end=DEPART + timedelta(hours=1))
    with pytest.raises(UnknownSegmentKind):
        evaluate(bogus, DEPART)


def test_segment_end_resolves_closed_and_rejects_open_ended() -> None:
    closed = Segment(seq=0, kind="layover", t_start=DEPART, t_end=DEPART + timedelta(hours=6))
    assert segment_end(closed, DEPART) == closed.t_end
    # An open-ended boundary (t_end=None) is the Phase 2c wormhole-queue seam:
    # the model admits it, but no resolver can fix it yet.
    open_ended = Segment(seq=1, kind="layover", t_start=DEPART, t_end=None)
    with pytest.raises(OpenEndedSegment):
        segment_end(open_ended, DEPART)


# --- PD calendar ----------------------------------------------------------------


def test_pd_epoch_reads_1890() -> None:
    clock = SimClock()
    assert clock.to_pd(clock.sim_epoch) == pytest.approx(1890.0)
    assert clock.pd_now() == pytest.approx(1890.0, abs=1e-3)  # ~now == epoch


def test_pd_year_advances_one_per_terran_year() -> None:
    clock = SimClock()
    assert clock.to_pd(clock.sim_epoch + T_YEAR) == pytest.approx(1891.0)
    assert clock.to_pd(clock.sim_epoch + 10 * T_YEAR) == pytest.approx(1900.0)


def test_pd_round_trips() -> None:
    clock = SimClock()
    for pd in (1890.0, 1900.5, 1851.25, 2003.75):
        assert clock.to_pd(clock.from_pd(pd)) == pytest.approx(pd)


def test_pd_epoch_year_is_configurable() -> None:
    clock = SimClock(pd_epoch_year=1900.0)
    assert clock.to_pd(clock.sim_epoch) == pytest.approx(1900.0)
