"""Repeating routes: a ship that lives on a loop (Sprint 039, #59).

Reuses the tiny self-contained artifact from ``test_route`` (alpha/beta/gamma,
one wormhole junction) so the cycle mechanics are exercised without the real
dataset. The load-bearing property under test is that a repeating route stays
**lazy and analytic** — no background tick, and re-querying the same instant
gives the same answer.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from conftest import DEPART, WARSHIP
from hvsim.route import RouteLeg, simulation_for_route
from hvsim.route.repeat import (
    REPEATING_ROUTE_SCHEMA,
    CycleRule,
    LayoverSpec,
    RepeatingRoute,
    cycle_end,
    from_filed,
    layover_for,
    route_at,
    to_filed,
)
from hvsim.universe import Universe

HOUR = 3600.0


def _courier(cycles: int | None = None, rules: tuple[CycleRule, ...] = ()) -> RepeatingRoute:
    """alpha:p1 -> alpha:far -> alpha:p1, forever — an in-system shuttle run."""
    return RepeatingRoute(
        ship=WARSHIP,
        transponder="1.1.1",
        origin_system="alpha",
        origin_body="alpha:p1",
        legs=[
            RouteLeg("nspace", "alpha", "alpha:far"),
            RouteLeg("nspace", "alpha", "alpha:p1"),
        ],
        start_at=DEPART,
        layovers=[LayoverSpec(1 * HOUR, 4 * HOUR), LayoverSpec(2 * HOUR, 6 * HOUR)],
        seed=42,
        cycles=cycles,
        rules=rules,
    )


# --- Deterministic layovers -----------------------------------------------------


def test_layover_is_inside_the_range_and_reproducible() -> None:
    rep = _courier()
    for cycle in range(20):
        for stop, spec in enumerate(rep.layovers):
            got = layover_for(rep, cycle, stop).total_seconds()
            assert spec.min_s <= got <= spec.max_s
            assert got == layover_for(rep, cycle, stop).total_seconds()


def test_layovers_vary_across_cycles() -> None:
    rep = _courier()
    draws = {layover_for(rep, c, 0).total_seconds() for c in range(20)}
    assert len(draws) > 15  # not a constant dressed up as a range


def test_a_cycle_rule_overrides_the_draw() -> None:
    # "every 5th round trip, a 12 h crew rotation at the origin stop".
    rep = _courier(rules=(CycleRule(every=5, stop=1, layover_s=12 * HOUR),))
    assert layover_for(rep, 4, 1) == timedelta(hours=12)  # cycle 5 (0-based 4)
    assert layover_for(rep, 9, 1) == timedelta(hours=12)
    assert layover_for(rep, 3, 1) != timedelta(hours=12)
    assert layover_for(rep, 4, 0) != timedelta(hours=12)  # the other stop is untouched


def test_a_fixed_layover_needs_no_draw() -> None:
    rep = RepeatingRoute(
        WARSHIP, "1.1.1", "alpha", "alpha:p1", [], DEPART, [LayoverSpec.fixed(90.0)]
    )
    assert layover_for(rep, 0, 0) == layover_for(rep, 7, 0) == timedelta(seconds=90)


# --- The cycle walk -------------------------------------------------------------


def test_cycle_zero_covers_the_start(u: Universe) -> None:
    rep = _courier()
    cycle, compiled = route_at(rep, DEPART, u)
    assert cycle == 0
    assert compiled.depart_at == DEPART
    assert compiled.route.origin_body == "alpha:p1"


def test_cycles_chain_end_to_start(u: Universe) -> None:
    rep = _courier()
    _, first = route_at(rep, DEPART, u)
    n, second = route_at(rep, first.arrival, u)
    assert n == 1
    assert second.depart_at == first.arrival  # cycle N+1 departs where N ended


def test_walk_reaches_a_far_future_cycle(u: Universe) -> None:
    rep = _courier()
    _, first = route_at(rep, DEPART, u)
    span = first.arrival - DEPART
    far = DEPART + span * 12 + timedelta(minutes=1)
    cycle, compiled = route_at(rep, far, u)
    assert cycle >= 10  # cycles differ in length, so just check we walked deep
    assert compiled.depart_at <= far < compiled.arrival


def test_state_is_identical_when_requeried(u: Universe) -> None:
    rep = _courier()
    when = DEPART + timedelta(days=40)

    def sample() -> tuple:
        cycle, compiled = route_at(rep, when, u)
        st = simulation_for_route(compiled, u).state(when)
        return cycle, st.phase, st.position.x, st.position.y, st.position.z

    assert sample() == sample()  # analytic, not stateful


def test_a_forever_route_never_arrives(u: Universe) -> None:
    rep = _courier()
    _, first = route_at(rep, DEPART, u)
    span = first.arrival - DEPART
    for n in range(1, 6):
        when = DEPART + span * n - timedelta(seconds=1)
        _, compiled = route_at(rep, when, u)
        assert simulation_for_route(compiled, u).state(when).phase != "arrived"


def test_a_finite_route_ends_arrived_at_its_origin(u: Universe) -> None:
    rep = _courier(cycles=2)
    _, last = route_at(rep, DEPART + timedelta(days=3650), u)
    cycle, compiled = route_at(rep, DEPART + timedelta(days=3650), u)
    assert cycle == 1  # the final cycle, held forever after
    st = simulation_for_route(compiled, u).state(DEPART + timedelta(days=3650))
    assert st.phase == "arrived"
    assert compiled.final_body == "alpha:p1" == last.final_body


def test_a_wormhole_cycle_chains_across_its_queue(u: Universe) -> None:
    # beta:p1 -> gamma (junction) -> back. The compiled cycle is unresolved like any
    # route (the queue is open-ended), but the *boundary* resolves in isolation, so
    # the next cycle departs after the wait rather than through it.
    rep = RepeatingRoute(
        ship=WARSHIP,
        transponder="1.1.1",
        origin_system="beta",
        origin_body="beta:p1",
        legs=[
            RouteLeg("wormhole", "gamma", None),
            RouteLeg("wormhole", "beta", "beta:p1"),
        ],
        start_at=DEPART,
        layovers=[LayoverSpec.fixed(0.0), LayoverSpec.fixed(2 * HOUR)],
        seed=7,
    )
    cycle, compiled = route_at(rep, DEPART + timedelta(hours=1), u)
    assert cycle == 0
    assert any(s.kind == "wormhole_queue" and s.t_end is None for s in compiled.segments)

    boundary = cycle_end(rep, 0, DEPART, u)
    assert boundary > compiled.arrival  # the queue wait is inside the cycle
    n, second = route_at(rep, boundary, u)
    assert n == 1 and second.depart_at == boundary


def test_an_absurd_template_is_refused_not_walked_forever(u: Universe) -> None:
    from hvsim.route.repeat import CycleWalkTooLong

    rep = _courier()
    with pytest.raises(CycleWalkTooLong):
        route_at(rep, DEPART + timedelta(days=365 * 500), u)


# --- The filed document ---------------------------------------------------------


def test_filed_document_round_trips(u: Universe) -> None:
    rep = _courier(cycles=5, rules=(CycleRule(3, 1, 12 * HOUR),))
    doc = to_filed(rep)
    assert doc["schema"] == REPEATING_ROUTE_SCHEMA and doc["ship"] == "1.1.1"
    back = from_filed(doc, u)
    assert back.origin_system == rep.origin_system and back.origin_body == rep.origin_body
    assert [(lg.mode, lg.to_system, lg.to_body) for lg in back.legs] == [
        (lg.mode, lg.to_system, lg.to_body) for lg in rep.legs
    ]
    assert back.layovers == rep.layovers and back.rules == rep.rules
    assert back.cycles == 5 and back.seed == 42
    assert back.start_at == datetime(1890, 1, 1, tzinfo=UTC)


def test_a_loop_that_does_not_return_home_is_refused(u: Universe) -> None:
    doc = to_filed(_courier())
    doc["legs"] = doc["legs"][:1]  # ends at alpha:far, not back at alpha:p1
    with pytest.raises(ValueError, match="return to its origin"):
        from_filed(doc, u)


def test_a_one_shot_document_is_not_a_repeating_route(u: Universe) -> None:
    with pytest.raises(ValueError, match="unexpected repeating-route schema"):
        from_filed({"schema": "hvsim.filed-route/v1"}, u)
