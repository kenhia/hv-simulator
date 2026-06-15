"""Trajectory-math validation: worked examples + physics invariants."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from hvsim.ephemeris import AU_M, heliocentric_position
from hvsim.kinematics import (
    SPEED_OF_LIGHT,
    STANDARD_GRAVITY,
    Trajectory,
    Vec3,
    solve_intercept,
    solve_profile,
)

A_250G = 250.0 * STANDARD_GRAVITY  # 2452.5 m/s²
V_CAP = 0.6 * SPEED_OF_LIGHT  # 0.6c
# Brachistochrone coasts only past this chord length (~88 AU at these settings).
COAST_THRESHOLD_M = V_CAP * V_CAP / A_250G


def _body_at(name: str):
    return lambda when: Vec3(*heliocentric_position(name, when))


# --- Worked example: Earth→Saturn brachistochrone -------------------------------


def test_earth_saturn_brachistochrone_matches_closed_form() -> None:
    d = 8.5 * AU_M  # representative Earth–Saturn separation
    p = solve_profile(d, A_250G, V_CAP)

    assert not p.coasts
    assert p.t_total == pytest.approx(2.0 * math.sqrt(d / A_250G), rel=1e-12)
    assert p.v_peak == pytest.approx(math.sqrt(A_250G * d), rel=1e-12)
    # Ballpark sanity: ~12.7 hours, peak ~0.187c.
    assert p.t_total / 3600.0 == pytest.approx(12.7, abs=0.3)
    assert p.v_peak / SPEED_OF_LIGHT == pytest.approx(0.187, abs=0.005)


# --- Profile selection ----------------------------------------------------------


def test_short_trip_is_brachistochrone() -> None:
    p = solve_profile(0.5 * COAST_THRESHOLD_M, A_250G, V_CAP)
    assert not p.coasts
    assert p.t_coast == 0.0
    assert p.v_peak < V_CAP


def test_long_trip_coasts_at_cap() -> None:
    p = solve_profile(2.0 * COAST_THRESHOLD_M, A_250G, V_CAP)
    assert p.coasts
    assert p.t_coast > 0.0
    assert p.v_peak == pytest.approx(V_CAP, rel=1e-12)
    assert p.t_accel == pytest.approx(V_CAP / A_250G, rel=1e-12)


@pytest.mark.parametrize("au", [0.01, 1.0, 8.5, 50.0, 200.0, 1000.0])
def test_velocity_never_exceeds_cap(au: float) -> None:
    p = solve_profile(au * AU_M, A_250G, V_CAP)
    speeds = [p.state(p.t_total * frac / 200.0)[1] for frac in range(201)]
    assert max(speeds) <= V_CAP * (1.0 + 1e-12)
    if p.coasts:
        assert p.state(p.t_total / 2.0)[1] == pytest.approx(V_CAP, rel=1e-12)


# --- State invariants -----------------------------------------------------------


def test_brachistochrone_is_symmetric() -> None:
    p = solve_profile(8.5 * AU_M, A_250G, V_CAP)
    # Peak speed reached exactly at the midpoint (the flip).
    assert p.state(p.t_total / 2.0)[1] == pytest.approx(p.v_peak, rel=1e-9)
    # Distance covered in the first half equals the second half.
    half = p.state(p.t_total / 2.0)[0]
    assert half == pytest.approx(p.distance / 2.0, rel=1e-9)


def test_state_endpoints() -> None:
    p = solve_profile(8.5 * AU_M, A_250G, V_CAP)
    assert p.state(0.0) == (0.0, 0.0, A_250G)
    s_end, v_end, _ = p.state(p.t_total)
    assert s_end == pytest.approx(p.distance, rel=1e-9)
    assert v_end == pytest.approx(0.0, abs=1e-3)  # arrives at rest


def test_state_continuous_across_phase_boundaries() -> None:
    p = solve_profile(2.0 * COAST_THRESHOLD_M, A_250G, V_CAP)  # has all three phases
    eps = 1e-3
    # At both boundaries the instantaneous speed is v_peak (= v_max). Position
    # must advance by ~v·Δt with no jump; velocity must not jump either. (A real
    # discontinuity from a branch bug would be orders of magnitude larger.)
    for boundary in (p.t_accel, p.t_accel + p.t_coast):
        s_before, v_before, _ = p.state(boundary - eps)
        s_after, v_after, _ = p.state(boundary + eps)
        assert (s_after - s_before) == pytest.approx(p.v_peak * 2 * eps, abs=1.0)
        assert v_after == pytest.approx(v_before, abs=A_250G * eps + 1e-6)


def test_trajectory_state_lies_on_chord() -> None:
    start = Vec3(1.0 * AU_M, 0.0, 0.0)
    end = Vec3(0.0, 8.5 * AU_M, 0.0)
    traj = Trajectory.between(start, end, A_250G, V_CAP)
    assert traj.state(0.0).position == start
    arrival = traj.state(traj.duration).position
    assert (arrival - end).norm() == pytest.approx(0.0, abs=1.0)  # within a metre


# --- Moving-target intercept ----------------------------------------------------


def test_intercept_converges_and_arrives_at_moving_target() -> None:
    depart = datetime(2026, 1, 1, tzinfo=UTC)
    start = Vec3(*heliocentric_position("earth", depart))
    saturn_at = _body_at("saturn")

    result = solve_intercept(start, saturn_at, depart, A_250G, V_CAP)

    assert result.iterations <= 5  # planet ≪ ship speed → converges fast
    # Ship's endpoint coincides with Saturn's position at the solved arrival time.
    endpoint = result.trajectory.state(result.trajectory.duration).position
    assert (endpoint - saturn_at(result.arrival)).norm() < 1_000e3  # < 1000 km
    # Ballpark: an Earth→Saturn dash is ~half a day.
    assert 10.0 < result.trajectory.duration / 3600.0 < 16.0


def test_intercept_accounts_for_target_motion() -> None:
    # The aim point should differ from the target's departure position, because
    # Saturn moves during the ~13-hour crossing.
    depart = datetime(2026, 1, 1, tzinfo=UTC)
    start = Vec3(*heliocentric_position("earth", depart))
    saturn_at = _body_at("saturn")
    result = solve_intercept(start, saturn_at, depart, A_250G, V_CAP)
    drift = (saturn_at(result.arrival) - saturn_at(depart)).norm()
    assert drift > 100e3  # Saturn moved >100 km; a static solve would miss


# --- Purity / determinism -------------------------------------------------------


def test_deterministic() -> None:
    assert solve_profile(8.5 * AU_M, A_250G, V_CAP) == solve_profile(8.5 * AU_M, A_250G, V_CAP)


def test_invalid_inputs_raise() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        solve_profile(-1.0, A_250G, V_CAP)
    with pytest.raises(ValueError, match="positive"):
        solve_profile(AU_M, 0.0, V_CAP)
