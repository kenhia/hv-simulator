"""Wormhole queue resolver — the math + the junction FCFS server (Sprint 019)."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import pytest

from hvsim.queue import (
    JunctionServer,
    interval,
    phantom_masses,
    tau,
)

# Canon transit-model coefficients (from the artifact).
A, B, BUFFER = 0.01684, 6.9e-13, 300.0
T0 = datetime(1920, 1, 1, tzinfo=UTC)


# --- tau / interval -------------------------------------------------------------


def test_tau_matches_the_formula() -> None:
    m = 5.0e6
    assert tau(m, A, B) == pytest.approx(A * math.sqrt(m) + B * m * m)


def test_interval_is_buffer_dominated_for_normal_ships() -> None:
    # A 2.5 Mt warship: tau is tens of seconds, far under the 300 s buffer.
    assert tau(2.5e6, A, B) < BUFFER
    assert interval(2.5e6, A, B, BUFFER) == pytest.approx(BUFFER)


def test_interval_tau_dominates_for_a_huge_convoy() -> None:
    # A 1e8 t mass: the B*M^2 term dwarfs the buffer.
    assert tau(1.0e8, A, B) > BUFFER
    assert interval(1.0e8, A, B, BUFFER) == pytest.approx(tau(1.0e8, A, B))


# --- Phantom traffic (seeded, varies, reproducible) -----------------------------


def test_phantom_draw_is_reproducible() -> None:
    a = phantom_masses(123, "manticore-junction", "347.5.3", 6.0)
    b = phantom_masses(123, "manticore-junction", "347.5.3", 6.0)
    assert a == b  # pure function of (seed, junction, ship-key)


def test_phantom_draw_varies_by_ship_and_junction() -> None:
    base = phantom_masses(123, "manticore-junction", "347.5.3", 6.0)
    other_ship = phantom_masses(123, "manticore-junction", "618.9.1", 6.0)
    other_junc = phantom_masses(123, "erewhon-junction", "347.5.3", 6.0)
    # Not all three identical — the key and junction perturb the stream.
    assert not (base == other_ship == other_junc)


def test_phantom_mean_depth_tracks_the_knob() -> None:
    # Averaged over many ship-keys, the count ~ Poisson(knob): busy >> quiet.
    busy = [len(phantom_masses(7, "busy", f"k{i}", 6.0)) for i in range(400)]
    quiet = [len(phantom_masses(7, "quiet", f"k{i}", 1.0)) for i in range(400)]
    assert sum(busy) / len(busy) == pytest.approx(6.0, abs=0.8)
    assert sum(quiet) / len(quiet) == pytest.approx(1.0, abs=0.4)


# --- The junction server --------------------------------------------------------


def _server(mean: float, seed: int = 1) -> JunctionServer:
    return JunctionServer("J", A, B, BUFFER, mean_depth=mean, seed=seed)


def test_quiet_junction_can_transit_almost_immediately() -> None:
    # mean 0 -> no phantom -> the ship transits at its arrival instant.
    res = _server(0.0).serve(T0, 2.5e6, "ship-1")
    assert res.transit_open == T0
    assert res.position(T0) == 1


def test_busy_junction_serialises_behind_phantom() -> None:
    res = _server(6.0).serve(T0, 2.5e6, "ship-1")
    assert res.transit_open > T0
    wait = (res.transit_open - T0).total_seconds()
    assert wait % BUFFER == pytest.approx(0.0, abs=1e-6)  # whole buffers (tau << buffer)
    # Position counts down to 1 as the phantom ahead clear.
    start = res.position(T0)
    assert start >= 1
    assert res.position(res.transit_open - timedelta(seconds=1)) == 1


def test_second_ship_serialises_behind_the_first() -> None:
    server = _server(6.0)
    first = server.serve(T0, 2.5e6, "ship-1")
    second = server.serve(T0, 2.5e6, "ship-2")  # arrives at the same instant
    assert second.transit_open > first.transit_open
    # At the shared arrival, the second ship sees a deeper queue (it's behind #1).
    assert second.position(T0) > first.position(T0)
